"""
港股市场数据工具

为 TradingAgents 提供港股市场数据查询工具。
"""

import logging
from typing import Any, Dict, List, Optional

from core.market_data.managers.source_router import DataSourceRouter
from core.market_data.models import MarketType
from core.market_data.tools.base_tool import DataSource, MarketDataToolBase

logger = logging.getLogger(__name__)


class HKStockTool(MarketDataToolBase):
    """
    港股市场数据工具

    提供港股市场数据查询功能
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        source_router: Optional[DataSourceRouter] = None,
        data_source: DataSource = DataSource.AUTO,
    ):
        super().__init__(user_id, source_router, data_source)

    def get_market(self) -> MarketType:
        """获取市场类型"""
        return MarketType.HK_STOCK

    async def get_realtime_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情

        Args:
            symbol: 股票代码

        Returns:
            实时行情数据
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured, falling back to database")
                return await self.get_latest_quote(symbol)

            # 确保代码格式正确
            if not symbol.endswith(".HK"):
                # 补0到4位
                code = symbol.zfill(4)
                symbol = f"{code}.HK"

            # 尝试从数据源获取实时行情
            sources = await self.source_router.get_available_sources(MarketType.HK_STOCK)

            for source in sources:
                if hasattr(source, "get_realtime_quote"):
                    quote = await source.get_realtime_quote(symbol)  # type: ignore[union-attr]
                    if quote:
                        return dict(quote)  # type: ignore[no-any-return]

            # 如果实时数据获取失败，回退到数据库
            logger.warning(f"Realtime quote not available for {symbol}, using database")
            return await self.get_latest_quote(symbol)

        except Exception as e:
            logger.error(f"Failed to get realtime quote for {symbol}: {e}")
            return await self.get_latest_quote(symbol)

    async def get_stock_list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取热门港股列表

        Args:
            limit: 返回数量

        Returns:
            股票信息列表
        """
        try:
            # 从数据库获取港股列表
            stocks = await super().get_stock_list(limit)

            if not stocks and self.source_router:
                # 如果数据库为空，从数据源获取
                logger.info("No HK stocks in database, fetching from data source")
                stock_list = await self.source_router.route_to_best_source(
                    market=MarketType.HK_STOCK, method_name="get_stock_list", status="L"
                )

                return [
                    {
                        "symbol": s.symbol,
                        "market": s.market,
                        "name": s.name,
                        "industry": s.industry,
                        "sector": s.sector,
                        "listing_date": s.listing_date,
                        "exchange": s.exchange,
                        "status": s.status,
                        "data_source": s.data_source,
                    }
                    for s in stock_list
                ]

            return stocks

        except Exception as e:
            logger.error(f"Failed to get HK stock list: {e}")
            return []

    async def get_popular_stocks(self) -> List[Dict[str, Any]]:
        """
        获取热门港股列表

        Returns:
            热门港股列表
        """
        popular_symbols = [
            "0700.HK",  # 腾讯
            "9988.HK",  # 阿里巴巴
            "0941.HK",  # 中国移动
            "1299.HK",  # 友邦保险
            "0939.HK",  # 建设银行
            "1398.HK",  # 工商银行
            "2318.HK",  # 平安保险
            "0883.HK",  # 中国海洋石油
            "0388.HK",  # 港交所
            "0005.HK",  # 汇丰控股
        ]

        results = []
        for symbol in popular_symbols:
            stock_info = await self.get_stock_info(symbol)
            if stock_info:
                results.append(stock_info)

        return results

    async def get_hk_connect_stocks(self) -> List[Dict[str, Any]]:
        """
        获取港股通成分股

        Returns:
            港股通成分股列表
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return []

            # 获取 AkShare 适配器
            sources = await self.source_router.get_available_sources(MarketType.HK_STOCK)

            for source in sources:
                if source.source_name == "akshare" and hasattr(
                    source, "get_hk_stock_ggt_components"
                ):
                    components = await source.get_hk_stock_ggt_components()  # type: ignore[union-attr]
                    return list(components) if components else []  # type: ignore[no-any-return]

            return []

        except Exception as e:
            logger.error(f"Failed to get HK Connect stocks: {e}")
            return []

    async def get_hk_money_flow(self) -> Optional[Dict[str, Any]]:
        """
        获取港股通资金流向

        Returns:
            资金流向数据
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return None

            # 获取 AkShare 适配器
            sources = await self.source_router.get_available_sources(MarketType.HK_STOCK)

            for source in sources:
                if source.source_name == "akshare" and hasattr(source, "get_hk_stock_money_flow"):
                    flow_data = await source.get_hk_stock_money_flow()  # type: ignore[union-attr]
                    return dict(flow_data) if flow_data else None  # type: ignore[no-any-return]

            return None

        except Exception as e:
            logger.error(f"Failed to get HK money flow: {e}")
            return None

    async def get_hk_index_spot(self) -> List[Dict[str, Any]]:
        """
        获取港股指数实时行情

        Returns:
            指数行情列表
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return []

            # 获取 AkShare 适配器
            sources = await self.source_router.get_available_sources(MarketType.HK_STOCK)

            for source in sources:
                if source.source_name == "akshare" and hasattr(source, "get_hk_index_spot"):
                    index_data = await source.get_hk_index_spot()
                    return list(index_data) if index_data else []  # type: ignore[no-any-return]

            return []

        except Exception as e:
            logger.error(f"Failed to get HK index spot: {e}")
            return []

    async def get_hk_index_daily(
        self, symbol: str = "恒生指数", days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取港股指数历史行情

        Args:
            symbol: 指数名称
            days: 获取最近N天的数据

        Returns:
            指数历史行情列表
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return []

            # 获取 AkShare 适配器
            sources = await self.source_router.get_available_sources(MarketType.HK_STOCK)

            for source in sources:
                if source.source_name == "akshare" and hasattr(source, "get_hk_index_daily"):
                    index_data = await source.get_hk_index_daily(symbol=symbol)
                    # 限制返回数量
                    return index_data[:days] if index_data else []

            return []

        except Exception as e:
            logger.error(f"Failed to get HK index daily: {e}")
            return []


# 导出
__all__ = ["HKStockTool"]
