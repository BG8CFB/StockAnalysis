"""A股数据源"""

from modules.market_data.sources.a_stock.tushare_adapter import TuShareAdapter
from modules.market_data.sources.a_stock.akshare_adapter import AkShareAdapter

__all__ = ['TuShareAdapter', 'AkShareAdapter']
