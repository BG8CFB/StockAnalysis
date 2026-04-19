"""
市场数据模型单元测试
"""

from core.market_data.models import Exchange, MarketType, StockInfo, StockQuote


class TestMarketType:
    """MarketType 枚举测试"""

    def test_market_types_exist(self) -> None:
        assert MarketType.A_STOCK is not None
        assert MarketType.US_STOCK is not None
        assert MarketType.HK_STOCK is not None

    def test_market_type_values(self) -> None:
        assert MarketType.A_STOCK.value == "A_STOCK"
        assert MarketType.US_STOCK.value == "US_STOCK"
        assert MarketType.HK_STOCK.value == "HK_STOCK"


class TestStockQuoteModel:
    """StockQuote 模型测试"""

    def test_create_stock_quote(self) -> None:
        quote = StockQuote(
            symbol="600519.SS",
            market=MarketType.A_STOCK,
            trade_date="20240101",
            open=1800.0,
            high=1850.0,
            low=1790.0,
            close=1830.0,
            volume=100000,
            amount=183000000.0,
            turnover_rate=None,
            change_pct=None,
            pre_close=None,
            data_source="test",
        )  # type: ignore[call-arg]
        assert quote.symbol == "600519.SS"
        assert quote.close == 1830.0
        assert quote.volume == 100000

    def test_stock_quote_optional_fields(self) -> None:
        """可选字段可以省略"""
        quote = StockQuote(
            symbol="600519.SS",
            market=MarketType.A_STOCK,
            trade_date="20240101",
            open=1800.0,
            high=1850.0,
            low=1790.0,
            close=1830.0,
            volume=100000,
            amount=183000000.0,
            turnover_rate=None,
            change_pct=None,
            pre_close=None,
            data_source="test",
        )  # type: ignore[call-arg]
        assert quote.turnover_rate is None
        assert quote.change_pct is None


class TestStockInfoModel:
    """StockInfo 模型测试"""

    def test_create_stock_info(self) -> None:
        info = StockInfo(
            symbol="600519.SS",
            code="600519",
            market=MarketType.A_STOCK,
            name="贵州茅台",
            industry="白酒",
            list_date="20010827",
            exchange=Exchange.SSE,
            area=None,
            sector=None,
            fullname=None,
            enname=None,
            description=None,
            listing_date=None,
            status=None,
            is_hs=None,
            data_source="test",
        )  # type: ignore[call-arg]
        assert info.name == "贵州茅台"
        assert info.symbol == "600519.SS"
        assert info.code == "600519"
