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
    StockKLine,
    StockFinancial,
    StockFinancialIndicator,
    StockCompany,
    MacroEconomic,
    MarketType,
    Exchange,
)
from core.market_data.tools.field_mapper import TuShareFieldMapper

logger = logging.getLogger(__name__)


class TuShareAdapter(DataSourceAdapter):
    """TuShare Pro 数据源适配器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        api_token = self.config.get("api_token") if self.config else None
        if not api_token:
            raise ValueError("TuShare API Token is required")

        ts.set_token(api_token)
        self.pro = ts.pro_api()
        self.source_name = "tushare"

    def supports_market(self, market: MarketType) -> bool:
        return market == MarketType.A_STOCK

    def get_priority(self) -> int:
        return 1

    async def test_connection(self) -> bool:
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
    ) -> List[StockKLine]:
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
                    kline = StockKLine(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        trade_date=str(row['trade_date']),
                        open=float(row['open']) if pd.notna(row['open']) else 0,
                        high=float(row['high']) if pd.notna(row['high']) else 0,
                        low=float(row['low']) if pd.notna(row['low']) else 0,
                        close=float(row['close']) if pd.notna(row['close']) else 0,
                        volume=int(row['vol']) if pd.notna(row['vol']) else 0,
                        amount=float(row['amount']) / 1000 if pd.notna(row['amount']) else None,
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
            params = {'ts_code': symbol}
            if report_date:
                params['period'] = report_date

            df = self.pro.cashflow(**params)

            if df is None or df.empty:
                return []

            financials = []
            for _, row in df.iterrows():
                try:
                    mapped = TuShareFieldMapper.map_financial_cashflow(row, symbol)
                    financial = StockFinancial(**mapped)
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
                result.append({
                    'symbol': symbol,
                    'trade_date': str(row['trade_date']),
                    'pe': float(row['pe']) if pd.notna(row['pe']) else None,
                    'pe_ttm': float(row['pe_ttm']) if pd.notna(row['pe_ttm']) else None,
                    'pb': float(row['pb']) if pd.notna(row['pb']) else None,
                    'ps': float(row['ps']) if pd.notna(row['ps']) else None,
                    'ps_ttm': float(row['ps_ttm']) if pd.notna(row['ps_ttm']) else None,
                    'dv_ratio': float(row['dv_ratio']) if pd.notna(row['dv_ratio']) else None,
                    'dv_ttm': float(row['dv_ttm']) if pd.notna(row['dv_ttm']) else None,
                    'total_share': float(row['total_share']) if pd.notna(row['total_share']) else None,
                    'float_share': float(row['float_share']) if pd.notna(row['float_share']) else None,
                    'free_share': float(row['free_share']) if pd.notna(row['free_share']) else None,
                    'total_mv': float(row['total_mv']) if pd.notna(row['total_mv']) else None,
                    'circ_mv': float(row['circ_mv']) if pd.notna(row['circ_mv']) else None,
                    'data_source': self.source_name,
                })

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
                result.append({
                    'symbol': row.get('ts_code'),
                    'trade_date': str(row['trade_date']),
                    'buy_elg_vol': float(row['buy_elg_vol']) if pd.notna(row.get('buy_elg_vol')) else None,
                    'buy_elg_amount': float(row['buy_elg_amount']) if pd.notna(row.get('buy_elg_amount')) else None,
                    'sell_elg_vol': float(row['sell_elg_vol']) if pd.notna(row.get('sell_elg_vol')) else None,
                    'sell_elg_amount': float(row['sell_elg_amount']) if pd.notna(row.get('sell_elg_amount')) else None,
                    'buy_lg_vol': float(row['buy_lg_vol']) if pd.notna(row.get('buy_lg_vol')) else None,
                    'buy_lg_amount': float(row['buy_lg_amount']) if pd.notna(row.get('buy_lg_amount')) else None,
                    'sell_lg_vol': float(row['sell_lg_vol']) if pd.notna(row.get('sell_lg_vol')) else None,
                    'sell_lg_amount': float(row['sell_lg_amount']) if pd.notna(row.get('sell_lg_amount')) else None,
                    'buy_md_vol': float(row['buy_md_vol']) if pd.notna(row.get('buy_md_vol')) else None,
                    'buy_md_amount': float(row['buy_md_amount']) if pd.notna(row.get('buy_md_amount')) else None,
                    'sell_md_vol': float(row['sell_md_vol']) if pd.notna(row.get('sell_md_vol')) else None,
                    'sell_md_amount': float(row['sell_md_amount']) if pd.notna(row.get('sell_md_amount')) else None,
                    'buy_sm_vol': float(row['buy_sm_vol']) if pd.notna(row.get('buy_sm_vol')) else None,
                    'buy_sm_amount': float(row['buy_sm_amount']) if pd.notna(row.get('buy_sm_amount')) else None,
                    'sell_sm_vol': float(row['sell_sm_vol']) if pd.notna(row.get('sell_sm_vol')) else None,
                    'sell_sm_amount': float(row['sell_sm_amount']) if pd.notna(row.get('sell_sm_amount')) else None,
                    'net_mf_vol': float(row['net_mf_vol']) if pd.notna(row.get('net_mf_vol')) else None,
                    'net_mf_amount': float(row['net_mf_amount']) if pd.notna(row.get('net_mf_amount')) else None,
                    'data_source': self.source_name,
                })

            logger.info(f"Retrieved {len(result)} individual money flow")
            return result

        except Exception as e:
            logger.error(f"Failed to get individual money flow: {e}")
            raise
