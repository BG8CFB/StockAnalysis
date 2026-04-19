"""
AkShare 美股数据源适配器

支持美股行情、财务数据、公司信息等数据获取。
使用 AkShare 库获取美股数据。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None
    logging.warning("akshare not installed. Install with: pip install akshare")

from core.market_data.models import (
    MarketType,
    StockInfo,
    StockKLine,
    StockQuote,
)
from core.market_data.sources.base import DataSourceAdapter
from core.market_data.tools.field_mapper import FieldMapper

logger = logging.getLogger(__name__)


class AkShareUSFieldMapper(FieldMapper):
    """AkShare 美股字段映射器"""

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
            return code

        # 美股代码统一添加 .US 后缀
        return f"{code}.US"

    @staticmethod
    def map_stock_info(row: pd.Series) -> Dict[str, Any]:
        """
        映射 AkShare 美股股票信息

        Args:
            row: DataFrame 行

        Returns:
            统一格式股票信息字典
        """
        code = str(row.get("代码", ""))
        symbol = AkShareUSFieldMapper.normalize_us_symbol(code)

        return {
            "symbol": symbol,
            "market": MarketType.US_STOCK,
            "name": row.get("名称", ""),
            "industry": row.get("行业", None),
            "sector": None,
            "listing_date": "",
            "exchange": "",
            "status": "L",
            "data_source": "akshare",
        }

    @staticmethod
    def map_stock_quote(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射 AkShare 美股行情数据

        Args:
            row: DataFrame 行
            symbol: 股票代码

        Returns:
            统一格式行情数据字典
        """
        trade_date = str(row.get("日期", ""))
        trade_date = FieldMapper.normalize_date(trade_date)

        return {
            "symbol": symbol,
            "market": MarketType.US_STOCK,
            "trade_date": trade_date,
            "open": FieldMapper.safe_float(row.get("开盘")),
            "high": FieldMapper.safe_float(row.get("最高")),
            "low": FieldMapper.safe_float(row.get("最低")),
            "close": FieldMapper.safe_float(row.get("收盘")),
            "pre_close": None,
            "volume": FieldMapper.safe_int(row.get("成交量")),
            "amount": FieldMapper.safe_float(row.get("成交额")),
            "change": FieldMapper.safe_float(row.get("涨跌额")),
            "change_pct": FieldMapper.safe_float(row.get("涨跌幅")),
            "turnover_rate": None,
            "data_source": "akshare",
        }


