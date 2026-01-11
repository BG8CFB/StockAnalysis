"""
AkShare 数据源适配器

AkShare A股数据源适配器实现（作为TuShare的降级备用）
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import akshare as ak
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


class AkShareAdapter(DataSourceAdapter):
    """AkShare 数据源适配器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 AkShare 适配器

        Args:
            config: 配置字典（AkShare不需要认证）
        """
        super().__init__(config)
        self.source_name = "akshare"

    def supports_market(self, market: MarketType) -> bool:
        """AkShare支持A股市场"""
        return market == MarketType.A_STOCK

    def get_priority(self) -> int:
        """AkShare优先级为2（作为降级备用）"""
        return 2

    async def test_connection(self) -> bool:
        """
        测试AkShare连接

        Returns:
            连接成功返回True
        """
        try:
            # 尝试获取A股实时行情作为连接测试
            df = ak.stock_zh_a_spot_em()
            return df is not None and len(df) > 0
        except Exception as e:
            logger.error(f"AkShare connection test failed: {e}")
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
            raise ValueError(f"AkShare does not support market: {market}")

        try:
            # 调用AkShare API获取A股实时行情（包含股票列表）
            df = ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                logger.warning(f"No stocks found from AkShare")
                return []

            # 转换为StockInfo对象列表
            stock_list = []
            for _, row in df.iterrows():
                try:
                    # AkShare返回的代码格式：600519，需要添加交易所后缀
                    code = str(row['代码'])
                    symbol = self._normalize_symbol(code)

                    # 判断交易所
                    exchange = self._get_exchange_by_code(code)

                    stock_info = StockInfo(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        name=row['名称'],
                        industry=None,  # AkShare实时行情没有行业信息
                        sector=None,
                        listing_date="",  # 需要额外调用接口获取
                        exchange=exchange,
                        status=status,
                        data_source=self.source_name
                    )
                    stock_list.append(stock_info)
                except Exception as e:
                    logger.warning(f"Failed to parse stock info for {row.get('代码')}: {e}")
                    continue

            logger.info(f"Retrieved {len(stock_list)} stocks from AkShare")
            return stock_list

        except Exception as e:
            logger.error(f"Failed to get stock list from AkShare: {e}")
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
            symbol: 股票代码（如600519.SH）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust_type: 复权类型（qfq前复权/hfq后复权）

        Returns:
            日线行情列表
        """
        try:
            # 移除交易所后缀，AkShare使用纯代码
            code = symbol.split('.')[0]

            # 转换日期格式：YYYYMMDD -> YYYY-MM-DD
            start = self._format_date_akshare(start_date) if start_date else "19900101"
            end = self._format_date_akshare(end_date) if end_date else "21000101"

            # AkShare使用adjust参数：''不复权, 'qfq'前复权, 'hfq'后复权
            adjust = adjust_type if adjust_type in ['qfq', 'hfq'] else ""

            # 调用AkShare接口
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start,
                end_date=end,
                adjust=adjust
            )

            if df is None or df.empty:
                logger.warning(f"No quotes found for {symbol}")
                return []

            # 转换为StockQuote对象列表
            quotes = []
            for _, row in df.iterrows():
                try:
                    # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
                    trade_date = str(row['日期']).replace('-', '')

                    quote = StockQuote(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        trade_date=trade_date,
                        open=float(row['开盘']),
                        high=float(row['最高']),
                        low=float(row['最低']),
                        close=float(row['收盘']),
                        pre_close=None,  # AkShare没有昨收价
                        volume=int(row['成交量']),
                        amount=float(row['成交额']) / 10000,  # 转换为万元
                        change=float(row['涨跌额']) if pd.notna(row['涨跌额']) else None,
                        change_pct=float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None,
                        turnover_rate=float(row['换手率']) if pd.notna(row['换手率']) else None,
                        data_source=self.source_name
                    )
                    quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Failed to parse quote for {symbol} on {row.get('日期')}: {e}")
                    continue

            logger.info(f"Retrieved {len(quotes)} quotes for {symbol} from AkShare")
            return quotes

        except Exception as e:
            logger.error(f"Failed to get daily quotes for {symbol} from AkShare: {e}")
            raise

    async def get_stock_financials(
        self,
        symbol: str,
        report_date: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> List[StockFinancial]:
        """
        获取财务报表

        注意：AkShare的财务接口不支持按股票筛选，需要获取全部数据后本地筛选

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）
            report_type: 报告类型

        Returns:
            财务报表列表
        """
        try:
            # AkShare财务接口不支持按股票筛选，需获取全部数据
            # 警告：这个接口返回数据量很大
            logger.warning("AkShare financial API returns all stocks data, filtering locally")

            # 调用利润表接口
            df = ak.stock_profit_sheet_by_report_em(symbol=symbol.split('.')[0])

            if df is None or df.empty:
                logger.warning(f"No financial data found for {symbol}")
                return []

            # 如果指定了报告期，进行筛选
            if report_date:
                df = df[df['报告期'] == report_date]

            # 转换为StockFinancial对象列表
            financials = []
            for _, row in df.iterrows():
                try:
                    financial = StockFinancial(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        report_date=str(row['报告期']),
                        report_type=report_type or 'annual',
                        publish_date=None,  # AkShare没有公告日期
                        income_statement=self._parse_income_statement_ak(row),
                        balance_sheet={},  # 需要单独调用接口
                        cash_flow={},  # 需要单独调用接口
                        data_source=self.source_name
                    )
                    financials.append(financial)
                except Exception as e:
                    logger.warning(f"Failed to parse financial for {symbol}: {e}")
                    continue

            logger.info(f"Retrieved {len(financials)} financials for {symbol} from AkShare")
            return financials

        except Exception as e:
            logger.error(f"Failed to get financials for {symbol} from AkShare: {e}")
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
            # 移除交易所后缀
            code = symbol.split('.')[0]

            # 调用财务指标接口
            df = ak.stock_financial_abstract(symbol=code)

            if df is None or df.empty:
                logger.warning(f"No financial indicators found for {symbol}")
                return []

            # 如果指定了报告期，进行筛选
            if report_date:
                df = df[df['报告期'] == report_date]

            # 转换为StockFinancialIndicator对象列表
            indicators = []
            for _, row in df.iterrows():
                try:
                    indicator = StockFinancialIndicator(
                        symbol=symbol,
                        market=MarketType.A_STOCK,
                        report_date=str(row['报告期']),
                        publish_date=None,
                        roe=None,  # AkShare没有ROE
                        roa=None,
                        debt_to_assets=None,
                        current_ratio=None,
                        quick_ratio=None,
                        eps=None,  # 需要从其他字段提取
                        data_source=self.source_name
                    )
                    indicators.append(indicator)
                except Exception as e:
                    logger.warning(f"Failed to parse indicator for {symbol}: {e}")
                    continue

            logger.info(f"Retrieved {len(indicators)} indicators for {symbol} from AkShare")
            return indicators

        except Exception as e:
            logger.error(f"Failed to get financial indicators for {symbol} from AkShare: {e}")
            raise

    def _normalize_symbol(self, code: str) -> str:
        """
        标准化股票代码（添加交易所后缀）

        Args:
            code: 股票代码（如600519）

        Returns:
            标准化代码（如600519.SH）
        """
        exchange = self._get_exchange_by_code(code)
        return f"{code}.{exchange.value}"

    def _get_exchange_by_code(self, code: str) -> Exchange:
        """
        根据股票代码判断交易所

        Args:
            code: 股票代码

        Returns:
            Exchange枚举值
        """
        # 上海交易所：60/688/689开头
        if code.startswith(('60', '688', '689')):
            return Exchange.SSE
        # 深圳交易所：00/30/301开头
        elif code.startswith(('00', '30', '301')):
            return Exchange.SZSE
        else:
            # 默认上海交易所
            return Exchange.SSE

    def _format_date_akshare(self, date_str: str) -> str:
        """
        转换日期格式：YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: YYYYMMDD格式日期

        Returns:
            YYYY-MM-DD格式日期
        """
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    def _parse_income_statement_ak(self, row: pd.Series) -> Dict[str, Any]:
        """
        解析利润表数据（AkShare字段）

        Args:
            row: DataFrame行

        Returns:
            利润表字典
        """
        return {
            'total_revenue': None,  # AkShare没有此字段
            'revenue': self._safe_float(row.get('营业收入')),
            'operating_cost': self._safe_float(row.get('营业成本')),
            'net_income': self._safe_float(row.get('净利润')),
            'basic_eps': None,  # AkShare没有此字段
        }

    def _safe_float(self, value) -> Optional[float]:
        """
        安全转换为float

        Args:
            value: 任意值

        Returns:
            float或None
        """
        try:
            return float(value) if pd.notna(value) else None
        except (ValueError, TypeError):
            return None
