"""
AkShare 港股数据源适配器

支持港股行情、港股通成分股、资金流向、持股明细、指数数据等。
使用 AkShare 库获取港股数据。
"""

import logging
from datetime import datetime, timedelta
import asyncio
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None
    logging.warning("akshare not installed. Install with: pip install akshare")

from core.market_data.models import (
    MarketType,
    StockInfo,
    StockQuote,
)
from core.market_data.sources.base import DataSourceAdapter
from core.market_data.tools.field_mapper import FieldMapper

logger = logging.getLogger(__name__)


class AkShareHKFieldMapper(FieldMapper):
    """AkShare 港股字段映射器"""

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
        code = str(code).zfill(4)
        return f"{code}.HK"

    @staticmethod
    def map_stock_spot(row: pd.Series) -> Dict[str, Any]:
        """
        映射 AkShare 港股实时行情数据

        Args:
            row: DataFrame 行

        Returns:
            统一格式股票信息字典
        """
        code = str(row.get("代码", ""))
        symbol = AkShareHKFieldMapper.normalize_hk_symbol(code)

        return {
            "symbol": symbol,
            "market": MarketType.HK_STOCK,
            "name": row.get("名称", ""),
            "industry": None,
            "sector": None,
            "listing_date": "",
            "exchange": "HKEX",
            "status": "L",
            "data_source": "akshare",
        }

    @staticmethod
    def map_stock_quote(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射 AkShare 港股行情数据

        Args:
            row: DataFrame 行
            symbol: 股票代码

        Returns:
            统一格式行情数据字典
        """
        trade_date = str(row.get("date", ""))
        trade_date = FieldMapper.normalize_date(trade_date)

        return {
            "symbol": symbol,
            "market": MarketType.HK_STOCK,
            "trade_date": trade_date,
            "open": FieldMapper.safe_float(row.get("open")),
            "high": FieldMapper.safe_float(row.get("high")),
            "low": FieldMapper.safe_float(row.get("low")),
            "close": FieldMapper.safe_float(row.get("close")),
            "pre_close": None,
            "volume": FieldMapper.safe_int(row.get("volume")),
            "amount": FieldMapper.safe_float(row.get("amount")),
            "change": FieldMapper.safe_float(row.get("change")),
            "change_pct": FieldMapper.safe_float(row.get("percent")),
            "turnover_rate": None,
            "data_source": "akshare",
        }


class AkShareHKAdapter(DataSourceAdapter):
    """AkShare 港股数据源适配器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if ak is None:
            raise ImportError("akshare is not installed. Install with: pip install akshare")

        self.source_name = "akshare"
        # 设置默认优先级（AkShare 是港股主要数据源）
        self._priority = 1

    async def _fetch_with_retry(
        self,
        fetch_func: Callable[..., Any],
        *args: Any,
        max_retries: int = 3,
        base_wait: int = 2,
        **kwargs: Any,
    ) -> Optional[Any]:
        """带指数退避的重试机制"""
        from requests.exceptions import ConnectionError, RequestException
        for attempt in range(max_retries):
            try:
                return await asyncio.to_thread(fetch_func, *args, **kwargs)
            except (ConnectionError, RequestException) as e:
                error_msg = str(e)
                if any(
                    keyword in error_msg
                    for keyword in [
                        "Connection aborted",
                        "RemoteDisconnected",
                        "Connection reset",
                        "Timeout",
                        "网络",
                    ]
                ):
                    if attempt < max_retries - 1:
                        wait_time = base_wait * (2**attempt)
                        logger.warning(
                            f"AkShare HK network error, waiting {wait_time}s "
                            f"before retry (attempt {attempt + 1}/{max_retries}): {error_msg}"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                raise
            except Exception as e:
                raise
        return None

    def supports_market(self, market: MarketType) -> bool:
        return market == MarketType.HK_STOCK

    async def test_connection(self) -> bool:
        try:
            df = await self._fetch_with_retry(ak.stock_hk_spot_em, max_retries=2, base_wait=1)
            return df is not None and len(df) > 0
        except Exception as e:
            logger.error(f"AkShare HK connection test failed: {e}")
            return False

    async def get_stock_list(self, market: MarketType, status: str = "L") -> List[StockInfo]:
        """
        获取港股股票列表

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            股票信息列表
        """
        try:
            logger.info("Fetching HK stock list from AkShare")

            df = ak.stock_hk_spot_em()

            if df is None or df.empty:
                logger.warning("No HK stock list returned from AkShare")
                return []

            stock_list = []
            for _, row in df.iterrows():
                try:
                    mapped = AkShareHKFieldMapper.map_stock_spot(row)
                    if status == "L":
                        stock_info = StockInfo(**mapped)
                        stock_list.append(stock_info)
                except Exception as e:
                    logger.warning(f"Failed to parse stock: {e}")
                    continue

            logger.info(f"Retrieved {len(stock_list)} HK stocks from AkShare")
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
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型

        Returns:
            日线行情列表
        """
        try:
            code = symbol.replace(".HK", "")
            code = code.zfill(4)

            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            logger.info(f"Fetching HK daily quotes from AkShare: symbol={code}")

            # AkShare 港股历史数据接口
            df = ak.stock_hk_hist(
                symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=""
            )

            if df is None or df.empty:
                logger.warning(f"No daily quotes returned for {symbol}")
                return []

            quotes = []
            for _, row in df.iterrows():
                try:
                    mapped = AkShareHKFieldMapper.map_stock_quote(row, symbol)
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

    async def get_stock_financials(
        self, symbol: str, report_date: Optional[str] = None, report_type: Optional[str] = None
    ) -> List[Any]:
        """AkShare 港股财务数据支持有限"""
        logger.warning("AkShare has limited HK financial data support")
        return []

    async def get_financial_indicators(
        self, symbol: str, report_date: Optional[str] = None
    ) -> List[Any]:
        """AkShare 港股财务指标支持有限"""
        logger.warning("AkShare has limited HK financial indicator support")
        return []

    async def get_stock_company(self, symbol: str) -> Optional[Any]:
        """AkShare 港股公司信息支持有限"""
        logger.warning("AkShare has limited HK company info support")
        return None

    async def get_hk_stock_ggt_components(self) -> List[Dict[str, Any]]:
        """
        获取港股通成分股

        Returns:
            港股通成分股列表
        """
        try:
            logger.info("Fetching HK Connect stock list from AkShare")

            df = ak.stock_hk_ggt_components_em()

            if df is None or df.empty:
                logger.warning("No HK Connect stocks returned")
                return []

            result = []
            for _, row in df.iterrows():
                code = str(row.get("港股代码", ""))
                symbol = AkShareHKFieldMapper.normalize_hk_symbol(code)

                result.append(
                    {
                        "symbol": symbol,
                        "name": row.get("港股名称", ""),
                        "sector": row.get("所属行业", ""),
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(result)} HK Connect stocks")
            return result

        except Exception as e:
            logger.error(f"Failed to get HK Connect stocks: {e}")
            return []

    async def get_hk_stock_money_flow(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取港股通资金流向

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            资金流向数据列表
        """
        try:
            logger.info("Fetching HK Connect money flow from AkShare")

            df = ak.stock_hsgt_hist_em()

            if df is None or df.empty:
                logger.warning("No HK Connect money flow data returned")
                return []

            result = []
            for _, row in df.iterrows():
                date_str = str(row.get("date", ""))
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue

                result.append(
                    {
                        "trade_date": FieldMapper.normalize_date(date_str),
                        "ggt_ss_money": FieldMapper.safe_float(row.get("沪股通净流入")),
                        "ggt_sz_money": FieldMapper.safe_float(row.get("深股通净流入")),
                        "north_money": FieldMapper.safe_float(row.get("北向资金净流入")),
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(result)} HK Connect money flow records")
            return result

        except Exception as e:
            logger.error(f"Failed to get HK Connect money flow: {e}")
            return []

    async def get_hk_stock_holdings(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取港股通持股明细

        Args:
            symbol: 股票代码（可选）

        Returns:
            持股明细列表
        """
        try:
            logger.info("Fetching HK Connect holdings from AkShare")

            df = ak.stock_hsgt_hold_stock_em()

            if df is None or df.empty:
                logger.warning("No HK Connect holdings data returned")
                return []

            result = []
            for _, row in df.iterrows():
                stock_code = str(row.get("港股代码", ""))
                stock_symbol = AkShareHKFieldMapper.normalize_hk_symbol(stock_code)

                if symbol and stock_symbol != symbol:
                    continue

                result.append(
                    {
                        "symbol": stock_symbol,
                        "name": row.get("港股名称", ""),
                        "hold_percent": FieldMapper.safe_float(row.get("持股比例")),
                        "hold_amount": FieldMapper.safe_float(row.get("持股数量")),
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(result)} HK Connect holdings records")
            return result

        except Exception as e:
            logger.error(f"Failed to get HK Connect holdings: {e}")
            return []

    async def get_hk_index_spot(self) -> List[Dict[str, Any]]:
        """
        获取港股指数实时行情

        Returns:
            指数行情列表
        """
        try:
            logger.info("Fetching HK index spot from AkShare")

            df = ak.stock_hk_index_spot_em()

            if df is None or df.empty:
                logger.warning("No HK index spot data returned")
                return []

            result = []
            for _, row in df.iterrows():
                code = str(row.get("代码", ""))
                name = row.get("名称", "")

                result.append(
                    {
                        "symbol": code,
                        "name": name,
                        "price": FieldMapper.safe_float(row.get("最新价")),
                        "change": FieldMapper.safe_float(row.get("涨跌额")),
                        "change_pct": FieldMapper.safe_float(row.get("涨跌幅")),
                        "volume": FieldMapper.safe_int(row.get("成交量")),
                        "amount": FieldMapper.safe_float(row.get("成交额")),
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(result)} HK index spot records")
            return result

        except Exception as e:
            logger.error(f"Failed to get HK index spot: {e}")
            return []

    async def get_hk_index_daily(
        self,
        symbol: str = "恒生指数",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取港股指数历史行情

        Args:
            symbol: 指数名称
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            指数历史行情列表
        """
        try:
            logger.info(f"Fetching HK index daily from AkShare: symbol={symbol}")

            df = ak.stock_hk_index_daily_em(symbol=symbol)

            if df is None or df.empty:
                logger.warning(f"No HK index daily data returned for {symbol}")
                return []

            result = []
            for _, row in df.iterrows():
                date_str = str(row.get("date", ""))
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue

                result.append(
                    {
                        "symbol": symbol,
                        "trade_date": FieldMapper.normalize_date(date_str),
                        "open": FieldMapper.safe_float(row.get("open")),
                        "high": FieldMapper.safe_float(row.get("high")),
                        "low": FieldMapper.safe_float(row.get("low")),
                        "close": FieldMapper.safe_float(row.get("close")),
                        "volume": FieldMapper.safe_int(row.get("volume")),
                        "amount": FieldMapper.safe_float(row.get("amount")),
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(result)} HK index daily records for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Failed to get HK index daily: {e}")
            return []

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

            logger.info(f"Fetching HK realtime quote from AkShare: symbol={code}")

            df = ak.stock_hk_spot_em()

            if df is None or df.empty:
                logger.warning(f"No realtime quote returned for {symbol}")
                return None

            # 查找对应股票
            stock_df = df[df["代码"] == code]
            if stock_df.empty:
                logger.warning(f"Stock {code} not found in HK spot data")
                return None

            row = stock_df.iloc[0]

            quote = {
                "symbol": symbol,
                "market": MarketType.HK_STOCK,
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
