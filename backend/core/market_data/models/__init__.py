"""
市场数据模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class MarketType(str, Enum):
    """市场类型枚举"""
    A_STOCK = "A_STOCK"
    US_STOCK = "US_STOCK"
    HK_STOCK = "HK_STOCK"


class Exchange(str, Enum):
    """交易所枚举"""
    SSE = "SSE"  # 上交所
    SZSE = "SZSE"  # 深交所
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"


# 从子模块导入股票数据模型
from core.market_data.models.stock_info import StockInfo
from core.market_data.models.stock_quote import StockQuote, StockKLine
from core.market_data.models.stock_financials import StockFinancial, StockFinancialIndicator
from core.market_data.models.stock_company import StockCompany
from core.market_data.models.stock_macro import MacroEconomic
from core.market_data.models.stock_other import (
    StockSector,
    StockTopList,
    StockDividend,
    StockMargin,
    StockNews,
)

# 从子模块导入其他模型
from core.market_data.models.datasource import (
    DataSourceStatus,
    DataSourceType,
    SystemDataSourceConfig,
    UserDataSourceConfig,
    DataSourceHealthStatus,
    DataSourceStatusHistory,
)
from core.market_data.models.watchlist import (
    WatchlistStock,
    UserWatchlist,
)
from core.market_data.models.sync_task import (
    DataSyncTask,
)

__all__ = [
    # Market
    "MarketType",
    "Exchange",
    "StockInfo",
    "StockQuote",
    "StockKLine",
    "StockFinancial",
    "StockFinancialIndicator",
    "StockCompany",
    "MacroEconomic",
    "StockSector",
    "StockTopList",
    "StockDividend",
    "StockMargin",
    "StockNews",
    # DataSource
    "DataSourceStatus",
    "DataSourceType",
    "SystemDataSourceConfig",
    "UserDataSourceConfig",
    "DataSourceHealthStatus",
    "DataSourceStatusHistory",
    # Watchlist
    "WatchlistStock",
    "UserWatchlist",
    # SyncTask
    "DataSyncTask",
]
