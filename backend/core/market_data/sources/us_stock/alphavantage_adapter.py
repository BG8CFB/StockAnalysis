"""
Alpha Vantage 美股数据源适配器

支持美股日线行情和技术指标数据获取。
使用 Alpha Vantage API 进行数据交互，需要 API Key。
免费版限制 5 次/分钟。
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

try:
    import requests
except ImportError:
    requests = None
    logging.warning("requests not installed. Install with: pip install requests")

from core.market_data.sources.base import DataSourceAdapter
from core.market_data.models import (
    StockQuote,
    MarketType,
)
from core.market_data.tools.field_mapper import FieldMapper

logger = logging.getLogger(__name__)


class AlphaVantageFieldMapper(FieldMapper):
    """Alpha Vantage 字段映射器"""

    @staticmethod
    def map_stock_quote(row: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        映射 Alpha Vantage 行情数据

        Args:
            row: 数据字典
            symbol: 股票代码

        Returns:
            统一格式行情数据字典
        """
        trade_date = FieldMapper.normalize_date(row.get('date', ''))

        return {
            "symbol": symbol,
            "market": MarketType.US_STOCK,
            "trade_date": trade_date,
            "open": FieldMapper.safe_float(row.get('1. open')),
            "high": FieldMapper.safe_float(row.get('2. high')),
            "low": FieldMapper.safe_float(row.get('3. low')),
            "close": FieldMapper.safe_float(row.get('4. close')),
            "pre_close": None,
            "volume": FieldMapper.safe_int(row.get('5. volume')),
            "amount": None,
            "change": None,
            "change_pct": None,
            "turnover_rate": None,
            "data_source": "alphavantage",
        }

    @staticmethod
    def map_technical_indicator(data: Dict[str, Any], symbol: str, indicator: str) -> Dict[str, Any]:
        """
        映射 Alpha Vantage 技术指标数据

        Args:
            data: 响应数据
            symbol: 股票代码
            indicator: 指标名称

        Returns:
            技术指标数据字典
        """
        time_series_key = f"Technical Analysis: {indicator}"
        if time_series_key not in data:
            return {}

        result = []
        for date, values in data[time_series_key].items():
            result.append({
                "symbol": symbol,
                "date": FieldMapper.normalize_date(date),
                "indicator": indicator,
                "values": values,
                "data_source": "alphavantage",
            })

        return {"data": result, "symbol": symbol, "indicator": indicator}


