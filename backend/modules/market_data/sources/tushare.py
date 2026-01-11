"""
TuShare 数据源适配器

TuShare Pro A股数据源适配器实现
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import tushare as ts
import pandas as pd

from modules.market_data.sources.base import DataSourceAdapter
from modules.market_data.models import (
    StockInfo,
    StockQuote,
    StockFinancial,
    StockFinancialIndicator,
    MarketType,
    Exchange,
)

logger = logging.getLogger(__name__)


class TuShareAdapter(DataSourceAdapter):
    """TuShare Pro 数据源适配器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 TuShare 适配器

        Args:
            config: 配置字典，必须包含 api_token
        """
        super().__init__(config)

        # 从配置或环境变量获取API Token
        api_token = self.config.get("api_token") if self.config else None
        if not api_token:
            raise ValueError("TuShare API Token is required")

        # 设置TuShare Token
        ts.set_token(api_token)

        # 初始化Pro API
        self.pro = ts.pro_api()

        self.source_name = "tushare"

    def supports_market(self, market: MarketType) -> bool:
        """TuShare支持A股市场"""
        return market == MarketType.A_STOCK

    def get_priority(self) -> int:
        """TuShare优先级为1（最高）"""
        return 1

    async def test_connection(self) -> bool:
        """
        测试TuShare连接

        Returns:
            连接成功返回True
        """
        try:
            # 尝试获取股票列表作为连接测试
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
        """
        获取股票列表

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            股票信息列表
        """
        if not self.supports_market(market):
            raise ValueError(f"TuShare does not support market: {market}")

        try:
            # 调用TuShare API
            df = self.pro.stock_basic(
                exchange='',
                list_status=status,
                fields='ts_code,symbol,name,area,industry,market,exchange,list_date,is_hs'
            )

            if df is None or df.empty:
                logger.warning(f"No stocks found for market {market}, status {status}")
                return []

            # 转换为StockInfo对象列表
            stock_list = []
            for _, row in df.iterrows():
                try:
                    # 映射交易所代码
                    exchange = self._map_exchange(row.get('exchange', ''))

                    stock_info = StockInfo(
                        symbol=row['ts_code'],
                        market=MarketType.A_STOCK,
                        name=row['name'],
                        industry=row.get('industry'),
                        sector=row.get('area'),  # TuShare的area对应sector
                        listing_date=str(row['list_date']),
                        exchange=exchange,
                        status=status,
                        data_source=self.source_name
                    )
                    stock_list.append(stock_info)
                except Exception as e:
                    logger.warning(f"Failed to parse stock info for {row.get('ts_code')}: {e}")
                    continue

            logger.info(f"Retrieved {len(stock_list)} stocks from TuShare")
            return stock_list

        except Exception as e:
            logger.error(f"Failed to get stock list from TuShare: {e}")
            raise

    async def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust_type: Optional[str] = None
    ) -> List[StockQuote]:
        """
        获取日线行情

        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust_type: 复权类型（qfq/hfq/None）

        Returns:
            日线行情列表
        """
        try:
            # TuShare使用adj参数：None不复权, qfq前复权, hfq后复权
            adj = adjust_type if adjust_type in ['qfq', 'hfq'] else None

            # 调用pro_bar接口（支持复权）
            df = ts.pro_bar(
                ts_code=symbol,
                adj=adj,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"No quotes found for {symbol}")
                return []

            # 重置索引，将索引转为列
            df = df.reset_index()

            # 转换为StockQuote对象列表
            quotes = []
            for _, row in df.iterrows():
                try:
                    # TuShare pro_bar返回的日期在trade_date列
                    trade_date = str(row['trade_date']).replace('-', '')

                    quote = StockQuote(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        trade_date=trade_date,
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        pre_close=float(row['pre_close']) if pd.notna(row['pre_close']) else None,
                        volume=int(row['vol']),
                        amount=float(row['amount']) / 1000 if pd.notna(row['amount']) else None,  # 转换为万元
                        change=float(row['change']) if pd.notna(row['change']) else None,
                        change_pct=float(row['pct_chg']) if pd.notna(row['pct_chg']) else None,
                        data_source=self.source_name
                    )
                    quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Failed to parse quote for {symbol}: {e}")
                    continue

            logger.info(f"Retrieved {len(quotes)} quotes for {symbol} from TuShare")
            return quotes

        except Exception as e:
            logger.error(f"Failed to get daily quotes for {symbol} from TuShare: {e}")
            raise

    async def get_stock_financials(
        self,
        symbol: str,
        report_date: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> List[StockFinancial]:
        """
        获取财务报表

        注意：TuShare的财务接口ts_code是必填参数

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）
            report_type: 报告类型

        Returns:
            财务报表列表
        """
        try:
            # 构建查询参数（ts_code必填）
            params = {'ts_code': symbol}
            if report_date:
                params['period'] = report_date

            # 调用利润表接口
            df_income = self.pro.income(**params)

            if df_income is None or df_income.empty:
                logger.warning(f"No income data found for {symbol}")
                return []

            # 转换为StockFinancial对象列表
            financials = []
            for _, row in df_income.iterrows():
                try:
                    financial = StockFinancial(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        report_date=str(row['end_date']),
                        report_type=row.get('report_type', 'annual'),
                        publish_date=str(row['ann_date']) if pd.notna(row['ann_date']) else None,
                        income_statement=self._parse_income_statement(row),
                        balance_sheet={},  # 需要单独调用balancesheet
                        cash_flow={},  # 需要单独调用cashflow
                        data_source=self.source_name
                    )
                    financials.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to parse financial for {symbol}: {e}")
                    continue

            logger.info(f"Retrieved {len(financials)} financials for {symbol} from TuShare")
            return financials

        except Exception as e:
            logger.error(f"Failed to get financials for {symbol} from TuShare: {e}")
            raise

    async def get_financial_indicators(
        self,
        symbol: str,
        report_date: Optional[str] = None
    ) -> List[StockFinancialIndicator]:
        """
        获取财务指标

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）

        Returns:
            财务指标列表
        """
        try:
            # 构建查询参数
            params = {'ts_code': symbol}
            if report_date:
                params['period'] = report_date

            # 调用财务指标接口
            df = self.pro.fina_indicator(**params)

            if df is None or df.empty:
                logger.warning(f"No financial indicators found for {symbol}")
                return []

            # 转换为StockFinancialIndicator对象列表
            indicators = []
            for _, row in df.iterrows():
                try:
                    indicator = StockFinancialIndicator(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        report_date=str(row['end_date']),
                        publish_date=str(row['ann_date']) if pd.notna(row['ann_date']) else None,
                        roe=float(row['roe']) / 100 if pd.notna(row['roe']) else None,  # 转换为小数
                        roa=float(row['roa']) / 100 if pd.notna(row['roa']) else None,
                        debt_to_assets=float(row['debt_to_assets']) if pd.notna(row['debt_to_assets']) else None,
                        current_ratio=float(row['current_ratio']) if pd.notna(row['current_ratio']) else None,
                        quick_ratio=float(row['quick_ratio']) if pd.notna(row['quick_ratio']) else None,
                        eps=float(row['basic_eps']) if pd.notna(row['basic_eps']) else None,
                        data_source=self.source_name
                    )
                    indicators.append(indicator)
                except Exception as e:
                    logger.warning(f"Failed to parse indicator for {symbol}: {e}")
                    continue

            logger.info(f"Retrieved {len(indicators)} indicators for {symbol} from TuShare")
            return indicators

        except Exception as e:
            logger.error(f"Failed to get financial indicators for {symbol} from TuShare: {e}")
            raise

    def _map_exchange(self, exchange_str: str) -> Exchange:
        """
        映射交易所代码

        Args:
            exchange_str: TuShare交易所代码

        Returns:
            Exchange枚举值
        """
        exchange_map = {
            'SSE': Exchange.SSE,
            'SZSE': Exchange.SZSE,
        }
        return exchange_map.get(exchange_str, Exchange.SSE)

    def _parse_income_statement(self, row: pd.Series) -> Dict[str, Any]:
        """
        解析利润表数据

        Args:
            row: DataFrame行

        Returns:
            利润表字典
        """
        return {
            'total_revenue': float(row['total_revenue']) if pd.notna(row['total_revenue']) else None,
            'revenue': float(row['revenue']) if pd.notna(row['revenue']) else None,
            'operating_cost': float(row['oper_cost']) if pd.notna(row['oper_cost']) else None,
            'net_income': float(row['n_income']) if pd.notna(row['n_income']) else None,
            'basic_eps': float(row['basic_eps']) if pd.notna(row['basic_eps']) else None,
        }