class AkShareUSAdapter(DataSourceAdapter):
    """AkShare 美股数据源适配器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if ak is None:
            raise ImportError("akshare is not installed. Install with: pip install akshare")

        self.source_name = "akshare"
        # 设置默认优先级（AkShare 作为美股备用数据源）
        self._priority = 2

    def supports_market(self, market: MarketType) -> bool:
        return market == MarketType.US_STOCK

    async def test_connection(self) -> bool:
        try:
            df = ak.stock_us_spot_em()
            return df is not None and len(df) > 0
        except Exception as e:
            logger.error(f"AkShare US connection test failed: {e}")
            return False

    async def get_stock_list(self, market: MarketType, status: str = "L") -> List[StockInfo]:
        """
        获取美股股票列表

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            股票信息列表
        """
        try:
            logger.info("Fetching US stock list from AkShare")

            df = ak.stock_us_spot_em()

            if df is None or df.empty:
                logger.warning("No US stock list returned from AkShare")
                return []

            stock_list = []
            for _, row in df.iterrows():
                try:
                    mapped = AkShareUSFieldMapper.map_stock_info(row)
                    if status == "L":
                        stock_info = StockInfo(**mapped)
                        stock_list.append(stock_info)
                except Exception as e:
                    logger.warning(f"Failed to parse stock: {e}")
                    continue

            logger.info(f"Retrieved {len(stock_list)} US stocks from AkShare")
            return stock_list

        except Exception as e:
            logger.error(f"Failed to get US stock list: {e}")
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
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型

        Returns:
            日线行情列表
        """
        try:
            code = symbol.replace(".US", "")

            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            logger.info(f"Fetching US daily quotes from AkShare: symbol={code}")

            # AkShare 美股历史数据接口
            df = ak.stock_us_hist(
                symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=""
            )

            if df is None or df.empty:
                logger.warning(f"No daily quotes returned for {symbol}")
                return []

            quotes = []
            for _, row in df.iterrows():
                try:
                    mapped = AkShareUSFieldMapper.map_stock_quote(row, symbol)
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
            freq: K线频率（1m/5m/15m/30m/60m）

        Returns:
            分钟K线数据列表
        """
        try:
            code = symbol.replace(".US", "")

            period_map = {
                "1min": "1",
                "5min": "5",
                "15min": "15",
                "30min": "30",
                "60min": "60",
            }
            period = period_map.get(freq, "1")

            logger.info(f"Fetching US minute quotes from AkShare: symbol={code}, period={period}")

            df = ak.stock_us_hist_min_em(symbol=code, period=period)

            if df is None or df.empty:
                logger.warning(f"No minute quotes returned for {symbol}")
                return []

            klines = []
            for _, row in df.iterrows():
                try:
                    trade_dt = str(row.get("时间", ""))

                    if trade_date and trade_dt:
                        date_part = trade_dt[:10].replace("-", "")
                        if date_part != trade_date:
                            continue

                    if len(trade_dt) > 8:
                        trade_dt = trade_dt.replace("-", "").replace(" ", "").replace(":", "")

                    kline = StockKLine(
                        symbol=symbol,
                        market=MarketType.US_STOCK,
                        trade_date=trade_dt[:8] if len(trade_dt) >= 8 else trade_dt,
                        open=float(row.get("开盘", 0)),
                        high=float(row.get("最高", 0)),
                        low=float(row.get("最低", 0)),
                        close=float(row.get("收盘", 0)),
                        volume=int(row.get("成交量", 0)),
                        amount=float(row.get("成交额", 0)),
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
    ) -> List[Any]:
        """AkShare 美股财务数据支持有限"""
        logger.warning("AkShare has limited US financial data support")
        return []

    async def get_financial_indicators(
        self, symbol: str, report_date: Optional[str] = None
    ) -> List[Any]:
        """AkShare 美股财务指标支持有限"""
        logger.warning("AkShare has limited US financial indicator support")
        return []

    async def get_stock_company(self, symbol: str) -> Optional[Any]:
        """AkShare 美股公司信息支持有限"""
        logger.warning("AkShare has limited US company info support")
        return None

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

            logger.info(f"Fetching US realtime quote from AkShare: symbol={code}")

            df = ak.stock_us_spot_em()

            if df is None or df.empty:
                logger.warning(f"No realtime quote returned for {symbol}")
                return None

            # 查找对应股票
            stock_df = df[df["代码"] == code]
            if stock_df.empty:
                logger.warning(f"Stock {code} not found in US spot data")
                return None

            row = stock_df.iloc[0]

            quote = {
                "symbol": symbol,
                "market": MarketType.US_STOCK,
                "price": FieldMapper.safe_float(row.get("最新价")),
                "change": FieldMapper.safe_float(row.get("涨跌额")),
                "change_pct": FieldMapper.safe_float(row.get("涨跌幅")),
                "open": FieldMapper.safe_float(row.get("今开")),
                "high": FieldMapper.safe_float(row.get("最高")),
                "low": FieldMapper.safe_float(row.get("最低")),
                "close": FieldMapper.safe_float(row.get("昨收")),
                "volume": FieldMapper.safe_int(row.get("成交量")),
                "amount": FieldMapper.safe_float(row.get("成交额")),
                "data_source": self.source_name,
            }

            logger.info(f"Retrieved realtime quote for {symbol}")
            return quote

        except Exception as e:
            logger.error(f"Failed to get realtime quote: {e}")
            return None
