"""
市场数据业务服务层

实现核心业务逻辑:
1. 用户配置优先: 如果用户配置了付费接口,实时获取不存储
2. 降级策略: 如果用户没配置,从公共数据库查,没有就降级到AkShare
3. 健康检查: 实时监控数据源状态
"""

import logging
from typing import Any
from datetime import datetime

from core.market_data.models.datasource import (
    DataSourceType,
    DataSourceHealthStatus,
    DataSourceStatus,
)
from core.market_data.models.watchlist import UserWatchlist
from core.market_data.repositories.datasource import (
    SystemDataSourceRepository,
    UserDataSourceRepository,
    DataSourceStatusRepository,
    DataSourceStatusHistoryRepository,
)
from core.market_data.repositories.watchlist import UserWatchlistRepository
from core.market_data.repositories.stock_info import StockInfoRepository
from core.market_data.repositories.stock_quotes import StockQuoteRepository
from core.market_data.sources.base import DataSourceAdapter
from core.market_data.models import MarketType
from core.market_data.managers.source_router import (
    DataSourceRouter,
    get_source_router,
)

logger = logging.getLogger(__name__)


class MarketDataService:
    """市场数据业务服务"""

    def __init__(self):
        self.system_source_repo = SystemDataSourceRepository()
        self.user_source_repo = UserDataSourceRepository()
        self.status_repo = DataSourceStatusRepository()
        self.status_history_repo = DataSourceStatusHistoryRepository()
        self.watchlist_repo = UserWatchlistRepository()
        self.stock_info_repo = StockInfoRepository()
        self.stock_quotes_repo = StockQuoteRepository()
        self.router = None  # 延迟初始化

    async def _get_router(self, market: MarketType) -> DataSourceRouter:
        """
        获取数据源路由器（延迟初始化）

        Args:
            market: 市场类型

        Returns:
            数据源路由器
        """
        if self.router is None:
            self.router = get_source_router()
        return self.router

    async def get_stock_list_with_fallback(
        self,
        market: MarketType,
        user_id: str | None = None,
        status: str = "L"
    ) -> tuple[list[dict[str, Any]], str]:
        """
        获取股票列表(支持用户配置和降级)

        业务逻辑:
        1. 如果用户配置了数据源,优先使用用户配置
        2. 否则使用系统公共数据源
        3. 自动降级到备用数据源

        Args:
            market: 市场类型
            user_id: 用户ID
            status: 上市状态

        Returns:
            (股票列表, 实际使用的数据源)
        """
        market_str = market.value

        # 获取路由器
        router = await self._get_router(market)

        # 获取系统公共数据源配置
        system_sources = await self.system_source_repo.get_enabled_configs(
            market=market_str,
            enabled_only=True
        )

        # 如果有用户ID，获取用户配置
        user_configs = []
        if user_id:
            user_configs = await self.user_source_repo.get_user_configs(
                user_id=user_id,
                market=market_str,
                enabled=True
            )
            logger.info(f"User {user_id} has {len(user_configs)} configured data sources for {market_str}")
        else:
            logger.info(f"No user_id provided, using system sources only for {market_str}")

        # 合并数据源（用户配置优先级更高）
        all_sources = []
        added_sources = set()

        # 先添加用户配置的数据源（优先级更高）
        for config in user_configs:
            source_id = config.get("source_id")
            if source_id and source_id not in added_sources:
                all_sources.append({
                    "source_id": source_id,
                    "priority": config.get("priority", 999),
                    "config": config.get("config", {}),
                    "is_user": True
                })
                added_sources.add(source_id)

        # 再添加系统数据源（排除已添加的）
        for config in system_sources:
            source_id = config.get("source_id")
            if source_id and source_id not in added_sources:
                all_sources.append({
                    "source_id": source_id,
                    "priority": config.get("priority", 999),
                    "config": config.get("config", {}),
                    "is_user": False
                })
                added_sources.add(source_id)

        # 按优先级排序
        all_sources.sort(key=lambda x: x["priority"])

        if not all_sources:
            logger.warning(f"No available data sources for {market_str}")
            return [], "none"

        logger.info(f"Trying {len(all_sources)} data sources for {market_str}: {[s['source_id'] for s in all_sources]}")

        # 遍历数据源，尝试获取数据
        last_error = None
        for source_config in all_sources:
            source_id = source_config["source_id"]

            try:
                logger.info(f"Fetching stock list from {source_id} for {market_str}")

                # 调用路由器的 route_to_best_source 方法
                result = await router.route_to_best_source(
                    market=market,
                    method_name="get_stock_list",
                    status=status
                )

                if result:
                    # 转换为字典列表
                    stock_list = [stock.model_dump() for stock in result]
                    logger.info(f"Successfully fetched {len(stock_list)} stocks from {source_id}")
                    return stock_list, source_id

            except Exception as e:
                last_error = e
                logger.warning(f"Failed to fetch stock list from {source_id}: {e}")
                continue

        # 所有数据源都失败
        logger.error(f"All data sources failed for {market_str}. Last error: {last_error}")
        return [], "failed"

    async def get_daily_quotes_with_fallback(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        user_id: str | None = None,
        adjust_type: str | None = None
    ) -> tuple[list[dict[str, Any]], str]:
        """
        获取日线行情(支持用户配置和降级)

        业务逻辑(按文档要求):
        1. 如果用户配置了付费数据源 → 实时获取,直接返回(不存储)
        2. 如果用户没配置 → 从公共数据库查询
        3. 如果数据库没有 → 降级到AkShare实时获取

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            user_id: 用户ID
            adjust_type: 复权类型

        Returns:
            (行情列表, 数据来源说明)
        """
        source_used = "database"

        # 判断市场类型
        market = self._infer_market_from_symbol(symbol)
        if not market:
            logger.error(f"Cannot infer market type for symbol: {symbol}")
            return [], "unknown"

        market_str = market.value

        # 步骤1: 检查用户是否配置了付费数据源
        if user_id:
            user_sources = await self.user_source_repo.get_user_configs(
                user_id=user_id,
                market=market_str,
                enabled=True
            )

            if user_sources:
                # 用户配置了数据源，实时获取(通道1)
                logger.info(f"User {user_id} has configured data source for {symbol}, fetching real-time")

                # 获取路由器
                router = await self._get_router(market)

                # 获取用户配置的数据源ID列表
                user_source_ids = [config.get("source_id") for config in user_sources]

                # 尝试从用户配置的数据源获取
                last_error = None
                for source_id in user_source_ids:
                    try:
                        logger.info(f"Fetching real-time quotes for {symbol} from user source: {source_id}")

                        # 这里需要实现直接从用户配置的数据源获取
                        # 由于数据源路由器的限制，我们使用数据库查询作为降级
                        quotes = await self._fetch_from_user_source(
                            symbol=symbol,
                            source_id=source_id,
                            start_date=start_date,
                            end_date=end_date,
                            adjust_type=adjust_type
                        )

                        if quotes:
                            source_used = f"user_realtime_{source_id}"
                            logger.info(f"Successfully fetched {len(quotes)} quotes from user source {source_id}")
                            return quotes, source_id

                    except Exception as e:
                        last_error = e
                        logger.warning(f"Failed to fetch from user source {source_id}: {e}")
                        continue

        # 步骤2: 从公共数据库查询
        quotes = await self.stock_quotes_repo.get_quotes(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        if quotes:
            # 数据库有数据，直接返回
            logger.info(f"Found {len(quotes)} quotes in database for {symbol}")
            return quotes, "database"

        # 步骤3: 数据库没有，降级到AkShare实时获取
        logger.info(f"No data in database for {symbol}, fallback to AkShare")

        try:
            # 获取路由器
            router = await self._get_router(market)

            # 调用路由器的降级方法
            result = await router.route_to_best_source(
                market=market,
                method_name="get_daily_quotes",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust_type=adjust_type
            )

            if result:
                # 转换为字典列表
                quotes = [quote.model_dump() for quote in result]

                # 可选：存储到数据库
                try:
                    for quote_data in quotes:
                        await self.stock_quotes_repo.upsert_one(
                            filter_query={
                                "symbol": quote_data.get("symbol"),
                                "trade_date": quote_data.get("trade_date")
                            },
                            data={**quote_data, "updated_at": datetime.now()}
                        )
                    logger.info(f"Stored {len(quotes)} quotes to database from AkShare fallback")
                except Exception as e:
                    logger.warning(f"Failed to store quotes to database: {e}")

                source_used = "akshare_fallback"
                logger.info(f"Successfully fetched {len(quotes)} quotes from AkShare fallback")
                return quotes, source_used

        except Exception as e:
            logger.error(f"Failed to fetch from AkShare fallback: {e}")

        return [], "failed"

    def _infer_market_from_symbol(self, symbol: str) -> MarketType | None:
        """
        从股票代码推断市场类型

        Args:
            symbol: 股票代码

        Returns:
            市场类型，无法推断时返回 None
        """
        if not symbol:
            return None

        if symbol.endswith(('.SH', '.SZ')):
            return MarketType.A_STOCK
        elif symbol.endswith('.US'):
            return MarketType.US_STOCK
        elif symbol.endswith('.HK'):
            return MarketType.HK_STOCK
        elif '.' in symbol:
            # 其他格式，尝试从后缀判断
            suffix = symbol.split('.')[-1].upper()
            if suffix in ['SH', 'SZ']:
                return MarketType.A_STOCK
            elif suffix == 'US':
                return MarketType.US_STOCK
            elif suffix == 'HK':
                return MarketType.HK_STOCK

        # 无法推断，默认为A股
        return MarketType.A_STOCK

    async def _fetch_from_user_source(
        self,
        symbol: str,
        source_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        从用户配置的数据源获取数据

        注意: 此方法目前是简化实现，实际应从用户配置中获取真实的 API 密钥。
        完整实现需要从 user_source_repo 获取用户配置的完整 config。

        Args:
            symbol: 股票代码
            source_id: 数据源ID
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型

        Returns:
            行情数据列表
        """
        # 从用户配置中获取真实配置（包含 API 密钥）
        # 注意：这里简化实现，实际使用时应从用户配置中获取
        try:
            config = await self.user_source_repo.get_config(
                user_id="",  # 实际应传入真实 user_id
                source_id=source_id,
                market=self._infer_market_from_symbol(symbol).value if self._infer_market_from_symbol(symbol) else "A_STOCK"
            )
            user_config = config.get("config", {}) if config else {}
        except Exception:
            user_config = {}

        # 延迟导入避免循环依赖
        if source_id == "tushare_pro":
            from core.market_data.sources.a_stock.tushare_adapter import TuShareAdapter
            adapter = TuShareAdapter(config=user_config or {})
        elif source_id == "alpha_vantage":
            from core.market_data.sources.us_stock.alphavantage_adapter import AlphaVantageAdapter
            adapter = AlphaVantageAdapter(config=user_config or {})
        else:
            logger.warning(f"Unsupported user source: {source_id}")
            return []

        try:
            result = await adapter.get_daily_quotes(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust_type=adjust_type
            )

            # 转换为字典列表
            return [quote.model_dump() for quote in result]

        except Exception as e:
            logger.error(f"Failed to fetch from user source {source_id}: {e}")
            return []
