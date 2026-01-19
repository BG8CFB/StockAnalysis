"""
Yahoo Finance 港股数据源适配器

支持港股股票列表、日线行情、分钟K线、财务数据、公司信息、实时行情等数据获取。
使用 yfinance 库与 Yahoo Finance API 交互。
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None
    logging.warning("yfinance not installed. Install with: pip install yfinance")

from core.market_data.sources.base import DataSourceAdapter
from core.market_data.models import (
    StockInfo,
    StockQuote,
    StockKLine,
    StockFinancial,
    StockFinancialIndicator,
    StockCompany,
    MarketType,
)
from core.market_data.tools.field_mapper import FieldMapper

logger = logging.getLogger(__name__)


class YahooHKFieldMapper(FieldMapper):
    """Yahoo Finance 港股字段映射器"""

    @staticmethod
    def normalize_hk_symbol(code: str) -> str:
        """
        标准化港股代码为 {code}.HK 格式

        Args:
            code: 港股代码

        Returns:
            标准化代码，如 0700.HK
        """
        if "." in code:
            return code

        # 港股代码需要补0到4位
        code = code.zfill(4)
        return f"{code}.HK"

    @staticmethod
    def map_stock_quote(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射 Yahoo Finance 港股行情数据

        Args:
            row: DataFrame 行
            symbol: 股票代码

        Returns:
            统一格式行情数据字典
        """
        trade_date = str(row.name) if hasattr(row, "name") else str(row.get("Date", ""))
        trade_date = FieldMapper.normalize_date(trade_date)

        return {
            "symbol": symbol,
            "market": MarketType.HK_STOCK,
            "trade_date": trade_date,
            "open": FieldMapper.safe_float(row.get("Open")),
            "high": FieldMapper.safe_float(row.get("High")),
            "low": FieldMapper.safe_float(row.get("Low")),
            "close": FieldMapper.safe_float(row.get("Close")),
            "pre_close": None,
            "volume": FieldMapper.safe_int(row.get("Volume")),
            "amount": None,
            "change": None,
            "change_pct": None,
            "turnover_rate": None,
            "data_source": "yahoo",
        }

    @staticmethod
    def map_financial_income(ticker: Any, symbol: str) -> Dict[str, Any]:
        """
        映射 Yahoo Finance 港股利润表数据

        Args:
            ticker: yfinance Ticker 对象
            symbol: 股票代码

        Returns:
            统一格式财务数据字典列表
        """
        try:
            financials = ticker.financials
            if financials is None or financials.empty:
                return []

            results = []
            for date in financials.columns:
                try:
                    date_str = str(date)[:10]
                    report_date = FieldMapper.normalize_date(date_str)

                    income_statement = {
                        "total_revenue": FieldMapper.safe_float(
                            financials.loc["Total Revenue", date]
                        )
                        if "Total Revenue" in financials.index
                        else None,
                        "revenue": FieldMapper.safe_float(financials.loc["Total Revenue", date])
                        if "Total Revenue" in financials.index
                        else None,
                        "operating_cost": None,
                        "net_income": FieldMapper.safe_float(financials.loc["Net Income", date])
                        if "Net Income" in financials.index
                        else None,
                        "basic_eps": None,
                        "operating_profit": FieldMapper.safe_float(
                            financials.loc["Operating Income", date]
                        )
                        if "Operating Income" in financials.index
                        else None,
                    }

                    results.append(
                        {
                            "symbol": symbol,
                            "market": MarketType.HK_STOCK,
                            "report_date": report_date,
                            "report_type": "quarterly",
                            "publish_date": None,
                            "income_statement": income_statement,
                            "balance_sheet": {},
                            "cash_flow": {},
                            "data_source": "yahoo",
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse financial row: {e}")
                    continue

            return results
        except Exception as e:
            logger.warning(f"Failed to get income statement: {e}")
            return []


class YahooHKAdapter(DataSourceAdapter):
    """Yahoo Finance 港股数据源适配器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if yf is None:
            raise ImportError("yfinance is not installed. Install with: pip install yfinance")

        self.source_name = "yahoo"
        # 设置默认优先级（Yahoo Finance 作为港股备用数据源）
        self._priority = 2

    def supports_market(self, market: MarketType) -> bool:
        return market == MarketType.HK_STOCK

    async def test_connection(self) -> bool:
        try:
            ticker = yf.Ticker("0700.HK")
            info = ticker.info
            return info is not None and len(info) > 0
        except Exception as e:
            logger.error(f"Yahoo Finance HK connection test failed: {e}")
            return False

    async def get_stock_list(self, market: MarketType, status: str = "L") -> List[StockInfo]:
        """
        获取港股股票列表

        Yahoo Finance 没有直接的港股列表接口，
        这里返回一些知名港股作为示例。

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            股票信息列表
        """
        try:
            # 热门港股列表示例
            popular_stocks = [
                ("0700", "Tencent Holdings Limited", "Technology", "Internet Services"),
                ("9988", "Alibaba Group Holding Limited", "Technology", "Internet Services"),
                (
                    "0941",
                    "China Mobile Limited",
                    "Telecommunications",
                    "Wireless Telecommunications",
                ),
                ("1299", "AIA Group Limited", "Financial Services", "Insurance"),
                ("0939", "CCB", "Financial Services", "Banks"),
                ("1398", "ICBC", "Financial Services", "Banks"),
                ("2318", "Ping An Insurance", "Financial Services", "Insurance"),
                ("0883", "CNOOC", "Energy", "Oil & Gas"),
                ("0388", "HK Exchanges", "Financial Services", "Financial Data"),
                ("1023", "HSB Holdings", "Industrials", "Real Estate"),
                ("0005", "HSBC Holdings", "Financial Services", "Banks"),
                ("0267", "CITIC", "Financial Services", "Investment Banking"),
                ("0883", "Sinopec", "Energy", "Oil & Gas"),
                ("0386", "Sino Corp", "Energy", "Oil & Gas"),
                ("0960", "Longyuan Power", "Utilities", "Electric Utilities"),
                ("0175", "Geely Auto", "Consumer Cyclical", "Auto Manufacturers"),
                ("0202", "ESPRIT", "Consumer Cyclical", "Apparel Retail"),
                ("1177", "Sino Biopharm", "Healthcare", "Pharmaceuticals"),
                ("0669", "Techtronic Ind", "Industrials", "Tools"),
                ("0688", "China Overseas", "Real Estate", "Real Estate"),
            ]

            stock_list = []
            for code, name, sector, industry in popular_stocks:
                if status == "L":
                    try:
                        stock_info = StockInfo(
                            symbol=YahooHKFieldMapper.normalize_hk_symbol(code),
                            market=MarketType.HK_STOCK,
                            name=name,
                            industry=industry,
                            sector=sector,
                            listing_date="",
                            exchange="HKEX",
                            status="L",
                            data_source=self.source_name,
                        )
                        stock_list.append(stock_info)
                    except Exception as e:
                        logger.warning(f"Failed to create stock info for {code}: {e}")
                        continue

            logger.info(f"Retrieved {len(stock_list)} HK stocks from Yahoo Finance")
            return stock_list

        except Exception as e:
            logger.error(f"Failed to get HK stock list: {e}")
            return []

    async def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust_type: Optional[str] = None,
    ) -> List[StockQuote]:
        """
        获取港股日线行情

        Args:
            symbol: 股票代码（标准化格式，如 0700.HK）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust_type: 复权类型

        Returns:
            日线行情列表
        """
        try:
            code = symbol.replace(".HK", "")
            code = code.zfill(4)
            ticker_symbol = f"{code}.HK"

            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            start = FieldMapper.normalize_date(start_date)
            end = FieldMapper.normalize_date(end_date)

            start_dt = datetime.strptime(start, "%Y%m%d")
            end_dt = datetime.strptime(end, "%Y%m%d")

            logger.info(
                f"Fetching HK daily quotes: symbol={ticker_symbol}, start={start}, end={end}"
            )

            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start_dt, end=end_dt)

            if df is None or df.empty:
                logger.warning(f"No daily quotes returned for {symbol}")
                return []

            quotes = []
            for idx, row in df.iterrows():
                try:
                    mapped = YahooHKFieldMapper.map_stock_quote(row, symbol)
                    quote = StockQuote(**mapped)
                    quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Failed to parse quote: {e}")
                    continue

            logger.info(f"Retrieved {len(quotes)} quotes for {symbol}")
            return quotes

        except Exception as e:
            logger.error(f"Failed to get daily quotes: {e}")
            raise

    async def get_minute_quotes(
        self, symbol: str, trade_date: Optional[str] = None, freq: str = "1min"
    ) -> List[StockKLine]:
        """
        获取港股分钟K线数据

        Args:
            symbol: 股票代码
            trade_date: 交易日期（YYYYMMDD）
            freq: K线频率（1m/5m/15m/30m/60m）

        Returns:
            分钟K线数据列表
        """
        try:
            code = symbol.replace(".HK", "")
            code = code.zfill(4)
            ticker_symbol = f"{code}.HK"

            interval_map = {
                "1min": "1m",
                "5min": "5m",
                "15min": "15m",
                "30min": "30m",
                "60min": "1h",
            }
            interval = interval_map.get(freq, "1m")

            if trade_date:
                dt = datetime.strptime(trade_date, "%Y%m%d")
                start_dt = dt
                end_dt = dt + timedelta(days=1)
            else:
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=7)

            logger.info(f"Fetching HK minute quotes: symbol={ticker_symbol}, interval={interval}")

            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start_dt, end=end_dt, interval=interval)

            if df is None or df.empty:
                logger.warning(f"No minute quotes returned for {symbol}")
                return []

            klines = []
            for idx, row in df.iterrows():
                try:
                    trade_dt = str(idx)
                    if len(trade_dt) > 10:
                        trade_dt = trade_dt.replace("-", "").replace(" ", "").replace(":", "")

                    kline = StockKLine(
                        symbol=symbol,
                        market=MarketType.HK_STOCK,
                        trade_date=trade_dt[:8] if len(trade_dt) >= 8 else trade_dt,
                        open=float(row["Open"]) if pd.notna(row["Open"]) else 0,
                        high=float(row["High"]) if pd.notna(row["High"]) else 0,
                        low=float(row["Low"]) if pd.notna(row["Low"]) else 0,
                        close=float(row["Close"]) if pd.notna(row["Close"]) else 0,
                        volume=int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
                        amount=None,
                        data_source=self.source_name,
                    )
                    klines.append(kline)
                except Exception as e:
                    logger.warning(f"Failed to parse kline: {e}")
                    continue

            logger.info(f"Retrieved {len(klines)} minute klines for {symbol}")
            return klines

        except Exception as e:
            logger.error(f"Failed to get minute quotes: {e}")
            raise

    async def get_stock_financials(
        self, symbol: str, report_date: Optional[str] = None, report_type: Optional[str] = None
    ) -> List[StockFinancial]:
        """
        获取港股财务报表

        Args:
            symbol: 股票代码
            report_date: 报告期
            report_type: 报告类型

        Returns:
            财务报表列表
        """
        try:
            code = symbol.replace(".HK", "")
            code = code.zfill(4)
            ticker_symbol = f"{code}.HK"

            logger.info(f"Fetching HK financials: symbol={ticker_symbol}")

            ticker = yf.Ticker(ticker_symbol)
            financials_list = YahooHKFieldMapper.map_financial_income(ticker, symbol)

            if not financials_list:
                logger.warning(f"No financials returned for {symbol}")
                return []

            if report_date:
                financials_list = [
                    f for f in financials_list if f.get("report_date") == report_date
                ]

            result = []
            for fin_data in financials_list:
                try:
                    financial = StockFinancial(**fin_data)
                    result.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to create financial: {e}")
                    continue

            logger.info(f"Retrieved {len(result)} financials for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Failed to get financials: {e}")
            return []

    async def get_financial_indicators(
        self, symbol: str, report_date: Optional[str] = None
    ) -> List[StockFinancialIndicator]:
        """获取港股财务指标（Yahoo Finance 支持）"""
        try:
            code = symbol.replace(".HK", "")
            code = code.zfill(4)
            ticker_symbol = f"{code}.HK"

            logger.info(f"Fetching HK financial indicators: symbol={ticker_symbol}")

            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            if not info:
                logger.warning(f"No financial indicators returned for {symbol}")
                return []

            try:
                indicator = StockFinancialIndicator(
                    symbol=symbol,
                    market=MarketType.HK_STOCK,
                    report_date="",
                    publish_date=None,
                    roe=FieldMapper.safe_float(info.get("returnOnEquity")),
                    roa=FieldMapper.safe_float(info.get("returnOnAssets")),
                    debt_to_assets=None,
                    current_ratio=FieldMapper.safe_float(info.get("currentRatio")),
                    quick_ratio=None,
                    eps=FieldMapper.safe_float(info.get("trailingEps")),
                    bps=None,
                    gross_profit_margin=FieldMapper.safe_float(info.get("grossMargins")),
                    net_profit_margin=FieldMapper.safe_float(info.get("profitMargins")),
                    data_source=self.source_name,
                )
                logger.info(f"Retrieved financial indicator for {symbol}")
                return [indicator]
            except Exception as e:
                logger.warning(f"Failed to create financial indicator: {e}")
                return []

        except Exception as e:
            logger.error(f"Failed to get financial indicators: {e}")
            return []

    async def get_stock_company(self, symbol: str) -> Optional[StockCompany]:
        """
        获取港股公司信息

        Args:
            symbol: 股票代码

        Returns:
            公司详细信息
        """
        try:
            code = symbol.replace(".HK", "")
            code = code.zfill(4)
            ticker_symbol = f"{code}.HK"

            logger.info(f"Fetching HK company info: symbol={ticker_symbol}")

            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            if not info:
                logger.warning(f"No company info returned for {symbol}")
                return None

            company = StockCompany(
                symbol=symbol,
                market=MarketType.HK_STOCK,
                company_name=info.get("longName", info.get("shortName", "")),
                company_name_en=info.get("longName", ""),
                industry=info.get("industry", ""),
                sector=info.get("sector", ""),
                listing_date="",
                contact={
                    "website": info.get("website"),
                },
                business={
                    "business_summary": info.get("longBusinessSummary"),
                    "industry": info.get("industry"),
                    "sector": info.get("sector"),
                },
                capital_structure={
                    "market_cap": info.get("marketCap"),
                },
                data_source=self.source_name,
            )

            logger.info(f"Retrieved company info for {symbol}")
            return company

        except Exception as e:
            logger.error(f"Failed to get company info: {e}")
            raise

    async def get_realtime_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取港股实时行情

        Args:
            symbol: 股票代码

        Returns:
            实时行情字典
        """
        try:
            code = symbol.replace(".HK", "")
            code = code.zfill(4)
            ticker_symbol = f"{code}.HK"

            logger.info(f"Fetching HK realtime quote: symbol={ticker_symbol}")

            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            if not info:
                logger.warning(f"No realtime quote returned for {symbol}")
                return None

            quote = {
                "symbol": symbol,
                "market": MarketType.HK_STOCK,
                "price": FieldMapper.safe_float(
                    info.get("currentPrice") or info.get("regularMarketPrice")
                ),
                "change": FieldMapper.safe_float(info.get("regularMarketChange")),
                "change_pct": FieldMapper.safe_float(info.get("regularMarketChangePercent")),
                "open": FieldMapper.safe_float(info.get("regularMarketOpen")),
                "high": FieldMapper.safe_float(info.get("regularMarketDayHigh")),
                "low": FieldMapper.safe_float(info.get("regularMarketDayLow")),
                "close": FieldMapper.safe_float(info.get("previousClose")),
                "volume": FieldMapper.safe_int(info.get("regularMarketVolume")),
                "market_cap": info.get("marketCap"),
                "data_source": self.source_name,
            }

            logger.info(f"Retrieved realtime quote for {symbol}")
            return quote

        except Exception as e:
            logger.error(f"Failed to get realtime quote: {e}")
            return None
