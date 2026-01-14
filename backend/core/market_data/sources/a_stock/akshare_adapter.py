import logging
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime

from ...models import (
    StockInfo, StockQuote, StockKLine, StockFinancial,
    StockCompany, StockNews, StockDividend, StockMargin,
    MacroEconomic, StockSector, StockTopList,
    MarketType, Exchange
)
from ...tools.field_mapper import FieldMapper, AkShareFieldMapper
from ..base import DataSourceAdapter

logger = logging.getLogger(__name__)


class AkShareAdapter(DataSourceAdapter):
    """AkShare数据源适配器（A股）"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        import akshare as ak
        self.ak = ak
        self.source_name = "akshare"

    async def connect(self) -> bool:
        """测试连接"""
        try:
            df = self.ak.tool_trade_date_hist_sina()
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

    def get_priority(self) -> int:
        """获取数据源优先级"""
        return 2  # AkShare 作为 A股的备用数据源

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
            df = self.ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                return []

            stocks = []
            for _, row in df.iterrows():
                try:
                    mapped = AkShareFieldMapper.map_stock_spot(row)
                    if not mapped.get('symbol'):
                        continue

                    stock = StockInfo(**mapped)
                    stocks.append(stock)
                except Exception as e:
                    logger.warning(f"Failed to parse stock: {e}")
                    continue

            logger.info(f"Retrieved {len(stocks)} stocks from AkShare")
            return stocks

        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            return []

    async def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust_type: Optional[str] = None
    ) -> List[StockQuote]:
        try:
            code = symbol.split('.')[0]

            start = FieldMapper.normalize_date(start_date) if start_date else "19900101"
            end = FieldMapper.normalize_date(end_date) if end_date else "21000101"

            adjust = adjust_type if adjust_type in ['qfq', 'hfq'] else ""

            logger.info(f"Fetching daily quotes: symbol={code}, start={start}, end={end}, adjust={adjust}")
            df = self.ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start,
                end_date=end,
                adjust=adjust
            )

            if df is None or df.empty:
                logger.warning(f"No daily quotes returned for {symbol}")
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
        self,
        symbol: str,
        trade_date: Optional[str] = None,
        freq: str = "1min"
    ) -> List[StockKLine]:
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
            code = symbol.split('.')[0]

            period_map = {
                '1min': '1',
                '5min': '5',
                '15min': '15',
                '30min': '30',
                '60min': '60',
            }
            period = period_map.get(freq, '1')

            logger.info(f"Fetching minute quotes: symbol={code}, period={period}")

            df = self.ak.stock_zh_a_hist_min_em(
                symbol=code,
                period=period,
                adjust=''
            )

            if df is None or df.empty:
                logger.warning(f"No minute quotes returned for {symbol}")
                return []

            klines = []
            for _, row in df.iterrows():
                try:
                    trade_dt = str(row.get('时间') or row.get('datetime', ''))

                    if trade_date and trade_dt:
                        date_part = trade_dt[:10].replace('-', '')
                        if date_part != trade_date:
                            continue

                    if len(trade_dt) > 8:
                        trade_dt = trade_dt.replace('-', '').replace(' ', '').replace(':', '')

                    kline = StockKLine(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        trade_date=trade_dt[:8] if len(trade_dt) >= 8 else trade_dt,
                        open=float(row.get('开盘') or row.get('open', 0)),
                        high=float(row.get('最高') or row.get('high', 0)),
                        low=float(row.get('最低') or row.get('low', 0)),
                        close=float(row.get('收盘') or row.get('close', 0)),
                        volume=int(row.get('成交量') or row.get('volume', 0)),
                        amount=float(row.get('成交额') or row.get('amount', 0)) / 10000,
                        data_source=self.source_name
                    )
                    klines.append(kline)
                except Exception as e:
                    logger.warning(f"Failed to parse kline: {e}")
                    continue

            if not klines and trade_date:
                logger.warning(f"Minute data returned but no data matches trade_date {trade_date}, returning all data")
                for _, row in df.iterrows():
                    try:
                        trade_dt = str(row.get('时间') or row.get('datetime', ''))
                        if len(trade_dt) > 8:
                            trade_dt = trade_dt.replace('-', '').replace(' ', '').replace(':', '')

                        kline = StockKLine(
                            symbol=symbol,
                            market=MarketType.A_STOCK,
                            trade_date=trade_dt[:8] if len(trade_dt) >= 8 else trade_dt,
                            open=float(row.get('开盘') or row.get('open', 0)),
                            high=float(row.get('最高') or row.get('high', 0)),
                            low=float(row.get('最低') or row.get('low', 0)),
                            close=float(row.get('收盘') or row.get('close', 0)),
                            volume=int(row.get('成交量') or row.get('volume', 0)),
                            amount=float(row.get('成交额') or row.get('amount', 0)) / 10000,
                            data_source=self.source_name
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
        self,
        symbol: str,
        report_date: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> List[StockFinancial]:
        try:
            code = symbol.split('.')[0]

            logger.info(f"Fetching profit sheet: symbol={code}")

            try:
                df = self.ak.stock_financial_report_sina(stock=code, symbol='利润表')
                logger.info(f"Profit sheet result type: {type(df)}, empty: {df.empty if isinstance(df, pd.DataFrame) else 'N/A'}")
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
                df = df[df['报告日'] == report_date]

            financials = []
            for _, row in df.iterrows():
                try:
                    report_period = str(row.get('报告日', ''))
                    if not report_period:
                        continue

                    income_statement = {
                        "total_revenue": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('营业总收入')), "yuan", "wanyuan"),
                        "revenue": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('营业收入')), "yuan", "wanyuan"),
                        "operating_cost": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('营业成本')), "yuan", "wanyuan"),
                        "net_income": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('净利润')), "yuan", "wanyuan"),
                        "basic_eps": FieldMapper.safe_float(row.get('基本每股收益')),
                        "operating_profit": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('营业利润')), "yuan", "wanyuan"),
                        "total_profit": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('利润总额')), "yuan", "wanyuan"),
                    }

                    mapped = {
                        "symbol": symbol,
                        "market": MarketType.A_STOCK,
                        "report_date": FieldMapper.normalize_date(report_period),
                        "report_type": "annual",
                        "publish_date": None,
                        "income_statement": income_statement,
                        "balance_sheet": {},
                        "cash_flow": {},
                        "data_source": self.source_name,
                    }

                    financial = StockFinancial(**mapped)
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
        self,
        symbol: str,
        report_date: Optional[str] = None
    ) -> List[StockFinancial]:
        """
        获取资产负债表

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）

        Returns:
            资产负债表数据列表
        """
        try:
            code = symbol.split('.')[0]

            logger.info(f"Fetching balance sheet: symbol={code}")

            try:
                df = self.ak.stock_financial_report_sina(stock=code, symbol='资产负债表')
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
                df = df[df['报告日'] == report_date]

            financials = []
            for _, row in df.iterrows():
                try:
                    report_period = str(row.get('报告日', ''))
                    if not report_period:
                        continue

                    balance_sheet = {
                        "total_assets": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('总资产')), "yuan", "wanyuan"),
                        "total_liabilities": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('负债合计')), "yuan", "wanyuan"),
                        "total_equity": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('所有者权益合计')), "yuan", "wanyuan"),
                    }

                    financial = StockFinancial(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        report_date=FieldMapper.normalize_date(report_period),
                        report_type='annual',
                        publish_date=None,
                        income_statement={},
                        balance_sheet=balance_sheet,
                        cash_flow={},
                        data_source=self.source_name
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
        self,
        symbol: str,
        report_date: Optional[str] = None
    ) -> List[StockFinancial]:
        """
        获取现金流量表

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）

        Returns:
            现金流量表数据列表
        """
        try:
            code = symbol.split('.')[0]

            logger.info(f"Fetching cashflow: symbol={code}")

            try:
                df = self.ak.stock_financial_report_sina(stock=code, symbol='现金流量表')
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
                df = df[df['报告日'] == report_date]

            financials = []
            for _, row in df.iterrows():
                try:
                    report_period = str(row.get('报告日', ''))
                    if not report_period:
                        continue

                    cash_flow = {
                        "operating_cash_flow": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('经营活动现金流量净额')), "yuan", "wanyuan"),
                        "investing_cash_flow": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('投资活动现金流量净额')), "yuan", "wanyuan"),
                        "financing_cash_flow": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('筹资活动现金流量净额')), "yuan", "wanyuan"),
                    }

                    financial = StockFinancial(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        report_date=FieldMapper.normalize_date(report_period),
                        report_type='annual',
                        publish_date=None,
                        income_statement={},
                        balance_sheet={},
                        cash_flow=cash_flow,
                        data_source=self.source_name
                    )
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
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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
            code = symbol.split('.')[0]
            exchange = 'SZ' if symbol.endswith('.SZ') or code.startswith(('000', '001', '002', '003', '300')) else 'SH'
            symbol_with_exchange = f"{code}.{exchange}"

            try:
                df = self.ak.stock_financial_analysis_indicator_em(symbol=symbol_with_exchange, indicator='按报告期')
            except Exception as e:
                logger.warning(f"Failed to get financial indicators: {e}")
                return []

            if df is None or df.empty:
                return []

            indicators = []
            for _, row in df.iterrows():
                try:
                    report_date = str(row.get('REPORT_DATE', ''))
                    if not report_date:
                        continue

                    if start_date and report_date < start_date:
                        continue
                    if end_date and report_date > end_date:
                        continue

                    indicator = {
                        'symbol': symbol,
                        'report_date': report_date,
                        'roe': FieldMapper.safe_float(row.get('ROEJQ')),
                        'roa': FieldMapper.safe_float(row.get('ZZCJLL')),
                        'gross_profit_margin': FieldMapper.safe_float(row.get('MLR')),
                        'debt_to_asset_ratio': FieldMapper.safe_float(row.get('ZCFZL')),
                        'current_ratio': FieldMapper.safe_float(row.get('LD')),
                        'data_source': self.source_name,
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

    async def get_stock_company(
        self,
        symbol: str
    ) -> StockCompany:
        """
        获取公司信息

        Args:
            symbol: 股票代码

        Returns:
            公司信息
        """
        try:
            code = symbol.split('.')[0]

            df = self.ak.stock_individual_info_em(symbol=code)

            if df is None or df.empty:
                return StockCompany(
                    symbol=symbol,
                    market=MarketType.A_STOCK,
                    company_name='',
                    industry='',
                    listing_date='',
                    data_source=self.source_name
                )

            row = df.iloc[0]
            company = StockCompany(
                symbol=symbol,
                market=MarketType.A_STOCK,
                company_name=row.get('股票简称', row.get('name', '')),
                industry=row.get('所属行业', row.get('industry', '')),
                listing_date=str(row.get('上市日期', '')),
                data_source=self.source_name
            )

            logger.info(f"Retrieved company info for {symbol}")
            return company

        except Exception as e:
            logger.error(f"Failed to get company info: {e}")
            return StockCompany(
                symbol=symbol,
                market=MarketType.A_STOCK,
                company_name='',
                industry='',
                listing_date='',
                data_source=self.source_name
            )

    async def get_daily_basic(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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
            code = symbol.split('.')[0]

            try:
                df = self.ak.stock_individual_fund_flow(stock=code)
            except Exception as e:
                logger.warning(f"Failed to get daily basic: {e}")
                return []

            if df is None or df.empty:
                return []

            basics = []
            for _, row in df.iterrows():
                try:
                    basic = {
                        'symbol': symbol,
                        'trade_date': str(row.get('日期', '')),
                        'pe_ratio': None,
                        'pb_ratio': None,
                        'total_share': None,
                        'float_share': None,
                        'data_source': self.source_name,
                    }
                    basics.append(basic)
                except Exception as e:
                    logger.warning(f"Failed to parse basic: {e}")
                    continue

            logger.info(f"Retrieved {len(basics)} daily basics")
            return basics

        except Exception as e:
            logger.error(f"Failed to get daily basic: {e}")
            return []

    async def get_trade_calendar(
        self,
        exchange: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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
            df = self.ak.tool_trade_date_hist_sina()

            if df is None or df.empty:
                return []

            calendar = []
            for _, row in df.iterrows():
                try:
                    trade_date = str(row.get('trade_date', ''))
                    normalized_date = FieldMapper.normalize_date(trade_date)

                    if start_date and normalized_date < start_date:
                        continue
                    if end_date and normalized_date > end_date:
                        continue

                    calendar.append({
                        'exchange': exchange,
                        'trade_date': normalized_date,
                        'is_open': True,
                        'data_source': self.source_name,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse calendar: {e}")
                    continue

            logger.info(f"Retrieved {len(calendar)} trade calendar dates")
            return calendar

        except Exception as e:
            logger.error(f"Failed to get trade calendar: {e}")
            return []

    async def get_shibor(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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

            periods = ['隔夜', '1周', '2周', '1月', '3月', '6月', '9月', '1年']
            period_map = {
                '隔夜': 'on',
                '1周': '1w',
                '2周': '2w',
                '1月': '1m',
                '3月': '3m',
                '6月': '6m',
                '9月': '9m',
                '1年': '1y'
            }

            for period in periods:
                try:
                    logger.info(f"Fetching SHIBOR data for period: {period}")
                    df = self.ak.rate_interbank(
                        market="上海银行同业拆借市场",
                        symbol="Shibor人民币",
                        indicator=period
                    )

                    if df is None or df.empty:
                        logger.warning(f"No SHIBOR data for period {period}")
                        continue

                    for _, row in df.iterrows():
                        try:
                            date_str = str(row.get('报告日', row.get('date', '')))
                            normalized_date = FieldMapper.normalize_date(date_str)

                            if start_date and normalized_date < start_date:
                                continue
                            if end_date and normalized_date > end_date:
                                continue

                            value = row.get('利率', row.get('value', row.get('今值')))
                            if pd.notna(value) and float(value) > 0:
                                period_key = period_map.get(period, period.lower())
                                result = MacroEconomic(
                                    indicator=f'shibor_{period_key}',
                                    period=normalized_date,
                                    value=float(value),
                                    unit='%',
                                    data_source=self.source_name
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
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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
            df = self.ak.macro_china_pmi_yearly()

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                try:
                    date = str(row.get('日期', ''))
                    date = FieldMapper.normalize_date(date)
                    value = row.get('今值')
                    if pd.notna(value):
                        result.append(MacroEconomic(
                            indicator='pmi_manufacturing',
                            period=date,
                            value=float(value),
                            unit='-',
                            data_source=self.source_name
                        ))
                except Exception as e:
                    logger.warning(f"Failed to parse PMI: {e}")
                    continue

            logger.info(f"Retrieved {len(result)} cic pmi data")
            return result

        except Exception as e:
            logger.error(f"Failed to get cic pmi: {e}")
            raise

    async def get_northbound_money_flow(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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
            df = self.ak.stock_hsgt_hist_em()

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                result.append({
                    'trade_date': FieldMapper.normalize_date(str(row.get('日期', ''))),
                    'ggt_ss': float(row.get('沪股通净流入(亿元)')) if pd.notna(row.get('沪股通净流入(亿元)')) else None,
                    'ggt_sz': float(row.get('深股通净流入(亿元)')) if pd.notna(row.get('深股通净流入(亿元)')) else None,
                    'north_money': float(row.get('北向资金净流入(亿元)')) if pd.notna(row.get('北向资金净流入(亿元)')) else None,
                    'north_money_hold': None,
                    'south_money': None,
                    'data_source': self.source_name,
                })

            logger.info(f"Retrieved {len(result)} northbound money flow")
            return result

        except Exception as e:
            logger.error(f"Failed to get northbound money flow: {e}")
            raise

    async def get_stock_new(
        self,
        market: str = "A股"
    ) -> List[Dict[str, Any]]:
        """
        获取新股发行数据

        Args:
            market: 市场类型

        Returns:
            新股数据列表
        """
        try:
            try:
                df = self.ak.stock_zh_a_new()
            except Exception as e:
                logger.warning(f"Failed to get new stocks: {e}")
                return []

            if df is None or df.empty:
                return []

            new_stocks = []
            for _, row in df.iterrows():
                try:
                    new_stocks.append({
                        'symbol': str(row.get('申购代码', '')),
                        'name': str(row.get('新股名称', '')),
                        'issue_date': str(row.get('上市日期', '')),
                        'issue_price': float(row.get('发行价格', 0)) if pd.notna(row.get('发行价格')) else None,
                        'data_source': self.source_name,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse new stock: {e}")
                    continue

            logger.info(f"Retrieved {len(new_stocks)} new stocks")
            return new_stocks

        except Exception as e:
            logger.error(f"Failed to get new stocks: {e}")
            return []

    async def get_stock_suspend(
        self,
        exchange: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取停牌股票

        Args:
            exchange: 交易所代码

        Returns:
            停牌股票列表
        """
        try:
            df = self.ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                return []

            suspend_list = []
            for _, row in df.iterrows():
                try:
                    code = str(row.get('代码', ''))
                    if not code:
                        continue

                    symbol = FieldMapper.normalize_symbol(code)

                    if exchange:
                        mapped_exchange = 'SSE' if symbol.endswith('.SH') else 'SZSE'
                        if mapped_exchange != exchange:
                            continue

                    suspend_list.append({
                        'symbol': symbol,
                        'name': str(row.get('名称', '')),
                        'suspend_reason': '',
                        'suspend_date': '',
                        'resume_date': '',
                        'data_source': self.source_name,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse suspend: {e}")
                    continue

            logger.info(f"Retrieved {len(suspend_list)} suspend stocks")
            return suspend_list

        except Exception as e:
            logger.error(f"Failed to get suspend stocks: {e}")
            return []

    async def get_stock_sectors(
        self,
        sector_type: str = "concept"
    ) -> List[StockSector]:
        """
        获取板块数据

        Args:
            sector_type: 板块类型（concept/industry）

        Returns:
            板块数据列表
        """
        try:
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
                sectors.append(StockSector(
                    sector_name=row.get('板块名称', ''),
                    sector_code=row.get('板块代码', ''),
                    sector_type=sector_type,
                    stock_count=FieldMapper.safe_int(row.get('成分股数量')),
                    description=None,
                    data_source=self.source_name
                ))

            logger.info(f"Retrieved {len(sectors)} {sector_type} sectors")
            return sectors

        except Exception as e:
            logger.error(f"Failed to get stock sectors: {e}")
            raise

    async def get_sector_quotes(
        self,
        sector_name: str
    ) -> List[Dict[str, Any]]:
        """
        获取板块实时行情

        Args:
            sector_name: 板块名称

        Returns:
            板块内股票实时行情列表
        """
        try:
            df = self.ak.stock_board_concept_spot_em(symbol=sector_name)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                code = str(row.get('代码', ''))
                symbol = FieldMapper.normalize_symbol(code)
                result.append({
                    'symbol': symbol,
                    'name': row.get('名称', ''),
                    'price': FieldMapper.safe_float(row.get('最新价')),
                    'change_pct': FieldMapper.safe_float(row.get('涨跌幅')),
                    'volume': FieldMapper.safe_int(row.get('成交量')),
                    'amount': FieldMapper.safe_float(row.get('成交额')),
                    'data_source': self.source_name,
                })

            logger.info(f"Retrieved {len(result)} quotes for sector {sector_name}")
            return result

        except Exception as e:
            logger.error(f"Failed to get sector quotes: {e}")
            return []

    async def get_stock_top_list(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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
            
            if start_date is None:
                start_date = "20240415"
            if end_date is None:
                end_date = start_date

            try:
                df = self.ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
            except Exception as e:
                logger.warning(f"Failed to get top list: {e}")
                return []

            if df is None or df.empty:
                return []

            top_list = []
            for _, row in df.iterrows():
                try:
                    stock_code = str(row.get('代码', ''))
                    if not stock_code:
                        continue

                    if stock_code != code:
                        continue

                    list_symbol = FieldMapper.normalize_symbol(stock_code)

                    top_list.append(StockTopList(
                        symbol=list_symbol,
                        trade_date=str(row.get('上榜日', '')),
                        buy_total=FieldMapper.safe_float(row.get('龙虎榜买入额', 0)),
                        sell_total=FieldMapper.safe_float(row.get('龙虎榜卖出额', 0)),
                        net_total=FieldMapper.safe_float(row.get('龙虎榜净买额', 0)),
                        data_source=self.source_name
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse top list: {e}")
                    continue

            logger.info(f"Retrieved {len(top_list)} top list records")
            return top_list

        except Exception as e:
            logger.error(f"Failed to get top list: {e}")
            return []

    async def get_stock_dividend(
        self,
        symbol: str
    ) -> List[StockDividend]:
        """
        获取分红数据

        Args:
            symbol: 股票代码

        Returns:
            分红数据列表
        """
        try:
            code = symbol.split('.')[0]

            try:
                df = self.ak.stock_history_dividend_detail(symbol=code, indicator='分红')
            except Exception as e:
                logger.warning(f"Failed to get dividend: {e}")
                return []

            if df is None or df.empty:
                return []

            dividends = []
            for _, row in df.iterrows():
                try:
                    ex_dividend_date = row.get('除权除息日', pd.NaT)
                    record_date = row.get('股权登记日', pd.NaT)

                    if pd.isna(ex_dividend_date) and pd.isna(record_date):
                        continue

                    ex_dividend_str = FieldMapper.normalize_date(str(ex_dividend_date) if not pd.isna(ex_dividend_date) else '')
                    record_date_str = FieldMapper.normalize_date(str(record_date) if not pd.isna(record_date) else '')

                    cash_dividend = FieldMapper.safe_float(row.get('派息', 0))

                    dividends.append(StockDividend(
                        symbol=symbol,
                        dividend_year=ex_dividend_str[:4] if ex_dividend_str else '',
                        ex_dividend_date=ex_dividend_str if ex_dividend_str else None,
                        record_date=record_date_str if record_date_str else None,
                        cash_dividend=cash_dividend,
                        dividend_ratio=None,
                        data_source=self.source_name
                    ))
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
        exchange: Optional[str] = None
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
            code = symbol.split('.')[0]
            
            if exchange is None:
                exchange_str = "sz" if symbol.endswith('.SZ') or code.startswith(('000', '001', '002', '003', '300')) else "sh"
            elif exchange == "SSE":
                exchange_str = "sh"
            elif exchange == "SZSE":
                exchange_str = "sz"
            else:
                exchange_str = "sh"

            try:
                if exchange_str == "sh":
                    df = self.ak.stock_margin_detail_sse(date="20240415")
                else:
                    df = self.ak.stock_margin_detail_szse(date="20240415")
            except Exception as e:
                logger.warning(f"Failed to get margin: {e}")
                return []

            if df is None or df.empty:
                return []

            margins = []
            for _, row in df.iterrows():
                try:
                    stock_code = str(row.get('标的证券代码', row.get('证券代码', '')))
                    if stock_code != code:
                        continue

                    trade_date = "20240415"

                    margin_buy = FieldMapper.safe_float(row.get('融资买入额', 0))
                    short_sell = FieldMapper.safe_float(row.get('融券卖出量', 0))
                    margin_balance = FieldMapper.safe_float(row.get('融资余额', 0))
                    short_balance = FieldMapper.safe_float(row.get('融券余额', 0))

                    margins.append(StockMargin(
                        symbol=symbol,
                        trade_date=trade_date,
                        margin_buy=margin_buy,
                        margin_sell=None,
                        margin_balance=margin_balance,
                        short_sell=short_sell,
                        short_buy=None,
                        short_balance=short_balance,
                        data_source=self.source_name
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse margin: {e}")
                    continue

            logger.info(f"Retrieved {len(margins)} margin records")
            return margins

        except Exception as e:
            logger.error(f"Failed to get margin: {e}")
            return []

    async def get_stock_news(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[StockNews]:
        """
        获取股票新闻

        Args:
            symbol: 股票代码
            limit: 返回数量限制

        Returns:
            新闻数据列表
        """
        try:
            code = symbol.split('.')[0]

            logger.info(f"Fetching stock news: symbol={code}")

            try:
                df = self.ak.stock_news_em(symbol=code)
                logger.info(f"News result type: {type(df)}, empty: {df.empty if isinstance(df, pd.DataFrame) else 'N/A'}")
            except Exception as e:
                logger.warning(f"Failed to get stock news: {e}")
                return []

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                logger.warning(f"No news data returned for {symbol}")
                return []

            if not isinstance(df, pd.DataFrame):
                logger.warning(f"Expected DataFrame but got {type(df)}")
                return []

            news_list = []
            for _, row in df.iterrows():
                try:
                    title = row.get('新闻标题', row.get('title', ''))
                    publish_time = row.get('发布时间', row.get('publish_time', row.get('time', '')))
                    url = row.get('新闻链接', row.get('url', ''))

                    if not title:
                        continue

                    news = StockNews(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        title=title,
                        url=url,
                        publish_time=publish_time,
                        content='',
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
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
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
            code = symbol.split('.')[0]

            df = self.ak.stock_individual_fund_flow(stock=code)

            if df is None or df.empty:
                return []

            fund_flows = []
            for _, row in df.iterrows():
                try:
                    fund_flows.append({
                        'symbol': symbol,
                        'trade_date': str(row.get('日期', '')),
                        'main_net_inflow': FieldMapper.safe_float(row.get('主力净流入')),
                        'large_order_net_inflow': FieldMapper.safe_float(row.get('超大单净流入')),
                        'medium_order_net_inflow': FieldMapper.safe_float(row.get('大单净流入')),
                        'small_order_net_inflow': FieldMapper.safe_float(row.get('小单净流入')),
                        'data_source': self.source_name,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse fund flow: {e}")
                    continue

            logger.info(f"Retrieved {len(fund_flows)} fund flow records")
            return fund_flows

        except Exception as e:
            logger.error(f"Failed to get fund flow: {e}")
            return []
