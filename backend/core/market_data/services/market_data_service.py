"""
市场数据业务服务层

实现核心业务逻辑:
1. 用户配置优先: 如果用户配置了付费接口,实时获取不存储
2. 降级策略: 如果用户没配置,从公共数据库查,没有就降级到AkShare
3. 健康检查: 实时监控数据源状态
"""

import logging
from typing import Optional, List, Dict, Any
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

    async def get_stock_list_with_fallback(
        self,
        market: MarketType,
        user_id: Optional[str] = None,
        status: str = "L"
    ) -> tuple[List[Dict[str, Any]], str]:
        """
        获取股票列表(支持用户配置和降级)

        业务逻辑:
        1. 如果用户配置了数据源,优先使用用户配置
        2. 否则使用系统公共数据源
        3. 自动降级到备用数据源

        Returns:
            (股票列表, 实际使用的数据源)
        """
        market_str = market.value

        # TODO: 获取用户配置的数据源
        user_sources = []
        if user_id:
            user_sources = await self.user_source_repo.get_user_sources(
                user_id=user_id,
                market=market_str
            )

        # 获取系统公共数据源
        system_sources = await self.system_source_repo.get_all_enabled(
            market=market_str
        )

        # 合并数据源(用户配置优先级更高)
        all_sources = user_sources + system_sources

        # 按优先级排序
        all_sources.sort(key=lambda x: x.get("priority", 999))

        # TODO: 遍历数据源,尝试获取数据
        # 1. 初始化数据源适配器
        # 2. 调用get_stock_list
        # 3. 成功则返回,失败则尝试下一个

        # 临时实现: 直接返回空列表
        logger.warning("User data source config not fully implemented yet")
        return [], "tushare"

    async def get_daily_quotes_with_fallback(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], str]:
        """
        获取日线行情(支持用户配置和降级)

        业务逻辑(按文档要求):
        1. 如果用户配置了付费数据源 → 实时获取,直接返回(不存储)
        2. 如果用户没配置 → 从公共数据库查询
        3. 如果数据库没有 → 降级到AkShare实时获取

        Returns:
            (行情列表, 数据来源说明)
        """
        source_used = "database"

        # 步骤1: 检查用户是否配置了付费数据源
        if user_id:
            user_sources = await self.user_source_repo.get_user_sources(
                user_id=user_id,
                market="A_STOCK"  # TODO: 根据symbol判断market
            )

            if user_sources:
                # 用户配置了数据源,实时获取(通道1)
                logger.info(f"User {user_id} has configured data source, fetching real-time")
                # TODO: 调用用户配置的数据源获取数据
                # 实时获取,不存储,直接返回
                source_used = "user_realtime"
                return [], source_used

        # 步骤2: 从公共数据库查询
        quotes = await self.stock_quotes_repo.get_quotes(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        if quotes:
            # 数据库有数据,直接返回
            logger.info(f"Found {len(quotes)} quotes in database for {symbol}")
            return quotes, "database"

        # 步骤3: 数据库没有,降级到AkShare实时获取
        logger.info(f"No data in database for {symbol}, fallback to AkShare")
        # TODO: 调用AkShare获取数据
        # 如果需要,可以写入数据库(通道2,限流)

        return [], "akshare_fallback"
