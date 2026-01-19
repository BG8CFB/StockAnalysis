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
    HKEX = "HKEX"  # 港交所
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"


# 从子模块导入股票数据模型
from core.market_data.models.stock_info import StockInfo, TradeCalendar
from core.market_data.models.stock_quote import (
    StockQuote,
    StockMinuteQuote,
    StockKLine,
    StockDailyIndicator,
    MarketBoardDaily
)
from core.market_data.models.stock_financials import (
    StockFinancial,
    FinancialIncome,
    FinancialBalance,
    FinancialCashFlow,
    StockFinancialIndicator
)
from core.market_data.models.stock_company import StockCompany
from core.market_data.models.stock_macro import MacroEconomy, MacroEconomic
from core.market_data.models.stock_other import (
    StockMoneyFlow,
    StockHSGTMoneyFlow,
    StockTopList,
    StockDividend,
    StockMargin,
    MarketNews,
)
from core.market_data.models.api_monitor import ApiMonitor

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
    "TradeCalendar",
    "StockQuote",
    "StockMinuteQuote",
    "StockKLine",
    "StockDailyIndicator",
    "MarketBoardDaily",
    "StockFinancial",
    "FinancialIncome",
    "FinancialBalance",
    "FinancialCashFlow",
    "StockFinancialIndicator",
    "StockCompany",
    "MacroEconomy",
    "MacroEconomic",
    "StockMoneyFlow",
    "StockHSGTMoneyFlow",
    "StockTopList",
    "StockDividend",
    "StockMargin",
    "MarketNews",
    "ApiMonitor",
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