class AlphaVantageAdapter(DataSourceAdapter):
    """Alpha Vantage 美股数据源适配器"""

    # API 基础 URL
    BASE_URL = "https://www.alphavantage.co/query"

    # 支持的技术指标
    SUPPORTED_INDICATORS = [
        "SMA", "EMA", "WMA", "DEMA", "TEMA", "TRIMA", "T3",
        "RSI", "MACD", "STOCH", "STOCHRSI", "WILLR", "ADX", "CCI", "AROON",
        "BBANDS", "MOM", "ROC", "TRIX", "CCI",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if requests is None:
            raise ImportError("requests is not installed. Install with: pip install requests")

        api_key = self.config.get("api_key") if self.config else None
        if not api_key:
            raise ValueError("Alpha Vantage API Key is required")

        self.api_key = api_key
        self.source_name = "alphavantage"
        # 设置默认优先级（Alpha Vantage 作为美股备用数据源）
        self._priority = 2

        # 限流控制：免费版 5 次/分钟
        self.request_times = []
        self.max_requests_per_minute = 5
        self.rate_limit_window = 60

    def supports_market(self, market: MarketType) -> bool:
        return market == MarketType.US_STOCK

    async def _check_rate_limit(self):
        """检查并执行限流控制"""
        now = datetime.now()

        # 清理超过时间窗口的请求记录
        self.request_times = [
            t for t in self.request_times
            if (now - t).total_seconds() < self.rate_limit_window
        ]

        # 如果达到限制，等待
        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = self.rate_limit_window - (now - self.request_times[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)

        # 记录本次请求时间
        self.request_times.append(now)

    async def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 API 请求

        Args:
            params: 请求参数

        Returns:
            响应数据
        """
        await self._check_rate_limit()

        params["apikey"] = self.api_key

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # 检查错误信息
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage API Error: {data['Error Message']}")
            if "Note" in data:
                logger.warning(f"Alpha Vantage API Note: {data['Note']}")
                # API 限流提示
                await asyncio.sleep(60)
                return await self._make_request(params)

            return data

        except requests.RequestException as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            raise

    async def test_connection(self) -> bool:
        try:
            # 测试获取一个股票的 quote
            data = await self._make_request({
                "function": "GLOBAL_QUOTE",
                "symbol": "AAPL",
            })
            return "Global Quote" in data
        except Exception as e:
            logger.error(f"Alpha Vantage connection test failed: {e}")
            return False

    async def get_stock_list(
        self,
        market: MarketType,
        status: str = "L"
    ) -> List[Any]:
        """
        Alpha Vantage 不支持股票列表获取

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            空列表
        """
        logger.warning("Alpha Vantage does not support stock list retrieval")
        return []

    async def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust_type: Optional[str] = None
    ) -> List[StockQuote]:
        """
        获取美股日线行情

        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust_type: 复权类型

        Returns:
            日线行情列表
        """
        try:
            code = symbol.replace('.US', '')

            # 设置输出大小
            outputsize = "full" if not start_date else "compact"

            logger.info(f"Fetching daily quotes from Alpha Vantage: symbol={code}")

            data = await self._make_request({
                "function": "TIME_SERIES_DAILY",
                "symbol": code,
                "outputsize": outputsize,
            })

            if "Time Series (Daily)" not in data:
                logger.warning(f"No daily quotes returned for {symbol}")
                return []

            time_series = data["Time Series (Daily)"]

            quotes = []
            for date, values in time_series.items():
                # 日期过滤
                trade_date = FieldMapper.normalize_date(date)
                if start_date and trade_date < start_date:
                    continue
                if end_date and trade_date > end_date:
                    continue

                try:
                    quote_data = {
                        "date": date,
                        "1. open": values.get("1. open"),
                        "2. high": values.get("2. high"),
                        "3. low": values.get("3. low"),
                        "4. close": values.get("4. close"),
                        "5. volume": values.get("5. volume"),
                    }

                    mapped = AlphaVantageFieldMapper.map_stock_quote(quote_data, symbol)
                    quote = StockQuote(**mapped)
                    quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Failed to parse quote: {e}")
                    continue

            # 按日期倒序排列
            quotes.sort(key=lambda x: x.trade_date, reverse=True)

            logger.info(f"Retrieved {len(quotes)} quotes for {symbol} from Alpha Vantage")
            return quotes

        except Exception as e:
            logger.error(f"Failed to get daily quotes: {e}")
            raise

    async def get_minute_quotes(
        self,
        symbol: str,
        trade_date: Optional[str] = None,
        freq: str = "1min"
    ) -> List[Any]:
        """
        获取美股分钟K线（Alpha Vantage 仅支持最近数据）

        Args:
            symbol: 股票代码
            trade_date: 交易日期
            freq: K线频率

        Returns:
            分钟K线数据列表
        """
        try:
            code = symbol.replace('.US', '')

            # Alpha Vantage 支持 1min, 5min, 15min, 30min, 60min
            interval_map = {
                '1min': '1min',
                '5min': '5min',
                '15min': '15min',
                '30min': '30min',
                '60min': '60min',
            }
            interval = interval_map.get(freq, '1min')

            logger.info(f"Fetching intraday quotes from Alpha Vantage: symbol={code}, interval={interval}")

            data = await self._make_request({
                "function": "TIME_SERIES_INTRADAY",
                "symbol": code,
                "interval": interval,
                "outputsize": "full",
            })

            time_series_key = f"Time Series ({interval})"
            if time_series_key not in data:
                logger.warning(f"No intraday quotes returned for {symbol}")
                return []

            time_series = data[time_series_key]

            klines = []
            for date, values in time_series.items():
                try:
                    from core.market_data.models import StockKLine

                    trade_dt = date.replace("-", "").replace(" ", "").replace(":", "")

                    kline = StockKLine(
                        symbol=symbol,
                        market=MarketType.US_STOCK,
                        trade_date=trade_dt[:8] if len(trade_dt) >= 8 else trade_dt,
                        open=float(values.get("1. open", 0)),
                        high=float(values.get("2. high", 0)),
                        low=float(values.get("3. low", 0)),
                        close=float(values.get("4. close", 0)),
                        volume=int(values.get("5. volume", 0)),
                        amount=None,
                        data_source=self.source_name
                    )
                    klines.append(kline)
                except Exception as e:
                    logger.warning(f"Failed to parse kline: {e}")
                    continue

            logger.info(f"Retrieved {len(klines)} minute klines for {symbol} from Alpha Vantage")
            return klines

        except Exception as e:
            logger.error(f"Failed to get minute quotes: {e}")
            raise

    async def get_stock_financials(self, symbol: str, report_date: Optional[str] = None, report_type: Optional[str] = None) -> List[Any]:
        """Alpha Vantage 不支持财务数据"""
        logger.warning("Alpha Vantage does not support financial data")
        return []

    async def get_financial_indicators(self, symbol: str, report_date: Optional[str] = None) -> List[Any]:
        """Alpha Vantage 不支持财务指标"""
        logger.warning("Alpha Vantage does not support financial indicators")
        return []

    async def get_technical_indicator(
        self,
        symbol: str,
        indicator: str,
        interval: str = "daily",
        time_period: int = 20,
        series_type: str = "close",
        **params
    ) -> Dict[str, Any]:
        """
        获取技术指标

        Args:
            symbol: 股票代码
            indicator: 指标名称（SMA, EMA, RSI, MACD, BBANDS, STOCH 等）
            interval: 时间间隔（1min, 5min, 15min, 30min, 60min, daily, weekly, monthly）
            time_period: 时间周期
            series_type: 价格类型（close, open, high, low）
            **params: 其他参数

        Returns:
            技术指标数据
        """
        try:
            if indicator not in self.SUPPORTED_INDICATORS:
                raise ValueError(f"Unsupported indicator: {indicator}. Supported: {self.SUPPORTED_INDICATORS}")

            code = symbol.replace('.US', '')

            request_params = {
                "function": indicator,
                "symbol": code,
                "interval": interval,
                "time_period": time_period,
                "series_type": series_type,
            }

            # 添加特定指标的额外参数
            if indicator == "MACD":
                request_params.update({
                    "fastperiod": params.get("fastperiod", 12),
                    "slowperiod": params.get("slowperiod", 26),
                    "signalperiod": params.get("signalperiod", 9),
                })
            elif indicator == "BBANDS":
                request_params.update({
                    "nbdevup": params.get("nbdevup", 2),
                    "nbdevdn": params.get("nbdevdn", 2),
                    "matype": params.get("matype", 0),
                })
            elif indicator == "STOCH":
                request_params.update({
                    "fastkperiod": params.get("fastkperiod", 5),
                    "slowkperiod": params.get("slowkperiod", 3),
                    "slowdperiod": params.get("slowdperiod", 3),
                    "slowkmatype": params.get("slowkmatype", 0),
                    "slowdmatype": params.get("slowdmatype", 0),
                })

            logger.info(f"Fetching technical indicator from Alpha Vantage: symbol={code}, indicator={indicator}")

            data = await self._make_request(request_params)

            return AlphaVantageFieldMapper.map_technical_indicator(data, symbol, indicator)

        except Exception as e:
            logger.error(f"Failed to get technical indicator: {e}")
            raise

    async def get_sma(
        self,
        symbol: str,
        time_period: int = 20,
        series_type: str = "close",
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """获取简单移动平均线 (SMA)"""
        return await self.get_technical_indicator(
            symbol, "SMA", interval, time_period, series_type
        )

    async def get_ema(
        self,
        symbol: str,
        time_period: int = 20,
        series_type: str = "close",
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """获取指数移动平均线 (EMA)"""
        return await self.get_technical_indicator(
            symbol, "EMA", interval, time_period, series_type
        )

    async def get_rsi(
        self,
        symbol: str,
        time_period: int = 14,
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """获取相对强弱指数 (RSI)"""
        return await self.get_technical_indicator(
            symbol, "RSI", interval, time_period, "close"
        )

    async def get_macd(
        self,
        symbol: str,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """获取 MACD 指标"""
        return await self.get_technical_indicator(
            symbol, "MACD", interval,
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )

    async def get_bollinger_bands(
        self,
        symbol: str,
        time_period: int = 20,
        nbdevup: int = 2,
        nbdevdn: int = 2,
        series_type: str = "close",
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """获取布林带 (BBANDS)"""
        return await self.get_technical_indicator(
            symbol, "BBANDS", interval, time_period, series_type,
            nbdevup=nbdevup, nbdevdn=nbdevdn
        )

    async def get_stochastic(
        self,
        symbol: str,
        fastkperiod: int = 5,
        slowkperiod: int = 3,
        slowdperiod: int = 3,
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """获取随机指标 (STOCH)"""
        return await self.get_technical_indicator(
            symbol, "STOCH", interval,
            fastkperiod=fastkperiod,
            slowkperiod=slowkperiod,
            slowdperiod=slowdperiod
        )
