"""
Yahoo Finance 美股数据源适配器

支持美股股票列表、日线行情、分钟K线、财务数据、公司信息、实时行情等数据获取。
使用 yfinance 库与 Yahoo Finance API 交互。
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Callable
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


class YahooFinanceFieldMapper(FieldMapper):
    """Yahoo Finance 字段映射器"""

    @staticmethod
    def normalize_us_symbol(code: str) -> str:
        """
        标准化美股代码为 {code}.US 格式

        Args:
            code: 美股代码

        Returns:
            标准化代码，如 AAPL.US
        """
        if "." in code:
            if code.endswith(".US"):
                return code
            # Yahoo Finance uses .SS for Shanghai, convert to .SH
            if code.endswith(".SS"):
                return code[:-3] + ".SH"
            return code

        # 美股代码统一添加 .US 后缀
        return f"{code}.US"

    @staticmethod
    def map_stock_info(row: pd.Series, code: str = None) -> Dict[str, Any]:
        """
        映射 Yahoo Finance 股票基本信息

        Args:
            row: DataFrame 行
            code: 股票代码

        Returns:
            统一格式股票信息字典
        """
        return {
            "symbol": YahooFinanceFieldMapper.normalize_us_symbol(code),
            "market": MarketType.US_STOCK,
            "name": row.get("longName", row.get("shortName", "")),
            "industry": row.get("industry", ""),
            "sector": row.get("sector", ""),
            "listing_date": "",
            "exchange": row.get("exchange", ""),
            "status": "L",
            "data_source": "yahoo",
        }

    @staticmethod
    def map_stock_quote(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射 Yahoo Finance 行情数据

        Args:
            row: DataFrame 行
            symbol: 股票代码

        Returns:
            统一格式行情数据字典
        """
        # yfinance returns index as date
        trade_date = str(row.name) if hasattr(row, "name") else str(row.get("Date", ""))
        trade_date = FieldMapper.normalize_date(trade_date)

        return {
            "symbol": symbol,
            "market": MarketType.US_STOCK,
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
        映射 Yahoo Finance 利润表数据

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
                            "market": MarketType.US_STOCK,
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

    @staticmethod
    def map_financial_indicator(ticker: Any, symbol: str) -> Dict[str, Any]:
        """
        映射 Yahoo Finance 财务指标

        Args:
            ticker: yfinance Ticker 对象
            symbol: 股票代码

        Returns:
            统一格式财务指标字典列表
        """
        try:
            info = ticker.info
            if not info:
                return []

            return {
                "symbol": symbol,
                "market": MarketType.US_STOCK,
                "report_date": "",
                "publish_date": None,
                "roe": FieldMapper.safe_float(info.get("returnOnEquity")),
                "roa": FieldMapper.safe_float(info.get("returnOnAssets")),
                "debt_to_assets": None,
                "current_ratio": FieldMapper.safe_float(info.get("currentRatio")),
                "quick_ratio": None,
                "eps": FieldMapper.safe_float(info.get("trailingEps")),
                "bps": None,
                "gross_profit_margin": FieldMapper.safe_float(info.get("grossMargins")),
                "net_profit_margin": FieldMapper.safe_float(info.get("profitMargins")),
                "data_source": "yahoo",
            }
        except Exception as e:
            logger.warning(f"Failed to get financial indicators: {e}")
            return {}


class YahooFinanceAdapter(DataSourceAdapter):
    """Yahoo Finance 美股数据源适配器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if yf is None:
            raise ImportError("yfinance is not installed. Install with: pip install yfinance")

        self.source_name = "yahoo"
        self._session = None
        # 设置默认优先级（Yahoo Finance 是美股主要数据源）
        self._priority = 1

    async def _fetch_with_retry(
        self, fetch_func: Callable, *args, max_retries: int = 3, base_wait: int = 1, **kwargs
    ) -> Optional[Any]:
        """
        带指数退避的重试机制

        Args:
            fetch_func: 要执行的函数
            *args: 位置参数
            max_retries: 最大重试次数
            base_wait: 基础等待时间（秒）
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 所有重试都失败后抛出原始异常
        """
        for attempt in range(max_retries):
            try:
                return fetch_func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)
                # 检测速率限制错误
                if (
                    "Too Many Requests" in error_msg
                    or "429" in error_msg
                    or "Rate limited" in error_msg
                ):
                    if attempt < max_retries - 1:
                        # 指数退避：1s, 2s, 4s
                        wait_time = base_wait * (2**attempt)
                        logger.warning(
                            f"Yahoo Finance rate limited, waiting {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                # 如果不是速率限制，或者已达到最大重试次数，直接抛出
                raise
        return None

    def supports_market(self, market: MarketType) -> bool:
        return market == MarketType.US_STOCK

    async def test_connection(self) -> bool:
        try:
            # 测试获取一个知名股票的数据
            ticker = yf.Ticker("AAPL")
            info = ticker.info
            return info is not None and len(info) > 0
        except Exception as e:
            logger.error(f"Yahoo Finance connection test failed: {e}")
            return False

    async def get_stock_list(self, market: MarketType, status: str = "L") -> List[StockInfo]:
        """
        获取美股股票列表

        Yahoo Finance 没有直接的股票列表接口，
        这里返回一些知名美股作为示例。

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            股票信息列表
        """
        try:
            # 热门美股列表示例
            popular_stocks = [
                ("AAPL", "Apple Inc.", "Technology", "Consumer Electronics"),
                ("MSFT", "Microsoft Corporation", "Technology", "Software"),
                ("GOOGL", "Alphabet Inc.", "Technology", "Internet Services"),
                ("AMZN", "Amazon.com Inc.", "Consumer Cyclical", "Internet Retail"),
                ("TSLA", "Tesla Inc.", "Consumer Cyclical", "Auto Manufacturers"),
                ("META", "Meta Platforms Inc.", "Technology", "Internet Services"),
                ("NVDA", "NVIDIA Corporation", "Technology", "Semiconductors"),
                ("JPM", "JPMorgan Chase & Co.", "Financial Services", "Banks"),
                ("V", "Visa Inc.", "Financial Services", "Financial Data"),
                ("JNJ", "Johnson & Johnson", "Healthcare", "Pharmaceuticals"),
                ("WMT", "Walmart Inc.", "Consumer Defensive", "Discount Stores"),
                ("PG", "Procter & Gamble Co.", "Consumer Defensive", "Household Products"),
                ("MA", "Mastercard Inc.", "Financial Services", "Financial Data"),
                ("HD", "Home Depot Inc.", "Consumer Cyclical", "Home Improvement"),
                ("DIS", "Walt Disney Co.", "Communication Services", "Entertainment"),
                ("NFLX", "Netflix Inc.", "Communication Services", "Entertainment"),
                ("PYPL", "PayPal Holdings Inc.", "Financial Services", "Financial Software"),
                ("INTC", "Intel Corporation", "Technology", "Semiconductors"),
                ("CSCO", "Cisco Systems Inc.", "Technology", "Network Equipment"),
                ("ADBE", "Adobe Inc.", "Technology", "Software"),
            ]

            stock_list = []
            for code, name, sector, industry in popular_stocks:
                if status == "L":  # 仅返回上市股票
                    try:
                        stock_info = StockInfo(
                            symbol=YahooFinanceFieldMapper.normalize_us_symbol(code),
                            market=MarketType.US_STOCK,
                            name=name,
                            industry=industry,
                            sector=sector,
                            listing_date="",
                            exchange="",
                            status="L",
                            data_source=self.source_name,
                        )
                        stock_list.append(stock_info)
                    except Exception as e:
                        logger.warning(f"Failed to create stock info for {code}: {e}")
                        continue

            logger.info(f"Retrieved {len(stock_list)} stocks from Yahoo Finance")
            return stock_list

        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            return []

    async def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust_type: Optional[str] = None,
    ) -> List[StockQuote]:
        """
        获取美股日线行情

        Args:
            symbol: 股票代码（标准化格式，如 AAPL.US）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust_type: 复权类型（yahoo不支持，忽略）

        Returns:
            日线行情列表
        """
        try:
            # 去掉 .US 后缀获取原始代码
            code = symbol.replace(".US", "")

            # 设置默认日期范围
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            start = FieldMapper.normalize_date(start_date)
            end = FieldMapper.normalize_date(end_date)

            # 转换为 yfinance 需要的格式
            start_dt = datetime.strptime(start, "%Y%m%d")
            end_dt = datetime.strptime(end, "%Y%m%d")

            logger.info(f"Fetching daily quotes: symbol={code}, start={start}, end={end}")

            ticker = yf.Ticker(code)
            df = await self._fetch_with_retry(ticker.history, start=start_dt, end=end_dt)

            if df is None or df.empty:
                logger.warning(f"No daily quotes returned for {symbol} after retries")
                return []

            quotes = []
            for idx, row in df.iterrows():
                try:
                    mapped = YahooFinanceFieldMapper.map_stock_quote(row, symbol)
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
        获取美股分钟K线数据

        Args:
            symbol: 股票代码
            trade_date: 交易日期（YYYYMMDD）
            freq: K线频率（1m/5m/15m/30m/60m/90m）

        Returns:
            分钟K线数据列表
        """
        try:
            code = symbol.replace(".US", "")

            # Yahoo Finance 支持的间隔
            interval_map = {
                "1min": "1m",
                "5min": "5m",
                "15min": "15m",
                "30min": "30m",
                "60min": "1h",
                "90min": "90m",
            }
            interval = interval_map.get(freq, "1m")

            # 设置日期范围
            if trade_date:
                dt = datetime.strptime(trade_date, "%Y%m%d")
                start_dt = dt
                end_dt = dt + timedelta(days=1)
            else:
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=7)  # 默认获取最近7天

            logger.info(f"Fetching minute quotes: symbol={code}, interval={interval}")

            ticker = yf.Ticker(code)
            df = ticker.history(start=start_dt, end=end_dt, interval=interval, prepost=False)

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
                        market=MarketType.US_STOCK,
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
        获取美股财务报表

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）
            report_type: 报告类型

        Returns:
            财务报表列表
        """
        try:
            code = symbol.replace(".US", "")

            logger.info(f"Fetching financials: symbol={code}")

            ticker = yf.Ticker(code)
            financials_list = YahooFinanceFieldMapper.map_financial_income(ticker, symbol)

            if not financials_list:
                logger.warning(f"No financials returned for {symbol}")
                return []

            # 过滤报告日期
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
        """
        获取美股财务指标

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）

        Returns:
            财务指标列表
        """
        try:
            code = symbol.replace(".US", "")

            logger.info(f"Fetching financial indicators: symbol={code}")

            ticker = yf.Ticker(code)
            indicator_data = YahooFinanceFieldMapper.map_financial_indicator(ticker, symbol)

            if not indicator_data:
                logger.warning(f"No financial indicators returned for {symbol}")
                return []

            try:
                indicator = StockFinancialIndicator(**indicator_data)
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
        获取美股公司信息

        Args:
            symbol: 股票代码

        Returns:
            公司详细信息，未找到返回None
        """
        try:
            code = symbol.replace(".US", "")

            logger.info(f"Fetching company info: symbol={code}")

            ticker = yf.Ticker(code)
            info = await self._fetch_with_retry(lambda: ticker.info, max_retries=3, base_wait=1)

            if not info:
                logger.warning(f"No company info returned for {symbol} after retries")
                return None

            company = StockCompany(
                symbol=symbol,
                market=MarketType.US_STOCK,
                company_name=info.get("longName", info.get("shortName", "")),
                company_name_en=info.get("longName", ""),
                industry=info.get("industry", ""),
                sector=info.get("sector", ""),
                listing_date="",
                contact={
                    "website": info.get("website"),
                    "phone": info.get("phone"),
                    "address": info.get("address1"),
                },
                business={
                    "business_summary": info.get("longBusinessSummary"),
                    "industry": info.get("industry"),
                    "sector": info.get("sector"),
                },
                capital_structure={
                    "market_cap": info.get("marketCap"),
                    "enterprise_value": info.get("enterpriseValue"),
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
        获取美股实时行情

        Args:
            symbol: 股票代码

        Returns:
            实时行情字典
        """
        try:
            code = symbol.replace(".US", "")

            logger.info(f"Fetching realtime quote: symbol={code}")

            ticker = yf.Ticker(code)
            info = ticker.info

            if not info:
                logger.warning(f"No realtime quote returned for {symbol}")
                return None

            quote = {
                "symbol": symbol,
                "market": MarketType.US_STOCK,
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

    async def get_stock_dividends(self, symbol: str) -> List[Dict[str, Any]]:
        """
        获取美股股息数据

        Args:
            symbol: 股票代码

        Returns:
            股息数据列表
        """
        try:
            code = symbol.replace(".US", "")

            logger.info(f"Fetching dividends: symbol={code}")

            ticker = yf.Ticker(code)
            dividends = ticker.dividends

            if dividends is None or dividends.empty:
                logger.warning(f"No dividends returned for {symbol}")
                return []

            result = []
            for date, value in dividends.items():
                result.append(
                    {
                        "symbol": symbol,
                        "ex_dividend_date": str(date.date()),
                        "dividend_amount": float(value),
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(result)} dividends for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Failed to get dividends: {e}")
            return []

    async def get_stock_splits(self, symbol: str) -> List[Dict[str, Any]]:
        """
        获取美股股票拆分数据

        Args:
            symbol: 股票代码

        Returns:
            股票拆分数据列表
        """
        try:
            code = symbol.replace(".US", "")

            logger.info(f"Fetching splits: symbol={code}")

            ticker = yf.Ticker(code)
            splits = ticker.splits

            if splits is None or splits.empty:
                logger.warning(f"No splits returned for {symbol}")
                return []

            result = []
            for date, ratio in splits.items():
                result.append(
                    {
                        "symbol": symbol,
                        "split_date": str(date.date()),
                        "split_ratio": float(ratio),
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(result)} splits for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Failed to get splits: {e}")
            return []
