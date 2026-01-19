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
from core.market_data.services.dual_channel_service import (
    get_dual_channel_service,
    DualChannelResult,
    ChannelType
)
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
        self.dual_channel_service = get_dual_channel_service(
            storage_callback=self._storage_callback
        )

    async def _storage_callback(self, symbol: str, data_type: str, data: Any) -> None:
        """
        双通道服务的存储回调
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            data: 数据内容
        """
        if not data:
            return

        try:
            if data_type == "daily_quote" and isinstance(data, list):
                # 批量存入日线行情
                for quote_data in data:
                    # 确保是字典
                    quote_dict = quote_data
                    if hasattr(quote_data, "model_dump"):
                        quote_dict = quote_data.model_dump()
                    elif not isinstance(quote_dict, dict):
                        continue

                    await self.stock_quotes_repo.upsert_one(
                        filter_query={
                            "symbol": quote_dict.get("symbol"),
                            "trade_date": quote_dict.get("trade_date")
                        },
                        data={**quote_dict, "updated_at": datetime.now()}
                    )
                logger.info(f"Stored {len(data)} quotes for {symbol} to database via callback")
        except Exception as e:
            logger.warning(f"Failed to store data via callback: {e}")

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
        1. 如果用户配置了付费数据源 → 实时获取,直接返回(双通道: 同时异步存入DB)
        2. 如果用户没配置 → 降级逻辑
           a. 从公共数据库查询
           b. 如果数据库没有 → 降级到AkShare实时获取并存入DB

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            user_id: 用户ID
            adjust_type: 复权类型

        Returns:
            (行情列表, 数据来源说明)
        """
        # 标准化日期格式为 YYYY-MM-DD
        from core.market_data.tools.field_mapper import FieldMapper
        if start_date:
            normalized = FieldMapper.normalize_date(start_date)
            if len(normalized) == 8:
                start_date = f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"
            else:
                start_date = normalized
        
        if end_date:
            normalized = FieldMapper.normalize_date(end_date)
            if len(normalized) == 8:
                end_date = f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"
            else:
                end_date = normalized

        # 判断市场类型
        market = self._infer_market_from_symbol(symbol)
        if not market:
            logger.error(f"Cannot infer market type for symbol: {symbol}")
            return [], "unknown"

        market_str = market.value
        
        # 准备用户数据源获取函数
        user_source_func = None
        has_user_config = False
        user_source_id = "unknown"

        if user_id:
            user_configs = await self.user_source_repo.get_user_configs(
                user_id=user_id,
                market=market_str,
                enabled=True
            )
            
            if user_configs:
                has_user_config = True
                # 使用优先级最高的数据源
                # 注意：这里简化处理，只取第一个。实际应该尝试所有配置的数据源。
                # 为了配合 fetch_func 的签名，我们构建一个闭包
                config = user_configs[0]
                user_source_id = config.get("source_id", "unknown")
                
                async def _fetch_user_data():
                    return await self._fetch_from_user_source(
                        symbol=symbol,
                        source_id=user_source_id,
                        user_id=user_id,
                        start_date=start_date,
                        end_date=end_date,
                        adjust_type=adjust_type
                    )
                user_source_func = _fetch_user_data

        # 准备降级获取函数 (仅查 DB)
        async def _fallback_func():
            # 1. 查 DB
            quotes = await self.stock_quotes_repo.get_quotes(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            if quotes:
                return quotes
            
            # DB 无数据，返回空列表（根据文档，用户未配置私有源时只能读库，不能触发公共源实时抓取）
            logger.info(f"No data in database for {symbol}, and no user source configured. Returning empty.")
            return []

        # 执行双通道获取 (如果配置了用户源) 或 直接降级
        if has_user_config and user_source_func:
            logger.info(f"Fetching quotes for {symbol} using user source {user_source_id}")
            result, source = await self.dual_channel_service.fetch_data(
                symbol=symbol,
                data_type="daily_quote",
                fetch_func=user_source_func,
                fallback_func=_fallback_func
            )
            return result, source
        else:
            # 没有用户配置，直接查 DB
            logger.info(f"No user source for {symbol}, reading from database only")
            quotes = await _fallback_func()
            return quotes, "database" if quotes else "none"

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
        user_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        从用户配置的数据源获取数据

        Args:
            symbol: 股票代码
            source_id: 数据源ID
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型

        Returns:
            行情数据列表
        """
        # 从用户配置中获取真实配置（包含 API 密钥）
        try:
            config = await self.user_source_repo.get_config(
                user_id=user_id,
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
