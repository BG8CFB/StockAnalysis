"""
字段映射和ETL转换器

实现Tushare和AkShare到统一存储的字段映射和数据转换
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd

from ..models import MarketType, Exchange

logger = logging.getLogger(__name__)


class FieldMapper:
    """字段映射器基类"""

    @staticmethod
    def normalize_symbol(code: str, exchange: str = None) -> str:
        """
        标准化股票代码为 {code}.{exchange} 格式

        Args:
            code: 股票代码
            exchange: 交易所代码，如果为None则根据代码推断

        Returns:
            标准化代码，如 600519.SH
        """
        if '.' in code:
            return code

        if exchange is None:
            exchange = FieldMapper.infer_exchange(code)

        return f"{code}.{exchange}"

    @staticmethod
    def infer_exchange(code: str) -> str:
        """
        根据股票代码推断交易所

        Args:
            code: 股票代码

        Returns:
            交易所代码 (SSE/SZSE)
        """
        code = code.replace('.SH', '').replace('.SZ', '').replace('.SSE', '').replace('.SZSE', '')
        code = code.split('.')[0] if '.' in code else code

        if code.startswith(('60', '688', '689', '900')):
            return 'SSE'
        elif code.startswith(('00', '30', '301', '002', '003')):
            return 'SZSE'
        else:
            return 'SSE'

    @staticmethod
    def normalize_date(date_str: str) -> str:
        """
        标准化日期为 YYYYMMDD 格式

        Args:
            date_str: 日期字符串，支持多种格式

        Returns:
            YYYYMMDD格式日期
        """
        if not date_str:
            return ""

        date_str = str(date_str).strip()

        if len(date_str) == 8 and date_str.isdigit():
            return date_str

        if len(date_str) == 10:
            if date_str[4] == '-' and date_str[7] == '-':
                return date_str.replace('-', '')
            if date_str[4] == '/' and date_str[7] == '/':
                return date_str.replace('/', '')

        if len(date_str) == 16:
            return date_str[:10].replace('-', '')

        try:
            dt = pd.to_datetime(date_str)
            return dt.strftime('%Y%m%d')
        except:
            logger.warning(f"Failed to normalize date: {date_str}")
            return ""

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> Optional[float]:
        """
        安全转换为浮点数

        Args:
            value: 任意值
            default: 默认值（当value为None或无效时返回None）

        Returns:
            float或None
        """
        if value is None or value == '' or value == '-':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def safe_int(value: Any, default: int = 0) -> Optional[int]:
        """
        安全转换为整数

        Args:
            value: 任意值
            default: 默认值

        Returns:
            int或None
        """
        if value is None or value == '' or value == '-':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def convert_amount(value: Optional[float], from_unit: str = "yuan", to_unit: str = "yuan") -> Optional[float]:
        """
        金额单位转换

        Args:
            value: 金额值
            from_unit: 原单位 (yuan/wanyuan/yiyuan)
            to_unit: 目标单位

        Returns:
            转换后的金额
        """
        if value is None:
            return None

        unit_map = {
            "yuan": 1,
            "wanyuan": 10000,
            "yiyuan": 100000000,
        }

        if from_unit not in unit_map or to_unit not in unit_map:
            logger.warning(f"Unsupported unit: {from_unit} -> {to_unit}")
            return value

        factor = unit_map[from_unit] / unit_map[to_unit]
        return value * factor


class TuShareFieldMapper(FieldMapper):
    """TuShare字段映射器"""

    @staticmethod
    def map_stock_info(row: pd.Series) -> Dict[str, Any]:
        """
        映射TuShare股票基本信息

        Args:
            row: DataFrame行

        Returns:
            统一格式股票信息字典
        """
        ts_code = row.get('ts_code', '')
        symbol = ts_code

        exchange_map = {
            'SSE': 'SSE',
            'SZSE': 'SZSE',
        }

        return {
            "symbol": symbol,
            "market": "A_STOCK",
            "name": row.get('name', ''),
            "industry": row.get('industry'),
            "sector": row.get('area'),
            "listing_date": FieldMapper.normalize_date(row.get('list_date', '')),
            "exchange": exchange_map.get(row.get('exchange', ''), 'SSE'),
            "status": row.get('list_status', 'L'),
            "data_source": "tushare",
        }

    @staticmethod
    def map_stock_quote(row: pd.Series, symbol: str = None) -> Dict[str, Any]:
        """
        映射TuShare行情数据

        Args:
            row: DataFrame行
            symbol: 股票代码

        Returns:
            统一格式行情数据字典
        """
        trade_date = FieldMapper.normalize_date(row.get('trade_date') or row.get('cal_date', ''))

        return {
            "symbol": symbol or row.get('ts_code', ''),
            "market": "A_STOCK",
            "trade_date": trade_date,
            "open": FieldMapper.safe_float(row.get('open')),
            "high": FieldMapper.safe_float(row.get('high')),
            "low": FieldMapper.safe_float(row.get('low')),
            "close": FieldMapper.safe_float(row.get('close')),
            "pre_close": FieldMapper.safe_float(row.get('pre_close')),
            "volume": FieldMapper.safe_int(row.get('vol')),
            "amount": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('amount')), "yuan", "wanyuan"),
            "change": FieldMapper.safe_float(row.get('change')),
            "change_pct": FieldMapper.safe_float(row.get('pct_chg')),
            "turnover_rate": FieldMapper.safe_float(row.get('turnover_rate')),
            "data_source": "tushare",
        }

    @staticmethod
    def map_financial_income(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射TuShare利润表数据

        Args:
            row: DataFrame行
            symbol: 股票代码

        Returns:
            统一格式财务数据字典
        """
        income_statement = {
            "total_revenue": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('total_revenue')), "yuan", "wanyuan"),
            "revenue": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('revenue')), "yuan", "wanyuan"),
            "operating_cost": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('oper_cost')), "yuan", "wanyuan"),
            "net_income": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('n_income')), "yuan", "wanyuan"),
            "basic_eps": FieldMapper.safe_float(row.get('basic_eps')),
            "operating_profit": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('oper_profit')), "yuan", "wanyuan"),
            "total_profit": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('total_profit')), "yuan", "wanyuan"),
        }

        return {
            "symbol": symbol,
            "market": "A_STOCK",
            "report_date": FieldMapper.normalize_date(row.get('end_date', '')),
            "report_type": row.get('report_type', 'annual'),
            "publish_date": FieldMapper.normalize_date(row.get('ann_date', '')),
            "income_statement": income_statement,
            "balance_sheet": {},
            "cash_flow": {},
            "data_source": "tushare",
        }

    @staticmethod
    def map_financial_balance(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射TuShare资产负债表数据

        Args:
            row: DataFrame行
            symbol: 股票代码

        Returns:
            统一格式资产负债表字典
        """
        balance_sheet = {
            "total_assets": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('total_assets')), "yuan", "wanyuan"),
            "total_liabilities": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('total_liab')), "yuan", "wanyuan"),
            "total_equity": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('total_hldr_eqy_exc_min_int')), "yuan", "wanyuan"),
            "current_assets": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('total_cur_assets')), "yuan", "wanyuan"),
            "current_liabilities": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('total_cur_liab')), "yuan", "wanyuan"),
        }

        return {
            "symbol": symbol,
            "market": "A_STOCK",
            "report_date": FieldMapper.normalize_date(row.get('end_date', '')),
            "report_type": row.get('report_type', 'annual'),
            "publish_date": FieldMapper.normalize_date(row.get('ann_date', '')),
            "income_statement": {},
            "balance_sheet": balance_sheet,
            "cash_flow": {},
            "data_source": "tushare",
        }

    @staticmethod
    def map_financial_cashflow(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射TuShare现金流量表数据

        Args:
            row: DataFrame行
            symbol: 股票代码

        Returns:
            统一格式现金流量表字典
        """
        cash_flow = {
            "operating_cash_flow": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('n_cashflow_act')), "yuan", "wanyuan"),
            "investing_cash_flow": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('n_cashflow_inv_act')), "yuan", "wanyuan"),
            "financing_cash_flow": FieldMapper.convert_amount(FieldMapper.safe_float(row.get('n_cash_flows_fnc_act')), "yuan", "wanyuan"),
        }

        return {
            "symbol": symbol,
            "market": "A_STOCK",
            "report_date": FieldMapper.normalize_date(row.get('end_date', '')),
            "report_type": row.get('report_type', 'annual'),
            "publish_date": FieldMapper.normalize_date(row.get('ann_date', '')),
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": cash_flow,
            "data_source": "tushare",
        }

    @staticmethod
    def map_financial_indicator(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射TuShare财务指标

        Args:
            row: DataFrame行
            symbol: 股票代码

        Returns:
            统一格式财务指标字典
        """
        return {
            "symbol": symbol,
            "market": "A_STOCK",
            "report_date": FieldMapper.normalize_date(row.get('end_date', '')),
            "publish_date": FieldMapper.normalize_date(row.get('ann_date', '')),
            "roe": FieldMapper.safe_float(row.get('roe')),
            "roa": FieldMapper.safe_float(row.get('roa')),
            "debt_to_assets": FieldMapper.safe_float(row.get('debt_to_assets')),
            "current_ratio": FieldMapper.safe_float(row.get('current_ratio')),
            "quick_ratio": FieldMapper.safe_float(row.get('quick_ratio')),
            "eps": FieldMapper.safe_float(row.get('basic_eps')),
            "bps": FieldMapper.safe_float(row.get('bps')),
            "gross_profit_margin": FieldMapper.safe_float(row.get('grossprofit_margin')),
            "net_profit_margin": FieldMapper.safe_float(row.get('netprofit_margin')),
            "data_source": "tushare",
        }


class AkShareFieldMapper(FieldMapper):
    """AkShare字段映射器"""

    @staticmethod
    def map_stock_quote(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射AkShare行情数据

        Args:
            row: DataFrame行（字段名为中文）
            symbol: 股票代码

        Returns:
            统一格式行情数据字典
        """
        trade_date = str(row.get('日期', row.get('trade_date', '')))
        trade_date = FieldMapper.normalize_date(trade_date)
        return {
            "symbol": symbol,
            "market": "A_STOCK",
            "trade_date": trade_date,
            "open": FieldMapper.safe_float(row.get('开盘', row.get('open'))),
            "high": FieldMapper.safe_float(row.get('最高', row.get('high'))),
            "low": FieldMapper.safe_float(row.get('最低', row.get('low'))),
            "close": FieldMapper.safe_float(row.get('收盘', row.get('close'))),
            "pre_close": FieldMapper.safe_float(row.get('昨收', row.get('pre_close'))),
            "volume": FieldMapper.safe_int(row.get('成交量', row.get('volume'))),
            "amount": FieldMapper.safe_float(row.get('成交额') or row.get('amount')),
            "change": FieldMapper.safe_float(row.get('涨跌额') or row.get('change')),
            "change_pct": FieldMapper.safe_float(row.get('涨跌幅') or row.get('change_pct')),
            "turnover_rate": FieldMapper.safe_float(row.get('换手率') or row.get('turnover_rate')),
            "data_source": "akshare",
        }

    @staticmethod
    def map_financial_income(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射AkShare利润表数据

        Args:
            row: DataFrame行（字段名为中文）
            symbol: 股票代码

        Returns:
            统一格式财务数据字典
        """
        income_statement = {
            "total_revenue": None,
            "revenue": FieldMapper.safe_float(row.get('营业收入') or row.get('revenue')),
            "operating_cost": FieldMapper.safe_float(row.get('营业成本') or row.get('operating_cost')),
            "net_income": FieldMapper.safe_float(row.get('净利润') or row.get('net_income')),
            "basic_eps": None,
            "operating_profit": FieldMapper.safe_float(row.get('营业利润') or row.get('operating_profit')),
        }

        return {
            "symbol": symbol,
            "market": "A_STOCK",
            "report_date": FieldMapper.normalize_date(row.get('报告期') or row.get('report_date', '')),
            "report_type": 'annual',
            "publish_date": None,
            "income_statement": income_statement,
            "balance_sheet": {},
            "cash_flow": {},
            "data_source": "akshare",
        }

    @staticmethod
    def map_stock_spot(row: pd.Series) -> Dict[str, Any]:
        """
        映射AkShare实时行情数据

        Args:
            row: DataFrame行

        Returns:
            统一格式股票信息字典
        """
        code = str(row.get('代码', ''))
        symbol = FieldMapper.normalize_symbol(code)

        listing_date = row.get('上市日期', '')
        if listing_date:
            listing_date = FieldMapper.normalize_date(str(listing_date))
        else:
            listing_date = ""

        exchange_str = FieldMapper.infer_exchange(code)
        exchange = Exchange.SSE if exchange_str == 'SSE' else Exchange.SZSE

        return {
            "symbol": symbol,
            "market": MarketType.A_STOCK,
            "name": row.get('名称', ''),
            "industry": None,
            "sector": None,
            "listing_date": listing_date,
            "exchange": exchange,
            "status": "L",
            "data_source": "akshare",
        }
