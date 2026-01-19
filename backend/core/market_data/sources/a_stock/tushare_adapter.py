"""
TuShare 数据源适配器（完整版）

TuShare Pro A股数据源适配器完整实现
包含所有文档定义的接口
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import tushare as ts
import pandas as pd

from core.market_data.sources.base import DataSourceAdapter
from core.market_data.models import (
    StockInfo,
    StockQuote,
    StockMinuteQuote,
    StockFinancial,
    FinancialIncome,
    FinancialBalance,
    FinancialCashFlow,
    StockFinancialIndicator,
    StockCompany,
    MacroEconomic,
    MarketType,
    Exchange,
    StockMoneyFlow,
    StockHSGTMoneyFlow,
    MarketNews,
)
from core.market_data.tools.data_cleaner import DataCleaner

logger = logging.getLogger(__name__)


class TuShareAdapter(DataSourceAdapter):
    """TuShare Pro 数据源适配器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        api_token = self.config.get("api_token") if self.config else None
        self._has_token = bool(api_token)

        if self._has_token:
            ts.set_token(api_token)
            self.pro = ts.pro_api()
            logger.info("TuShare adapter initialized with API token")
        else:
            self.pro = None
            logger.warning("TuShare adapter initialized without API token - will be disabled")

        self.source_name = "tushare"
        # 设置默认优先级（TuShare 是主要数据源，优先级最高）
        self._priority = 1

    def supports_market(self, market: MarketType) -> bool:
        return market == MarketType.A_STOCK

    async def test_connection(self) -> bool:
        if not self._has_token or self.pro is None:
            logger.warning("TuShare adapter cannot test connection - no API token configured")
            return False
        try:
            df = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            return df is not None and len(df) > 0
        except Exception as e:
            logger.error(f"TuShare connection test failed: {e}")
            return False

    async def get_stock_list(
        self,
        market: MarketType,
        status: str = "L"
    ) -> List[StockInfo]:
        if not self._has_token or self.pro is None:
            raise RuntimeError("TuShare API token not configured - cannot fetch data")
        try:
            df = self.pro.stock_basic(
                exchange='',
                list_status=status,
                fields='ts_code,symbol,name,area,industry,market,exchange,list_date,is_hs'
            )

            if df is None or df.empty:
                return []

            stock_list = []
            for _, row in df.iterrows():
                try:
                    mapped = TuShareFieldMapper.map_stock_info(row)
                    stock_info = StockInfo(**mapped)
                    stock_list.append(stock_info)
                except Exception as e:
                    logger.warning(f"Failed to parse stock info: {e}")
                    continue

            logger.info(f"Retrieved {len(stock_list)} stocks from TuShare")
            return stock_list

        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            raise

    async def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust_type: Optional[str] = None
    ) -> List[StockQuote]:
        if not self._has_token or self.pro is None:
            raise RuntimeError("TuShare API token not configured - cannot fetch data")
        try:
            adj = adjust_type if adjust_type in ['qfq', 'hfq'] else None

            df = ts.pro_bar(
                ts_code=symbol,
                adj=adj,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                return []

            df = df.reset_index()

            quotes = []
            for _, row in df.iterrows():
                try:
                    mapped = TuShareFieldMapper.map_stock_quote(row, symbol)
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
    ) -> List[StockMinuteQuote]:
        """
        获取分钟K线数据

        Args:
            symbol: 股票代码
            trade_date: 交易日期（YYYYMMDD）
            freq: K线频率（1min/5min/15min/30min/60min）

        Returns:
            分钟K线数据列表
        """
        try:
            params = {'ts_code': symbol}
            if trade_date:
                params['trade_date'] = trade_date

            df = self.pro.stk_mins(**params)

            if df is None or df.empty:
                return []

            klines = []
            for _, row in df.iterrows():
                try:
                    mapped = DataCleaner.clean_minute_quote(row.to_dict(), "tushare")
                    if mapped:
                        kline = StockMinuteQuote(**mapped)
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
            params = {'ts_code': symbol}
            if report_date:
                params['period'] = report_date

            df_income = self.pro.income(**params)

            if df_income is None or df_income.empty:
                return []

            financials = []
            for _, row in df_income.iterrows():
                try:
                    mapped = TuShareFieldMapper.map_financial_income(row, symbol)
                    financial = StockFinancial(**mapped)
                    financials.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to parse financial: {e}")
                    continue

            logger.info(f"Retrieved {len(financials)} financials for {symbol}")
            return financials

        except Exception as e:
            logger.error(f"Failed to get financials: {e}")
            raise

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
            params = {'ts_code': symbol}
            if report_date:
                params['period'] = report_date

            df = self.pro.balancesheet(**params)

            if df is None or df.empty:
                return []

            financials = []
            for _, row in df.iterrows():
                try:
                    mapped = TuShareFieldMapper.map_financial_balance(row, symbol)
                    financial = StockFinancial(**mapped)
                    financials.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to parse balance sheet: {e}")
                    continue

            logger.info(f"Retrieved {len(financials)} balance sheets for {symbol}")
            return financials

        except Exception as e:
            logger.error(f"Failed to get balance sheet: {e}")
            raise

    async def get_stock_cashflow(
        self,
        symbol: str,
        report_date: Optional[str] = None
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
            params = {'ts_code': symbol}
            if report_date:
                params['period'] = report_date

            df = self.pro.cashflow(**params)

            if df is None or df.empty:
                return []

            financials = []
            for _, row in df.iterrows():
                try:
                    mapped = DataCleaner.clean_financial_cashflow(row.to_dict(), "tushare")
                    if mapped:
                        financial = FinancialCashFlow(**mapped)
                        financials.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to parse cashflow: {e}")
                    continue

            logger.info(f"Retrieved {len(financials)} cashflows for {symbol}")
            return financials

        except Exception as e:
            logger.error(f"Failed to get cashflow: {e}")
            raise

    async def get_financial_indicators(
        self,
        symbol: str,
        report_date: Optional[str] = None
    ) -> List[StockFinancialIndicator]:
        try:
            params = {'ts_code': symbol}
            if report_date:
                params['period'] = report_date

            df = self.pro.fina_indicator(**params)

            if df is None or df.empty:
                return []

            indicators = []
            for _, row in df.iterrows():
                try:
                    mapped = TuShareFieldMapper.map_financial_indicator(row, symbol)
                    indicator = StockFinancialIndicator(**mapped)
                    indicators.append(indicator)
                except Exception as e:
                    logger.warning(f"Failed to parse indicator: {e}")
                    continue

            logger.info(f"Retrieved {len(indicators)} indicators for {symbol}")
            return indicators

        except Exception as e:
            logger.error(f"Failed to get financial indicators: {e}")
            raise

    async def get_stock_company(
        self,
        symbol: str
    ) -> Optional[StockCompany]:
        """
        获取公司详细信息

        Args:
            symbol: 股票代码

        Returns:
            公司详细信息，未找到返回None
        """
        try:
            exchange = 'SSE' if symbol.endswith('.SH') else 'SZSE'
            df = self.pro.stock_company(exchange=exchange)

            if df is None or df.empty:
                return None

            filtered_df = df[df['ts_code'] == symbol]
            if filtered_df.empty:
                return None

            row = filtered_df.iloc[0]

            company = StockCompany(
                symbol=symbol,
                market=MarketType.A_STOCK,
                company_name=row.get('company_name', row.get('com_name', '')),
                company_name_en=row.get('company_name_en'),
                industry=row.get('industry'),
                sector=row.get('area'),
                listing_date=str(row.get('list_date', row.get('list_date', ''))),
                contact={
                    'legal_representative': row.get('chairman'),
                    'secretary': row.get('secretary'),
                    'phone': row.get('office_address'),
                },
                business={
                    'main_business': row.get('main_business'),
                    'business_scope': row.get('business_scope'),
                },
                capital_structure={
                    'share_capital': float(row.get('share_capital', 0)) / 100000000 if pd.notna(row.get('share_capital')) else None,
                },
                data_source=self.source_name
            )

            logger.info(f"Retrieved company info for {symbol}")
            return company

        except Exception as e:
            logger.error(f"Failed to get company info: {e}")
            raise

    async def get_daily_basic(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取每日指标（市盈率、市净率等）

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            每日指标列表
        """
        try:
            params = {'ts_code': symbol}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.pro.daily_basic(**params)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                mapped = DataCleaner.clean_daily_indicator(row.to_dict(), "tushare")
                if mapped:
                    result.append(mapped)

            logger.info(f"Retrieved {len(result)} daily basics for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Failed to get daily basic: {e}")
            raise

    async def get_trade_calendar(
        self,
        exchange: str = "SSE",
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
            params = {'exchange': exchange}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.pro.trade_cal(**params)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                result.append({
                    'exchange': exchange,
                    'cal_date': str(row['cal_date']),
                    'is_open': bool(row['is_open']),
                })

            logger.info(f"Retrieved {len(result)} trade days for {exchange}")
            return result

        except Exception as e:
            logger.error(f"Failed to get trade calendar: {e}")
            raise

    async def get_shibor(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[MacroEconomic]:
        """
        获取SHIBOR利率数据

        Args:
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            SHIBOR数据列表
        """
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            logger.info(f"Fetching Tushare SHIBOR data: params={params}")
            df = self.pro.shibor(**params)

            if df is None or df.empty:
                logger.warning(f"No SHIBOR data returned from Tushare")
                return []

            result = []
            for _, row in df.iterrows():
                date = str(row.get('date', ''))
                if not date:
                    continue
                for period in ['on', '1w', '2w', '1m', '3m', '6m', '9m', '1y']:
                    rate = row.get(period)
                    if pd.notna(rate) and rate > 0:
                        result.append(MacroEconomic(
                            indicator=f'shibor_{period}',
                            period=date,
                            value=float(rate),
                            unit='%',
                            data_source=self.source_name
                        ))

            logger.info(f"Retrieved {len(result)} shibor rates")
            return result

        except Exception as e:
            logger.error(f"Failed to get shibor: {e}")
            return []

    async def get_shibor_quote(
        self,
        date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取SHIBOR报价数据

        Args:
            date: 日期（YYYYMMDD）

        Returns:
            SHIBOR报价列表
        """
        try:
            params = {}
            if date:
                params['date'] = date

            df = self.pro.shibor_quote(**params)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                result.append({
                    'date': str(row['date']),
                    'type': row.get('type'),
                    'term': row.get('term'),
                    'bid': float(row['bid']) if pd.notna(row['bid']) else None,
                    'ask': float(row['ask']) if pd.notna(row['ask']) else None,
                    'deal': float(row['deal']) if pd.notna(row['deal']) else None,
                    'data_source': self.source_name,
                })

            logger.info(f"Retrieved {len(result)} shibor quotes")
            return result

        except Exception as e:
            logger.error(f"Failed to get shibor quote: {e}")
            raise

    async def get_cpi(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[MacroEconomic]:
        """
        获取CPI数据

        Args:
            start_date: 开始日期（YYYYMM）
            end_date: 结束日期（YYYYMM）

        Returns:
            CPI数据列表
        """
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.pro.cn_cpi(**params)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                period = str(row.get('month', row.get('cpi', '')))
                result.append(MacroEconomic(
                    indicator='cpi',
                    period=period,
                    value=float(row.get('cpi', row.get('cpi_yoy', 0))),
                    unit='%',
                    yoy=float(row.get('cpi_yoy', 0)),
                    data_source=self.source_name
                ))

            logger.info(f"Retrieved {len(result)} cpi data")
            return result

        except Exception as e:
            logger.error(f"Failed to get cpi: {e}")
            raise

    async def get_ppi(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[MacroEconomic]:
        """
        获取PPI数据

        Args:
            start_date: 开始日期（YYYYMM）
            end_date: 结束日期（YYYYMM）

        Returns:
            PPI数据列表
        """
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.pro.cn_ppi(**params)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                period = str(row.get('month', row.get('ppi', '')))
                result.append(MacroEconomic(
                    indicator='ppi',
                    period=period,
                    value=float(row.get('ppi', row.get('ppi_yoy', 0))),
                    unit='%',
                    yoy=float(row.get('ppi_yoy', 0)),
                    data_source=self.source_name
                ))

            logger.info(f"Retrieved {len(result)} ppi data")
            return result

        except Exception as e:
            logger.error(f"Failed to get ppi: {e}")
            raise

    async def get_money_supply(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[MacroEconomic]:
        """
        获取货币供应量数据

        Args:
            start_date: 开始日期（YYYYMM）
            end_date: 结束日期（YYYYMM）

        Returns:
            货币供应量数据列表
        """
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.pro.cn_m(**params)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                result.append(MacroEconomic(
                    indicator=f'money_supply_{row.get("stat")}',
                    period=str(row['month']),
                    value=float(row['m2']),
                    unit='亿元',
                    yoy=float(row['m2_yoy']) if pd.notna(row['m2_yoy']) else None,
                    mom=float(row['m2_mom']) if pd.notna(row['m2_mom']) else None,
                    data_source=self.source_name
                ))

            logger.info(f"Retrieved {len(result)} money supply data")
            return result

        except Exception as e:
            logger.error(f"Failed to get money supply: {e}")
            raise

    async def get_pmi_caixin(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[MacroEconomic]:
        """
        获取财新PMI数据

        Args:
            start_date: 开始日期（YYYYMM）
            end_date: 结束日期（YYYYMM）

        Returns:
            PMI数据列表
        """
        try:
            params = {}
            if start_date:
                start_m = start_date[:6] if len(start_date) >= 6 else start_date
                params['start_m'] = start_m
            if end_date:
                end_m = end_date[:6] if len(end_date) >= 6 else end_date
                params['end_m'] = end_m

            df = self.pro.cn_pmi(**params)

            if df is None or df.empty:
                logger.warning(f"No PMI data returned for caixin")
                return []

            result = []
            for _, row in df.iterrows():
                pmi_value = row.get('PMI011200')
                if pd.notna(pmi_value) and pmi_value > 0:
                    result.append(MacroEconomic(
                        indicator='pmi_caixin',
                        period=str(row['MONTH']),
                        value=float(pmi_value),
                        unit='-',
                        data_source=self.source_name
                    ))

            logger.info(f"Retrieved {len(result)} caixin pmi data")
            return result

        except Exception as e:
            logger.error(f"Failed to get caixin pmi: {e}")
            return []

    async def get_pmi_cic(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[MacroEconomic]:
        """
        获取中采PMI数据

        Args:
            start_date: 开始日期（YYYYMM）
            end_date: 结束日期（YYYYMM）

        Returns:
            PMI数据列表
        """
        try:
            params = {}
            if start_date:
                start_m = start_date[:6] if len(start_date) >= 6 else start_date
                params['start_m'] = start_m
            if end_date:
                end_m = end_date[:6] if len(end_date) >= 6 else end_date
                params['end_m'] = end_m

            df = self.pro.cn_pmi(**params)

            if df is None or df.empty:
                logger.warning(f"No PMI data returned for cic")
                return []

            result = []
            for _, row in df.iterrows():
                pmi_value = row.get('PMI010200')
                if pd.notna(pmi_value) and pmi_value > 0:
                    result.append(MacroEconomic(
                        indicator='pmi_manufacturing',
                        period=str(row['MONTH']),
                        value=float(pmi_value),
                        unit='-',
                        data_source=self.source_name
                    ))

            logger.info(f"Retrieved {len(result)} cic pmi data")
            return result

        except Exception as e:
            logger.error(f"Failed to get cic pmi: {e}")
            return []

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
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.pro.moneyflow_hsgt(**params)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                result.append({
                    'trade_date': str(row.get('trade_date', '')),
                    'ggt_ss': float(row.get('ggt_ss')) if pd.notna(row.get('ggt_ss')) else None,
                    'ggt_sz': float(row.get('ggt_sz')) if pd.notna(row.get('ggt_sz')) else None,
                    'north_money': float(row.get('north_money')) if pd.notna(row.get('north_money')) else None,
                    'north_money_hold': None,
                    'south_money': float(row.get('south_money')) if pd.notna(row.get('south_money')) else None,
                    'data_source': self.source_name,
                })

            logger.info(f"Retrieved {len(result)} northbound money flow")
            return result

        except Exception as e:
            logger.error(f"Failed to get northbound money flow: {e}")
            raise

    async def get_individual_money_flow(
        self,
        symbol: Optional[str] = None,
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
            个股资金流向列表
        """
        try:
            params = {}
            if symbol:
                params['ts_code'] = symbol
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
                
            df = self.pro.moneyflow(**params)
            
            if df is None or df.empty:
                return []
                
            result = []
            for _, row in df.iterrows():
                mapped = DataCleaner.clean_stock_money_flow(row.to_dict(), "tushare")
                if mapped:
                    result.append(mapped)
                    
            logger.info(f"Retrieved {len(result)} individual money flow")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get individual money flow: {e}")
            raise

    async def get_market_news(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        src: str = "sina"
    ) -> List[MarketNews]:
        """
        获取市场新闻
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD HH:MM:SS)
            end_date: 结束日期 (YYYY-MM-DD HH:MM:SS)
            src: 新闻来源 (sina/10jqka/eastmoney/yuncaijing)
            
        Returns:
            新闻列表
        """
        try:
            params = {'src': src}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
                
            # TuShare news 接口
            df = self.pro.news(**params)
            
            if df is None or df.empty:
                return []
                
            news_list = []
            for _, row in df.iterrows():
                try:
                    news_id = str(row.get('news_id', ''))
                    if not news_id:
                        # 如果没有ID，使用来源+时间+标题生成一个
                        import hashlib
                        content_str = f"{src}_{row.get('datetime')}_{row.get('title')}"
                        news_id = hashlib.md5(content_str.encode()).hexdigest()
                        
                    news = MarketNews(
                        news_id=news_id,
                        ts_code=None,  # Tushare news 接口通常不返回关联股票
                        datetime=str(row.get('datetime', '')),
                        title=str(row.get('title', '')),
                        content=str(row.get('content', '')),
                        source=src,
                        data_source=self.source_name
                    )
                    news_list.append(news)
                except Exception as e:
                    logger.warning(f"Failed to parse news: {e}")
                    continue
                    
            logger.info(f"Retrieved {len(news_list)} news items from {src}")
            return news_list
            
        except Exception as e:
            logger.error(f"Failed to get market news: {e}")
            return []
