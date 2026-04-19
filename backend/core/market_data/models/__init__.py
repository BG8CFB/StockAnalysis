"""
市场数据模型

注意：MarketType 和 Exchange 必须在子模块导入之前定义，
因为 stock_info.py 等子模块会从本模块导入这些枚举。
"""

# ruff: noqa: I001, E402

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


# 从子模块导入其他模型
from core.market_data.models.api_monitor import ApiMonitor
from core.market_data.models.datasource import (
    DataSourceHealthStatus,
    DataSourceStatus,
    DataSourceStatusHistory,
    DataSourceType,
    SystemDataSourceConfig,
    UserDataSourceConfig,
)
from core.market_data.models.stock_company import StockCompany
from core.market_data.models.stock_financials import (
    FinancialBalance,
    FinancialCashFlow,
    FinancialIncome,
    StockFinancial,
    StockFinancialIndicator,
)
from core.market_data.models.stock_info import StockInfo, TradeCalendar
from core.market_data.models.stock_macro import MacroEconomic, MacroEconomy
from core.market_data.models.stock_other import (
    MarketNews,
    StockDividend,
    StockHSGTMoneyFlow,
    StockMargin,
    StockMoneyFlow,
    StockTopList,
)
from core.market_data.models.stock_quote import (
    MarketBoardDaily,
    StockDailyIndicator,
    StockKLine,
    StockMinuteQuote,
    StockQuote,
)
from core.market_data.models.sync_task import DataSyncTask
from core.market_data.models.watchlist import UserWatchlist, WatchlistStock

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
