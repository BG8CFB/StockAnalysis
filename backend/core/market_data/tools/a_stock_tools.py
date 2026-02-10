"""
A股市场数据工具

为 TradingAgents 提供A股市场数据查询工具。
"""

import logging
from typing import Any, Dict, List, Optional

from core.market_data.models import MarketType
from core.market_data.tools.base_tool import DataSource, MarketDataToolBase
from core.market_data.managers.source_router import DataSourceRouter

logger = logging.getLogger(__name__)


class AStockTool(MarketDataToolBase):
    """
    A股市场数据工具

    提供A股市场数据查询功能
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
        return MarketType.A_STOCK

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

            # 确保代码格式正确（A股代码格式：000001.SZ 或 600000.SH）
            if not (symbol.endswith(".SZ") or symbol.endswith(".SH")):
                # 根据代码前缀判断交易所
                if symbol.startswith(("000", "001", "002", "003", "300", "301")):
                    symbol = f"{symbol}.SZ"
                elif symbol.startswith(("600", "601", "603", "605", "688", "689")):
                    symbol = f"{symbol}.SH"

            # 尝试从 AkShare 获取实时行情（免费数据源）
            sources = await self.source_router.get_available_sources(MarketType.A_STOCK)

            for source in sources:
                if hasattr(source, "get_realtime_quote"):
                    quote = await source.get_realtime_quote(symbol)
                    if quote:
                        return quote

            # 如果实时数据获取失败，回退到数据库
            logger.warning(f"Realtime quote not available for {symbol}, using database")
            return await self.get_latest_quote(symbol)

        except Exception as e:
            logger.error(f"Failed to get realtime quote for {symbol}: {e}")
            return await self.get_latest_quote(symbol)

    async def get_stock_list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取A股股票列表

        Args:
            limit: 返回数量

        Returns:
            股票信息列表
        """
        try:
            # 从数据库获取A股列表
            stocks = await super().get_stock_list(limit)

            if not stocks and self.source_router:
                # 如果数据库为空，从数据源获取
                logger.info("No A stocks in database, fetching from data source")
                stock_list = await self.source_router.route_to_best_source(
                    market=MarketType.A_STOCK, method_name="get_stock_list", status="L"
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
            logger.error(f"Failed to get A stock list: {e}")
            return []

    async def get_popular_stocks(self) -> List[Dict[str, Any]]:
        """
        获取热门A股列表

        Returns:
            热门A股列表
        """
        popular_symbols = [
            "600519.SH",  # 贵州茅台
            "000858.SZ",  # 五粮液
            "601318.SH",  # 中国平安
            "600036.SH",  # 招商银行
            "000333.SZ",  # 美的集团
            "600276.SH",  # 恒瑞医药
            "002415.SZ",  # 海康威视
            "601012.SH",  # 隆基绿能
            "300750.SZ",  # 宁德时代
            "600900.SH",  # 长江电力
        ]

        results = []
        for symbol in popular_symbols:
            stock_info = await self.get_stock_info(symbol)
            if stock_info:
                results.append(stock_info)

        return results

    async def get_index_stocks(self, index_code: str = "000300.SH") -> List[Dict[str, Any]]:
        """
        获取指数成分股

        Args:
            index_code: 指数代码（默认沪深300）

        Returns:
            成分股列表
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return []

            # 获取 TuShare 或 AkShare 适配器
            sources = await self.source_router.get_available_sources(MarketType.A_STOCK)

            for source in sources:
                if hasattr(source, "get_index_components"):
                    components = await source.get_index_components(index_code)
                    return components

            return []

        except Exception as e:
            logger.error(f"Failed to get index stocks for {index_code}: {e}")
            return []

    async def get_sector_stocks(self, sector: str) -> List[Dict[str, Any]]:
        """
        获取板块成分股

        Args:
            sector: 板块名称

        Returns:
            成分股列表
        """
        try:
            # 从数据库按行业查询
            stocks = await self.stock_info_repo.get_by_sector(
                market=MarketType.A_STOCK, sector=sector
            )
            return stocks if stocks else []

        except Exception as e:
            logger.error(f"Failed to get sector stocks for {sector}: {e}")
            return []

    async def get_macro_economic(self, indicator: str = "shibor") -> Optional[Dict[str, Any]]:
        """
        获取宏观经济数据

        Args:
            indicator: 指标名称（shibor, gdp, cpi, pmi 等）

        Returns:
            宏观经济数据
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return None

            # 获取数据源适配器
            sources = await self.source_router.get_available_sources(MarketType.A_STOCK)

            for source in sources:
                method_name = f"get_{indicator}"
                if hasattr(source, method_name):
                    method = getattr(source, method_name)
                    result = await method()
                    return result

            logger.warning(f"Macro economic indicator {indicator} not available")
            return None

        except Exception as e:
            logger.error(f"Failed to get macro economic data for {indicator}: {e}")
            return None

    async def get_top_list(self, trade_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取龙虎榜数据

        Args:
            trade_date: 交易日期（YYYYMMDD），默认最近交易日

        Returns:
            龙虎榜数据列表
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return []

            # 获取数据源适配器
            sources = await self.source_router.get_available_sources(MarketType.A_STOCK)

            for source in sources:
                if hasattr(source, "get_top_list"):
                    result = await source.get_top_list(trade_date=trade_date)
                    return result

            return []

        except Exception as e:
            logger.error(f"Failed to get top list: {e}")
            return []

    async def get_margin_trading(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取融资融券数据

        Args:
            symbol: 股票代码

        Returns:
            融资融券数据
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return None

            # 获取数据源适配器
            sources = await self.source_router.get_available_sources(MarketType.A_STOCK)

            for source in sources:
                if hasattr(source, "get_margin_trading"):
                    result = await source.get_margin_trading(symbol)
                    return result

            return None

        except Exception as e:
            logger.error(f"Failed to get margin trading for {symbol}: {e}")
            return None

    async def get_dividend_info(self, symbol: str) -> List[Dict[str, Any]]:
        """
        获取分红送股信息

        Args:
            symbol: 股票代码

        Returns:
            分红送股数据列表
        """
        try:
            if not self.source_router:
                logger.warning("Source router not configured")
                return []

            # 获取数据源适配器
            sources = await self.source_router.get_available_sources(MarketType.A_STOCK)

            for source in sources:
                if hasattr(source, "get_dividend"):
                    result = await source.get_dividend(symbol)
                    return result

            return []

        except Exception as e:
            logger.error(f"Failed to get dividend info for {symbol}: {e}")
            return []


# 导出
__all__ = ["AStockTool"]
