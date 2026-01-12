"""
港股数据源适配器

支持 Yahoo Finance、AkShare 等数据源。
"""

from core.market_data.sources.hk_stock.yahoo_adapter import YahooHKAdapter
from core.market_data.sources.hk_stock.akshare_adapter import AkShareHKAdapter

# 为了保持命名一致性，创建别名
YahooFinanceAdapter = YahooHKAdapter
AkShareAdapter = AkShareHKAdapter

__all__ = [
    "YahooFinanceAdapter",
    "AkShareAdapter",
    "YahooHKAdapter",
    "AkShareHKAdapter",
]
