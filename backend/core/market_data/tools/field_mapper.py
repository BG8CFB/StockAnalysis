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


class TuShareFieldMapper(FieldMapper):
    """Tushare 字段映射器"""

    @staticmethod
    def map_stock_quote(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射 Tushare 行情数据

        Args:
            row: DataFrame 行
            symbol: 股票代码

        Returns:
            统一格式行情数据字典
        """
        # Tushare 返回的是手，需要转换为股 (*100)
        vol = FieldMapper.safe_float(row.get('vol'))
        volume = int(vol * 100) if vol is not None else 0
        
        # Tushare 返回的是千元，需要转换为元 (*1000)
        amt = FieldMapper.safe_float(row.get('amount'))
        amount = amt * 1000 if amt is not None else None

        return {
            "symbol": symbol,
            "market": MarketType.A_STOCK,
            "trade_date": FieldMapper.normalize_date(str(row.get('trade_date'))),
            "open": FieldMapper.safe_float(row.get('open')),
            "high": FieldMapper.safe_float(row.get('high')),
            "low": FieldMapper.safe_float(row.get('low')),
            "close": FieldMapper.safe_float(row.get('close')),
            "pre_close": FieldMapper.safe_float(row.get('pre_close')),
            "change_pct": FieldMapper.safe_float(row.get('pct_chg')),
            "volume": volume,
            "amount": amount,
            "turnover_rate": None, # Tushare pro_bar 不一定返回换手率，或者字段名不同
            "data_source": "tushare",
        }

    @staticmethod
    def map_stock_info(row: pd.Series) -> Dict[str, Any]:
        """映射股票基本信息"""
        ts_code = str(row.get('ts_code'))
        return {
            "symbol": ts_code,
            "code": str(row.get('symbol')),
            "market": MarketType.A_STOCK,
            "name": str(row.get('name')),
            "area": str(row.get('area')),
            "industry": str(row.get('industry')),
            "list_date": FieldMapper.normalize_date(str(row.get('list_date'))),
            "exchange": row.get('exchange') or FieldMapper.infer_exchange(ts_code),
            "status": "L", # 默认为上市
            "data_source": "tushare"
        }
        
    @staticmethod
    def map_financial_income(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """映射利润表"""
        # 这里需要根据 StockFinancial 模型调整
        # 暂时只做基本映射，后续可能需要完善
        return {
            "symbol": symbol,
            "market": MarketType.A_STOCK,
            "report_date": FieldMapper.normalize_date(str(row.get('end_date'))),
            "report_type": "annual", # 需根据 comp_type 判断
            "data_source": "tushare",
            # ... 其他字段需要根据 FinancialIncome 模型填充
        }
        
    @staticmethod
    def map_financial_balance(row: pd.Series, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "market": MarketType.A_STOCK,
            "report_date": FieldMapper.normalize_date(str(row.get('end_date'))),
            "data_source": "tushare",
        }
        
    @staticmethod
    def map_financial_indicator(row: pd.Series, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "report_date": FieldMapper.normalize_date(str(row.get('end_date'))),
            "eps": FieldMapper.safe_float(row.get('eps')),
            "dt_eps": FieldMapper.safe_float(row.get('dt_eps')),
            "bps": FieldMapper.safe_float(row.get('bps')),
            "roe": FieldMapper.safe_float(row.get('roe')),
            "data_source": "tushare"
        }


class AkShareFieldMapper(FieldMapper):
    """AkShare 字段映射器"""

    @staticmethod
    def map_stock_quote(row: pd.Series, symbol: str) -> Dict[str, Any]:
        """
        映射 AkShare A股行情数据
        """
        # AkShare 返回的是日期字符串 YYYY-MM-DD
        trade_date = str(row.get('日期'))
        
        return {
            "symbol": symbol,
            "market": MarketType.A_STOCK,
            "trade_date": FieldMapper.normalize_date(trade_date),
            "open": FieldMapper.safe_float(row.get('开盘')),
            "high": FieldMapper.safe_float(row.get('最高')),
            "low": FieldMapper.safe_float(row.get('最低')),
            "close": FieldMapper.safe_float(row.get('收盘')),
            "volume": FieldMapper.safe_int(row.get('成交量')), # AkShare 单位通常是股
            "amount": FieldMapper.safe_float(row.get('成交额')), # 元
            "change_pct": FieldMapper.safe_float(row.get('涨跌幅')),
            "turnover_rate": FieldMapper.safe_float(row.get('换手率')),
            "pre_close": None, # AkShare hist 接口通常不返回昨收
            "data_source": "akshare",
        }

    @staticmethod
    def map_stock_spot(row: pd.Series) -> Dict[str, Any]:
        """映射实时行情/列表"""
        code = str(row.get('代码'))
        symbol = FieldMapper.normalize_symbol(code)
        
        return {
            "symbol": symbol,
            "code": code,
            "market": MarketType.A_STOCK,
            "name": str(row.get('名称')),
            "data_source": "akshare",
            # ...
        }

