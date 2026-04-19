"""
美股市场数据工具

为 TradingAgents 提供美股市场数据查询工具。
"""

import logging
from typing import Any, Dict, List, Optional

from core.market_data.managers.source_router import DataSourceRouter
from core.market_data.models import MarketType
from core.market_data.tools.base_tool import DataSource, MarketDataToolBase

logger = logging.getLogger(__name__)


class USStockTool(MarketDataToolBase):
    """
    美股市场数据工具

    提供美股市场数据查询功能
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
        return MarketType.US_STOCK

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
            if not symbol.endswith(".US"):
                symbol = f"{symbol}.US"

            # 尝试从 Yahoo Finance 获取实时行情

            # 获取 Yahoo Finance 适配器
            sources = await self.source_router.get_available_sources(MarketType.US_STOCK)

            for source in sources:
                if source.source_name == "yahoo":
                    quote = await source.get_realtime_quote(symbol)  # type: ignore[attr-defined]
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
        获取热门美股列表

        Args:
            limit: 返回数量

        Returns:
            股票信息列表
        """
        try:
            # 从数据库获取美股列表
            stocks = await super().get_stock_list(limit)

            if not stocks and self.source_router:
                # 如果数据库为空，从数据源获取
                logger.info("No US stocks in database, fetching from data source")
                stock_list = await self.source_router.route_to_best_source(
                    market=MarketType.US_STOCK, method_name="get_stock_list", status="L"
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
            logger.error(f"Failed to get US stock list: {e}")
            return []

    async def get_popular_stocks(self) -> List[Dict[str, Any]]:
        """
        获取热门美股列表

        Returns:
            热门美股列表
        """
        popular_symbols = [
            "AAPL.US",  # Apple
            "MSFT.US",  # Microsoft
            "GOOGL.US",  # Google
            "AMZN.US",  # Amazon
            "TSLA.US",  # Tesla
            "META.US",  # Meta
            "NVDA.US",  # NVIDIA
            "JPM.US",  # JPMorgan
            "V.US",  # Visa
            "JNJ.US",  # Johnson & Johnson
        ]

        results = []
        for symbol in popular_symbols:
            stock_info = await self.get_stock_info(symbol)
            if stock_info:
                results.append(stock_info)

        return results

    async def get_technical_indicators(
        self, symbol: str, indicator: str = "SMA", time_period: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        获取技术指标

        Args:
            symbol: 股票代码
            indicator: 指标名称（SMA, EMA, RSI, MACD, BBANDS）
            time_period: 时间周期

        Returns:
            技术指标数据
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return None

            # 确保代码格式正确
            if not symbol.endswith(".US"):
                symbol = f"{symbol}.US"

            # 获取 Alpha Vantage 适配器（技术指标）
            sources = await self.source_router.get_available_sources(MarketType.US_STOCK)

            for source in sources:
                if source.source_name == "alphavantage":
                    if hasattr(source, f"get_{indicator.lower()}"):
                        method = getattr(source, f"get_{indicator.lower()}")
                        result = await method(symbol, time_period=time_period)
                        return dict(result) if result else None  # type: ignore[no-any-return]

            logger.warning(f"Technical indicator {indicator} not available for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Failed to get technical indicators for {symbol}: {e}")
            return None


# 导出
__all__ = ["USStockTool"]
