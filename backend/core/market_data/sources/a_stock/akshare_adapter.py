import asyncio
import logging
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.market_data.models import (
    StockInfo,
    StockQuote,
    StockMinuteQuote,
    FinancialIncome,
    FinancialBalance,
    FinancialCashFlow,
    StockCompany,
    MarketNews,
    StockDividend,
    StockMargin,
    MacroEconomic,
    StockTopList,
    MarketType,
    Exchange,
    StockMoneyFlow,
    StockHSGTMoneyFlow,
    StockFinancialIndicator,
)
from core.market_data.tools.field_mapper import FieldMapper, AkShareFieldMapper
from core.market_data.tools.data_cleaner import DataCleaner
from core.market_data.sources.base import DataSourceAdapter

logger = logging.getLogger(__name__)


class AkShareAdapter(DataSourceAdapter):
    """AkShare数据源适配器（A股）"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        import akshare as ak

        self.ak = ak
        self.source_name = "akshare"
        # 设置默认优先级（AkShare 作为 A股的备用数据源）
        self._priority = 2

    async def connect(self) -> bool:
        """测试连接"""
        try:
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = await asyncio.to_thread(self.ak.tool_trade_date_hist_sina)
            return df is not None and not df.empty
        except Exception as e:
            logger.error(f"AkShare连接失败: {e}")
            return False

    async def test_connection(self) -> bool:
        """测试连接（别名方法）"""
        return await self.connect()

    def supports_market(self, market: MarketType) -> bool:
        """检查数据源是否支持指定市场"""
        return market == MarketType.A_STOCK

    async def get_stock_list(self, market: MarketType, status: str = "L") -> List[StockInfo]:
        """
        获取股票列表

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            股票信息列表
        """
        try:
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            # 使用 to_thread 避免阻塞主线程
            df = await asyncio.to_thread(self.ak.stock_zh_a_spot_em)

            if df is None or df.empty:
                return []

            stocks = []
            for _, row in df.iterrows():
                try:
                    mapped = AkShareFieldMapper.map_stock_spot(row)
                    if not mapped.get("symbol"):
                        continue

                    stock = StockInfo(**mapped)
                    stocks.append(stock)
                except Exception as e:
                    logger.debug(f"Failed to parse stock: {e}")
                    continue

            logger.debug(f"Retrieved {len(stocks)} stocks from AkShare")
            return stocks

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
        try:
            code = symbol.split(".")[0]

            start = FieldMapper.normalize_date(start_date) if start_date else "19900101"
            end = FieldMapper.normalize_date(end_date) if end_date else "21000101"

            adjust = adjust_type if adjust_type in ["qfq", "hfq"] else ""

            logger.info(
                f"Fetching daily quotes: symbol={code}, start={start}, end={end}, adjust={adjust}"
            )
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = self.ak.stock_zh_a_hist(
                symbol=code, period="daily", start_date=start, end_date=end, adjust=adjust
            )

            if df is None or df.empty:
                logger.warning(
                    f"No daily quotes returned for {code} (original: {symbol}). "
                    f"Possible reasons: 1. Stock delisted; 2. No trading data in range; 3. Invalid symbol."
                )
                return []

            quotes = []
            for _, row in df.iterrows():
                try:
                    mapped = AkShareFieldMapper.map_stock_quote(row, symbol)
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
    ) -> List[StockMinuteQuote]:
        """
        获取分钟K线数据

        Args:
            symbol: 股票代码
            trade_date: 交易日期（YYYYMMDD）
            freq: K线频率（1/5/15/30/60分钟）

        Returns:
            分钟K线数据列表
        """
        try:
            code = symbol.split(".")[0]

            period_map = {
                "1min": "1",
                "5min": "5",
                "15min": "15",
                "30min": "30",
                "60min": "60",
            }
            period = period_map.get(freq, "1")

            logger.info(f"Fetching minute quotes: symbol={code}, period={period}")

            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = self.ak.stock_zh_a_hist_min_em(symbol=code, period=period, adjust="")

            if df is None or df.empty:
                logger.warning(f"No minute quotes returned for {symbol}")
                return []

            klines = []
            for _, row in df.iterrows():
                try:
                    mapped = DataCleaner.clean_minute_quote(row.to_dict(), "akshare")
                    if mapped:
                        # 补全信息
                        mapped["ts_code"] = symbol
                        if "trade_time" in mapped:
                            # 简单格式化，DataCleaner中可能未完全处理时间格式
                            # 假设返回的是 '2023-01-01 09:30:00' 格式
                            pass
                        
                        kline = StockMinuteQuote(**mapped)
                        klines.append(kline)
                except Exception as e:
                    logger.warning(f"Failed to parse kline: {e}")
                    continue

            # 过滤日期逻辑移到这里或DataCleaner中，这里简化处理
            if trade_date:
                klines = [k for k in klines if k.trade_time.replace("-", "").replace(" ", "").replace(":", "").startswith(trade_date)]

            logger.info(f"Retrieved {len(klines)} minute klines for {symbol}")
            return klines

        except Exception as e:
            logger.error(f"Failed to get minute quotes: {e}")
            raise

    async def get_stock_financials(
        self, symbol: str, report_date: Optional[str] = None, report_type: Optional[str] = None
    ) -> List[FinancialIncome]:
        try:
            code = symbol.split(".")[0]

            logger.debug(f"Fetching profit sheet: symbol={code}")

            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = await asyncio.to_thread(self.ak.stock_financial_report_sina, stock=code, symbol="利润表")
                logger.debug(
                    f"Profit sheet result type: {type(df)}, empty: {df.empty if isinstance(df, pd.DataFrame) else 'N/A'}"
                )
            except Exception as e:
                logger.warning(f"Failed to get profit sheet: {e}")
                return []

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                logger.warning(f"No profit sheet data returned for {symbol}")
                return []

            if not isinstance(df, pd.DataFrame):
                logger.warning(f"Expected DataFrame but got {type(df)}")
                return []

            if report_date:
                df = df[df["报告日"] == report_date]

            financials = []
            for _, row in df.iterrows():
                try:
                    mapped = DataCleaner.clean_financial_income(row.to_dict(), "akshare")
                    if mapped:
                        mapped["ts_code"] = symbol
                        financial = FinancialIncome(**mapped)
                        financials.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to parse financial: {e}")
                    continue

            logger.info(f"Retrieved {len(financials)} financials for {symbol}")
            return financials

        except Exception as e:
            logger.error(f"Failed to get financials: {e}")
            return []

    async def get_stock_balance_sheet(
        self, symbol: str, report_date: Optional[str] = None
    ) -> List[FinancialBalance]:
        """
        获取资产负债表

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）

        Returns:
            资产负债表数据列表
        """
        try:
            code = symbol.split(".")[0]

            logger.info(f"Fetching balance sheet: symbol={code}")

            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = self.ak.stock_financial_report_sina(stock=code, symbol="资产负债表")
            except Exception as e:
                logger.warning(f"Failed to get balance sheet: {e}")
                return []

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                logger.warning(f"No balance sheet data returned for {symbol}")
                return []

            if not isinstance(df, pd.DataFrame):
                logger.warning(f"Expected DataFrame but got {type(df)}")
                return []

            if report_date:
                df = df[df["报告日"] == report_date]

            financials = []
            for _, row in df.iterrows():
                try:
                    report_period = str(row.get("报告日", ""))
                    if not report_period:
                        continue

                    balance_sheet = {
                        "total_assets": FieldMapper.convert_amount(
                            FieldMapper.safe_float(row.get("总资产")), "yuan", "wanyuan"
                        ),
                        "total_liabilities": FieldMapper.convert_amount(
                            FieldMapper.safe_float(row.get("负债合计")), "yuan", "wanyuan"
                        ),
                        "total_equity": FieldMapper.convert_amount(
                            FieldMapper.safe_float(row.get("所有者权益合计")), "yuan", "wanyuan"
                        ),
                    }

                    financial = StockFinancial(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        report_date=FieldMapper.normalize_date(report_period),
                        report_type="annual",
                        publish_date=None,
                        income_statement={},
                        balance_sheet=balance_sheet,
                        cash_flow={},
                        data_source=self.source_name,
                    )
                    financials.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to parse balance sheet: {e}")
                    continue

            logger.info(f"Retrieved {len(financials)} balance sheets for {symbol}")
            return financials

        except Exception as e:
            logger.error(f"Failed to get balance sheet: {e}")
            return []

    async def get_stock_cashflow(
        self, symbol: str, report_date: Optional[str] = None
    ) -> List[FinancialCashFlow]:
        """
        获取现金流量表

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）

        Returns:
            现金流量表数据列表
        """
        try:
            code = symbol.split(".")[0]

            logger.debug(f"Fetching cashflow: symbol={code}")

            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = await asyncio.to_thread(self.ak.stock_financial_report_sina, stock=code, symbol="现金流量表")
            except Exception as e:
                logger.warning(f"Failed to get cashflow: {e}")
                return []

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                logger.warning(f"No cashflow data returned for {symbol}")
                return []

            if not isinstance(df, pd.DataFrame):
                logger.warning(f"Expected DataFrame but got {type(df)}")
                return []

            if report_date:
                df = df[df["报告日"] == report_date]

            financials = []
            for _, row in df.iterrows():
                try:
                    mapped = DataCleaner.clean_financial_cashflow(row.to_dict(), "akshare")
                    if mapped:
                        mapped["symbol"] = symbol
                        financial = FinancialCashFlow(**mapped)
                        financials.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to parse cashflow: {e}")
                    continue

            logger.info(f"Retrieved {len(financials)} cashflow for {symbol}")
            return financials

        except Exception as e:
            logger.error(f"Failed to get cashflow: {e}")
            return []

    async def get_financial_indicators(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取财务指标

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            财务指标列表
        """
        try:
            code = symbol.split(".")[0]
            exchange = (
                "SZ"
                if symbol.endswith(".SZ") or code.startswith(("000", "001", "002", "003", "300"))
                else "SH"
            )
            symbol_with_exchange = f"{code}.{exchange}"

            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = self.ak.stock_financial_analysis_indicator_em(
                    symbol=symbol_with_exchange, indicator="按报告期"
                )
            except Exception as e:
                logger.warning(f"Failed to get financial indicators: {e}")
                return []

            if df is None or df.empty:
                return []

            indicators = []
            for _, row in df.iterrows():
                try:
                    report_date = str(row.get("REPORT_DATE", ""))
                    if not report_date:
                        continue

                    if start_date and report_date < start_date:
                        continue
                    if end_date and report_date > end_date:
                        continue

                    indicator = {
                        "symbol": symbol,
                        "report_date": report_date,
                        "roe": FieldMapper.safe_float(row.get("ROEJQ")),
                        "roa": FieldMapper.safe_float(row.get("ZZCJLL")),
                        "gross_profit_margin": FieldMapper.safe_float(row.get("MLR")),
                        "debt_to_asset_ratio": FieldMapper.safe_float(row.get("ZCFZL")),
                        "current_ratio": FieldMapper.safe_float(row.get("LD")),
                        "data_source": self.source_name,
                    }
                    indicators.append(indicator)
                except Exception as e:
                    logger.warning(f"Failed to parse indicator: {e}")
                    continue

            logger.info(f"Retrieved {len(indicators)} financial indicators")
            return indicators

        except Exception as e:
            logger.error(f"Failed to get financial indicators: {e}")
            return []

    async def get_stock_company(self, symbol: str) -> StockCompany:
        """
        获取公司信息

        Args:
            symbol: 股票代码

        Returns:
            公司信息
        """
        try:
            code = symbol.split(".")[0]

            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = await asyncio.to_thread(self.ak.stock_individual_info_em, symbol=code)

            if df is None or df.empty:
                return StockCompany(
                    symbol=symbol,
                    market=MarketType.A_STOCK,
                    company_name="",
                    industry="",
                    listing_date="",
                    data_source=self.source_name,
                )

            row = df.iloc[0]
            company = StockCompany(
                symbol=symbol,
                market=MarketType.A_STOCK,
                company_name=row.get("股票简称", row.get("name", "")),
                industry=row.get("所属行业", row.get("industry", "")),
                listing_date=str(row.get("上市日期", "")),
                data_source=self.source_name,
            )

            logger.debug(f"Retrieved company info for {symbol}")
            return company

        except Exception as e:
            logger.error(f"Failed to get company info: {e}")
            return StockCompany(
                symbol=symbol,
                market=MarketType.A_STOCK,
                company_name="",
                industry="",
                listing_date="",
                data_source=self.source_name,
            )

    async def get_daily_basic(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取每日指标

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            每日指标列表
        """
        try:
            code = symbol.split(".")[0]

            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = await asyncio.to_thread(self.ak.stock_individual_fund_flow, stock=code)
            except Exception as e:
                logger.warning(f"Failed to get daily basic: {e}")
                return []

            if df is None or df.empty:
                return []

            basics = []
            for _, row in df.iterrows():
                try:
                    mapped = DataCleaner.clean_daily_indicator(row.to_dict(), "akshare")
                    if mapped:
                         mapped["ts_code"] = symbol
                         basics.append(mapped)
                except Exception as e:
                    logger.debug(f"Failed to parse basic: {e}")
                    continue

            logger.debug(f"Retrieved {len(basics)} daily basics")
            return basics

        except Exception as e:
            logger.error(f"Failed to get daily basic: {e}")
            return []

    async def get_trade_calendar(
        self, exchange: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取交易日历

        Args:
            exchange: 交易所代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易日历列表
        """
        try:
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = await asyncio.to_thread(self.ak.tool_trade_date_hist_sina)

            if df is None or df.empty:
                return []

            calendar = []
            for _, row in df.iterrows():
                try:
                    trade_date = str(row.get("trade_date", ""))
                    normalized_date = FieldMapper.normalize_date(trade_date)

                    if start_date and normalized_date < start_date:
                        continue
                    if end_date and normalized_date > end_date:
                        continue

                    calendar.append(
                        {
                            "exchange": exchange,
                            "trade_date": normalized_date,
                            "is_open": True,
                            "data_source": self.source_name,
                        }
                    )
                except Exception as e:
                    logger.debug(f"Failed to parse calendar: {e}")
                    continue

            logger.debug(f"Retrieved {len(calendar)} trade calendar dates")
            return calendar

        except Exception as e:
            logger.error(f"Failed to get trade calendar: {e}")
            return []

    async def get_shibor(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[MacroEconomic]:
        """
        获取SHIBOR数据

        Args:
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            SHIBOR数据列表
        """
        try:
            results = []

            periods = ["隔夜", "1周", "2周", "1月", "3月", "6月", "9月", "1年"]
            period_map = {
                "隔夜": "on",
                "1周": "1w",
                "2周": "2w",
                "1月": "1m",
                "3月": "3m",
                "6月": "6m",
                "9月": "9m",
                "1年": "1y",
            }

            for period in periods:
                try:
                    logger.info(f"Fetching SHIBOR data for period: {period}")
                    await asyncio.sleep(1)  # 避免触发反爬虫机制
                    df = self.ak.rate_interbank(
                        market="上海银行同业拆借市场", symbol="Shibor人民币", indicator=period
                    )

                    if df is None or df.empty:
                        logger.warning(f"No SHIBOR data for period {period}")
                        continue

                    for _, row in df.iterrows():
                        try:
                            date_str = str(row.get("报告日", row.get("date", "")))
                            normalized_date = FieldMapper.normalize_date(date_str)

                            if start_date and normalized_date < start_date:
                                continue
                            if end_date and normalized_date > end_date:
                                continue

                            value = row.get("利率", row.get("value", row.get("今值")))
                            if pd.notna(value) and float(value) > 0:
                                period_key = period_map.get(period, period.lower())
                                result = MacroEconomic(
                                    indicator=f"shibor_{period_key}",
                                    period=normalized_date,
                                    value=float(value),
                                    unit="%",
                                    data_source=self.source_name,
                                )
                                results.append(result)
                        except Exception as e:
                            logger.warning(f"Failed to parse SHIBOR row: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"Failed to get SHIBOR for period {period}: {e}")
                    continue

            logger.info(f"Retrieved {len(results)} SHIBOR records")
            return results

        except Exception as e:
            logger.error(f"Failed to get SHIBOR: {e}")
            return []

    async def get_pmi_cic(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[MacroEconomic]:
        """
        获取中采PMI数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            PMI数据列表
        """
        try:
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = self.ak.macro_china_pmi_yearly()

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                try:
                    date = str(row.get("日期", ""))
                    date = FieldMapper.normalize_date(date)
                    value = row.get("今值")
                    if pd.notna(value):
                        result.append(
                            MacroEconomic(
                                indicator="pmi_manufacturing",
                                period=date,
                                value=float(value),
                                unit="-",
                                data_source=self.source_name,
                            )
                        )
                except Exception as e:
                    logger.warning(f"Failed to parse PMI: {e}")
                    continue

            logger.info(f"Retrieved {len(result)} cic pmi data")
            return result

        except Exception as e:
            logger.error(f"Failed to get cic pmi: {e}")
            raise

    async def get_northbound_money_flow(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取北向资金流向

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            北向资金流向列表
        """
        try:
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = self.ak.stock_hsgt_hist_em()

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                mapped = DataCleaner.clean_hsgt_money_flow(row.to_dict(), "akshare")
                if mapped:
                    result.append(mapped)

            logger.info(f"Retrieved {len(result)} northbound money flow")
            return result

        except Exception as e:
            logger.error(f"Failed to get northbound money flow: {e}")
            raise

    async def get_stock_new(self, market: str = "A股") -> List[Dict[str, Any]]:
        """
        获取新股发行数据

        Args:
            market: 市场类型

        Returns:
            新股数据列表
        """
        try:
            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = self.ak.stock_zh_a_new()
            except Exception as e:
                logger.warning(f"Failed to get new stocks: {e}")
                return []

            if df is None or df.empty:
                return []

            new_stocks = []
            for _, row in df.iterrows():
                try:
                    new_stocks.append(
                        {
                            "symbol": str(row.get("申购代码", "")),
                            "name": str(row.get("新股名称", "")),
                            "issue_date": str(row.get("上市日期", "")),
                            "issue_price": float(row.get("发行价格", 0))
                            if pd.notna(row.get("发行价格"))
                            else None,
                            "data_source": self.source_name,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse new stock: {e}")
                    continue

            logger.info(f"Retrieved {len(new_stocks)} new stocks")
            return new_stocks

        except Exception as e:
            logger.error(f"Failed to get new stocks: {e}")
            return []

    async def get_stock_company(self, symbol: str) -> Optional[StockCompany]:
        """
        获取公司信息

        Args:
            symbol: 股票代码

        Returns:
            公司信息
        """
        try:
            code = symbol.split(".")[0]
            # 使用个股信息接口
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = self.ak.stock_individual_info_em(symbol=code)

            if df is None or df.empty:
                return None

            # 转换为字典
            info = dict(zip(df["item"], df["value"]))

            # 解析上市日期 (YYYYMMDD)
            listing_date = str(info.get("上市时间", ""))
            if len(listing_date) == 8:
                pass
            else:
                # 尝试格式化，如果不是8位，可能需要处理
                pass

            return StockCompany(
                symbol=symbol,
                market=MarketType.A_STOCK,
                company_name=str(info.get("股票名称", "")),
                industry=str(info.get("行业", "")),
                listing_date=listing_date,
                capital_structure={
                    "total_share": info.get("总股本"),
                    "float_share": info.get("流通股"),
                },
                data_source=self.source_name,
            )

        except Exception as e:
            logger.warning(f"Failed to get company info for {symbol} from AkShare: {e}")
            return None

    async def get_stock_suspend(self, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取停牌股票

        Args:
            exchange: 交易所代码

        Returns:
            停牌股票列表
        """
        try:
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = self.ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                return []

            suspend_list = []
            for _, row in df.iterrows():
                try:
                    code = str(row.get("代码", ""))
                    if not code:
                        continue

                    symbol = FieldMapper.normalize_symbol(code)

                    if exchange:
                        mapped_exchange = "SSE" if symbol.endswith(".SH") else "SZSE"
                        if mapped_exchange != exchange:
                            continue

                    suspend_list.append(
                        {
                            "symbol": symbol,
                            "name": str(row.get("名称", "")),
                            "suspend_reason": "",
                            "suspend_date": "",
                            "resume_date": "",
                            "data_source": self.source_name,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse suspend: {e}")
                    continue

            logger.info(f"Retrieved {len(suspend_list)} suspend stocks")
            return suspend_list

        except Exception as e:
            logger.error(f"Failed to get suspend stocks: {e}")
            return []

    async def get_stock_sectors(self, sector_type: str = "concept") -> List[Dict[str, Any]]:
        """
        获取板块数据

        Args:
            sector_type: 板块类型（concept/industry）

        Returns:
            板块数据列表
        """
        try:
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            if sector_type == "concept":
                df = self.ak.stock_board_concept_name_em()
            elif sector_type == "industry":
                df = self.ak.stock_board_industry_name_em()
            else:
                df = self.ak.stock_board_concept_name_em()

            if df is None or df.empty:
                return []

            sectors = []
            for _, row in df.iterrows():
                sectors.append(
                    {
                        "sector_name": row.get("板块名称", ""),
                        "sector_code": row.get("板块代码", ""),
                        "sector_type": sector_type,
                        "stock_count": FieldMapper.safe_int(row.get("成分股数量")),
                        "description": None,
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(sectors)} {sector_type} sectors")
            return sectors

        except Exception as e:
            logger.error(f"Failed to get stock sectors: {e}")
            raise

    async def get_sector_quotes(self, sector_name: str) -> List[Dict[str, Any]]:
        """
        获取板块实时行情

        Args:
            sector_name: 板块名称

        Returns:
            板块内股票实时行情列表
        """
        try:
            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = self.ak.stock_board_concept_spot_em(symbol=sector_name)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                code = str(row.get("代码", ""))
                symbol = FieldMapper.normalize_symbol(code)
                result.append(
                    {
                        "symbol": symbol,
                        "name": row.get("名称", ""),
                        "price": FieldMapper.safe_float(row.get("最新价")),
                        "change_pct": FieldMapper.safe_float(row.get("涨跌幅")),
                        "volume": FieldMapper.safe_int(row.get("成交量")),
                        "amount": FieldMapper.safe_float(row.get("成交额")),
                        "data_source": self.source_name,
                    }
                )

            logger.info(f"Retrieved {len(result)} quotes for sector {sector_name}")
            return result

        except Exception as e:
            logger.error(f"Failed to get sector quotes: {e}")
            return []

    async def get_stock_top_list(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[StockTopList]:
        """
        获取龙虎榜数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            龙虎榜数据列表
        """
        try:
            code = symbol.split('.')[0]

            from datetime import datetime
            today = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = today
            if end_date is None:
                end_date = start_date

            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = self.ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
            except Exception as e:
                logger.warning(f"Failed to get top list: {e}")
                return []

            if df is None or df.empty:
                return []

            top_list = []
            for _, row in df.iterrows():
                try:
                    mapped = DataCleaner.clean_stock_top_list(row.to_dict(), "akshare")
                    if not mapped:
                        continue
                        
                    # 简单筛选：如果 mapped['ts_code'] matches symbol code
                    # clean_stock_top_list returns 'ts_code' as the raw code from akshare
                    if str(mapped.get("ts_code")) == code:
                        mapped["ts_code"] = symbol
                        item = StockTopList(**mapped)
                        top_list.append(item)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse top list item: {e}")
                    continue

            logger.info(f"Retrieved {len(top_list)} top list records")
            return top_list

        except Exception as e:
            logger.error(f"Failed to get top list: {e}")
            return []

    async def get_stock_dividend(self, symbol: str) -> List[StockDividend]:
        """
        获取分红数据

        Args:
            symbol: 股票代码

        Returns:
            分红数据列表
        """
        try:
            code = symbol.split(".")[0]

            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = self.ak.stock_history_dividend_detail(symbol=code, indicator="分红")
            except Exception as e:
                logger.warning(f"Failed to get dividend: {e}")
                return []

            if df is None or df.empty:
                return []

            dividends = []
            for _, row in df.iterrows():
                try:
                    ex_dividend_date = row.get("除权除息日", pd.NaT)
                    record_date = row.get("股权登记日", pd.NaT)

                    if pd.isna(ex_dividend_date) and pd.isna(record_date):
                        continue

                    ex_dividend_str = FieldMapper.normalize_date(
                        str(ex_dividend_date) if not pd.isna(ex_dividend_date) else ""
                    )
                    record_date_str = FieldMapper.normalize_date(
                        str(record_date) if not pd.isna(record_date) else ""
                    )

                    cash_dividend = FieldMapper.safe_float(row.get("派息", 0))

                    dividends.append(
                        StockDividend(
                            symbol=symbol,
                            dividend_year=ex_dividend_str[:4] if ex_dividend_str else "",
                            ex_dividend_date=ex_dividend_str if ex_dividend_str else None,
                            record_date=record_date_str if record_date_str else None,
                            cash_dividend=cash_dividend,
                            dividend_ratio=None,
                            data_source=self.source_name,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse dividend: {e}")
                    continue

            logger.info(f"Retrieved {len(dividends)} dividends")
            return dividends

        except Exception as e:
            logger.error(f"Failed to get dividends: {e}")
            return []

    async def get_stock_margin(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
    ) -> List[StockMargin]:
        """
        获取融资融券数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            exchange: 交易所代码

        Returns:
            融资融券数据列表
        """
        try:
            code = symbol.split(".")[0]

            if exchange is None:
                exchange_str = (
                    "sz"
                    if symbol.endswith(".SZ")
                    or code.startswith(("000", "001", "002", "003", "300"))
                    else "sh"
                )
            elif exchange == "SSE":
                exchange_str = "sh"
            elif exchange == "SZSE":
                exchange_str = "sz"
            else:
                exchange_str = "sh"

            from datetime import datetime

            try:
                today = datetime.now().strftime("%Y%m%d")
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                if exchange_str == "sh":
                    df = self.ak.stock_margin_detail_sse(date=today)
                else:
                    df = self.ak.stock_margin_detail_szse(date=today)
            except Exception as e:
                logger.warning(f"Failed to get margin: {e}")
                return []

            if df is None or df.empty:
                return []

            margins = []
            for _, row in df.iterrows():
                try:
                    stock_code = str(row.get("标的证券代码", row.get("证券代码", "")))
                    if stock_code != code:
                        continue

                    from datetime import datetime
                    trade_date = datetime.now().strftime('%Y%m%d')

                    margin_buy = FieldMapper.safe_float(row.get("融资买入额", 0))
                    short_sell = FieldMapper.safe_float(row.get("融券卖出量", 0))
                    margin_balance = FieldMapper.safe_float(row.get("融资余额", 0))
                    short_balance = FieldMapper.safe_float(row.get("融券余额", 0))

                    margins.append(
                        StockMargin(
                            symbol=symbol,
                            trade_date=trade_date,
                            margin_buy=margin_buy,
                            margin_sell=None,
                            margin_balance=margin_balance,
                            short_sell=short_sell,
                            short_buy=None,
                            short_balance=short_balance,
                            data_source=self.source_name,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse margin: {e}")
                    continue

            logger.info(f"Retrieved {len(margins)} margin records")
            return margins

        except Exception as e:
            logger.error(f"Failed to get margin: {e}")
            return []

    async def get_stock_news(self, symbol: str, limit: int = 100) -> List[MarketNews]:
        """
        获取股票新闻
        
        Args:
            symbol: 股票代码
            limit: 返回数量限制
            
        Returns:
            新闻数据列表
        """
        try:
            import hashlib
            code = symbol.split(".")[0]
            
            logger.info(f"Fetching stock news: symbol={code}")
            
            try:
                await asyncio.sleep(1)  # 避免触发反爬虫机制
                df = self.ak.stock_news_em(symbol=code)
            except Exception as e:
                logger.warning(f"Failed to get stock news: {e}")
                return []
                
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                return []
                
            news_list = []
            for _, row in df.iterrows():
                try:
                    title = str(row.get("新闻标题", row.get("title", "")))
                    publish_time = str(row.get("发布时间", row.get("publish_time", row.get("time", ""))))
                    url = str(row.get("新闻链接", row.get("url", "")))
                    content = str(row.get("新闻内容", row.get("content", "")))
                    
                    if not title:
                        continue
                        
                    # 生成ID
                    news_id = hashlib.md5(f"{symbol}_{publish_time}_{title}".encode()).hexdigest()
                    
                    news = MarketNews(
                        news_id=news_id,
                        ts_code=symbol,
                        datetime=publish_time,
                        title=title,
                        content=content + f" (Link: {url})" if url else content,
                        source="EastMoney",
                        data_source=self.source_name
                    )
                    news_list.append(news)
                    
                    if len(news_list) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to parse news: {e}")
                    continue
                    
            logger.info(f"Retrieved {len(news_list)} news for {symbol}")
            return news_list
            
        except Exception as e:
            logger.error(f"Failed to get stock news: {e}")
            return []

    async def get_individual_fund_flow(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取个股资金流向

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            资金流向列表
        """
        try:
            code = symbol.split(".")[0]

            await asyncio.sleep(1)  # 避免触发反爬虫机制
            df = self.ak.stock_individual_fund_flow(stock=code)

            if df is None or df.empty:
                return []

            fund_flows = []
            for _, row in df.iterrows():
                try:
                    fund_flows.append(
                        {
                            "symbol": symbol,
                            "trade_date": str(row.get("日期", "")),
                            "main_net_inflow": FieldMapper.safe_float(row.get("主力净流入")),
                            "large_order_net_inflow": FieldMapper.safe_float(
                                row.get("超大单净流入")
                            ),
                            "medium_order_net_inflow": FieldMapper.safe_float(
                                row.get("大单净流入")
                            ),
                            "small_order_net_inflow": FieldMapper.safe_float(row.get("小单净流入")),
                            "data_source": self.source_name,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse fund flow: {e}")
                    continue

            logger.info(f"Retrieved {len(fund_flows)} fund flow records")
            return fund_flows

        except Exception as e:
            logger.error(f"Failed to get fund flow: {e}")
            return []

    async def get_market_news(
        self,
        symbol: Optional[str] = None,
        limit: int = 20
    ) -> List[MarketNews]:
        """
        获取新闻
        
        Args:
            symbol: 股票代码 (可选，如果提供则获取个股新闻)
            limit: 限制数量
            
        Returns:
            新闻列表
        """
        try:
            import hashlib
            news_list = []
            
            if symbol:
                # 获取个股新闻
                code = symbol.split('.')[0]
                try:
                    await asyncio.sleep(1)  # 避免触发反爬虫机制
                    df = self.ak.stock_news_em(symbol=code)
                    if df is not None and not df.empty:
                        df = df.head(limit)
                        for _, row in df.iterrows():
                            title = str(row.get('新闻标题', ''))
                            date_str = str(row.get('发布时间', ''))
                            content = str(row.get('新闻内容', ''))
                            url = str(row.get('新闻链接', ''))
                            
                            # 生成ID
                            news_id = hashlib.md5(f"{symbol}_{date_str}_{title}".encode()).hexdigest()
                            
                            news = MarketNews(
                                news_id=news_id,
                                ts_code=symbol,
                                datetime=date_str,
                                title=title,
                                content=content + f" (Link: {url})" if url else content,
                                source="EastMoney",
                                data_source=self.source_name
                            )
                            news_list.append(news)
                except Exception as e:
                    logger.warning(f"Failed to get individual news for {symbol}: {e}")
            else:
                # 获取全球财经快讯
                try:
                    await asyncio.sleep(1)  # 避免触发反爬虫机制
                    df = self.ak.stock_info_global_cls()
                    if df is not None and not df.empty:
                        df = df.head(limit)
                        for _, row in df.iterrows():
                            title = str(row.get('title', ''))
                            date_str = str(row.get('publish_time', ''))
                            content = str(row.get('content', ''))
                            
                            news_id = hashlib.md5(f"global_{date_str}_{title}".encode()).hexdigest()
                            
                            news = MarketNews(
                                news_id=news_id,
                                ts_code=None,
                                datetime=date_str,
                                title=title,
                                content=content,
                                source="CLS",
                                data_source=self.source_name
                            )
                            news_list.append(news)
                except Exception as e:
                    logger.warning(f"Failed to get global news: {e}")
                    
            logger.info(f"Retrieved {len(news_list)} news items from AkShare")
            return news_list

        except Exception as e:
            logger.error(f"Failed to get market news: {e}")
            return []
