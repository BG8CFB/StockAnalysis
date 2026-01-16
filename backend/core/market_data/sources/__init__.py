"""数据源层初始化"""

from core.market_data.sources.base import DataSourceAdapter
from core.market_data.sources.a_stock import TuShareAdapter, AkShareAdapter
from core.market_data.sources.us_stock import YahooFinanceAdapter, AlphaVantageAdapter
from core.market_data.sources.hk_stock import YahooHKAdapter, AkShareHKAdapter

__all__ = [
    "DataSourceAdapter",
    "TuShareAdapter",
    "AkShareAdapter",
    "YahooFinanceAdapter",
    "AlphaVantageAdapter",
    "YahooHKAdapter",
    "AkShareHKAdapter",
]
