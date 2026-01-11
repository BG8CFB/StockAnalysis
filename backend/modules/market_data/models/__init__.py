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


class StockInfo(BaseModel):
    """股票基础信息模型"""
    symbol: str = Field(..., description="股票代码，如600519.SH")
    market: MarketType = Field(..., description="市场类型")
    name: str = Field(..., description="股票名称")
    industry: Optional[str] = Field(None, description="所属行业")
    sector: Optional[str] = Field(None, description="所属板块")
    listing_date: str = Field(..., description="上市日期，格式YYYYMMDD")
    exchange: Exchange = Field(..., description="交易所代码")
    status: str = Field(default="L", description="上市状态：L上市/D退市/P暂停")
    data_source: str = Field(..., description="数据来源：tushare/akshare")

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """验证股票代码格式"""
        if '.' not in v:
            raise ValueError(f"股票代码格式错误，应包含交易所后缀：{v}")
        return v

    @field_validator('listing_date')
    @classmethod
    def validate_listing_date(cls, v: str) -> str:
        """验证日期格式"""
        if v == "" or v is None:
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"日期格式错误，应为YYYYMMDD：{v}")
        return v


class StockQuote(BaseModel):
    """日线行情数据模型（当日）"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    trade_date: str = Field(..., description="交易日期，格式YYYYMMDD")
    open: float = Field(..., ge=0, description="开盘价")
    high: float = Field(..., ge=0, description="最高价")
    low: float = Field(..., ge=0, description="最低价")
    close: float = Field(..., ge=0, description="收盘价")
    pre_close: Optional[float] = Field(None, description="昨收价")
    volume: int = Field(..., ge=0, description="成交量（手）")
    amount: Optional[float] = Field(None, description="成交额（万元）")
    change: Optional[float] = Field(None, description="涨跌额")
    change_pct: Optional[float] = Field(None, description="涨跌幅（%）")
    turnover_rate: Optional[float] = Field(None, description="换手率（%）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")

    @field_validator('trade_date')
    @classmethod
    def validate_trade_date(cls, v: str) -> str:
        """验证日期格式"""
        if v == "" or v is None:
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"日期格式错误，应为YYYYMMDD：{v}")
        return v


class StockKLine(BaseModel):
    """历史K线数据模型（包含技术指标）"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    trade_date: str = Field(..., description="交易日期，格式YYYYMMDD")
    open: float = Field(..., ge=0, description="开盘价")
    high: float = Field(..., ge=0, description="最高价")
    low: float = Field(..., ge=0, description="最低价")
    close: float = Field(..., ge=0, description="收盘价")
    volume: int = Field(..., ge=0, description="成交量（股）")
    amount: Optional[float] = Field(None, description="成交额（万元）")
    pre_close: Optional[float] = Field(None, description="昨收价")
    change: Optional[float] = Field(None, description="涨跌额")
    change_pct: Optional[float] = Field(None, description="涨跌幅（%）")

    # 技术指标
    indicators: Optional[dict] = Field(None, description="技术指标（MA、MACD、RSI等）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockFinancial(BaseModel):
    """财务报表数据模型"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    report_date: str = Field(..., description="报告期，格式YYYYMMDD")
    report_type: str = Field(..., description="报告类型：Q1/Q2/Q3/Q4/annual")
    publish_date: Optional[str] = Field(None, description="发布日期")

    # 利润表
    income_statement: Optional[dict] = Field(None, description="利润表数据")

    # 资产负债表
    balance_sheet: Optional[dict] = Field(None, description="资产负债表数据")

    # 现金流量表
    cash_flow: Optional[dict] = Field(None, description="现金流量表数据")

    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockFinancialIndicator(BaseModel):
    """财务指标数据模型"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    report_date: str = Field(..., description="报告期，格式YYYYMMDD")
    publish_date: Optional[str] = Field(None, description="发布日期")

    # 盈利能力指标
    roe: Optional[float] = Field(None, description="净资产收益率（%）")
    roa: Optional[float] = Field(None, description="总资产净利率（%）")
    gross_profit_margin: Optional[float] = Field(None, description="销售毛利率（%）")
    net_profit_margin: Optional[float] = Field(None, description="销售净利率（%）")

    # 偿债能力指标
    debt_to_assets: Optional[float] = Field(None, description="资产负债率（%）")
    current_ratio: Optional[float] = Field(None, description="流动比率")
    quick_ratio: Optional[float] = Field(None, description="速动比率")

    # 营运能力指标
    eps: Optional[float] = Field(None, description="基本每股收益（元）")
    bps: Optional[float] = Field(None, description="每股净资产（元）")

    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockCompany(BaseModel):
    """公司详细信息模型"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    company_name: str = Field(..., description="公司名称")
    company_name_en: Optional[str] = Field(None, description="英文名称")
    industry: Optional[str] = Field(None, description="所属行业")
    sector: Optional[str] = Field(None, description="所属板块")
    listing_date: str = Field(..., description="上市日期")

    # 联系方式
    contact: Optional[dict] = Field(None, description="联系方式")

    # 业务描述
    business: Optional[dict] = Field(None, description="业务描述")

    # 股本结构
    capital_structure: Optional[dict] = Field(None, description="股本结构")

    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class MacroEconomic(BaseModel):
    """宏观经济数据模型"""
    indicator: str = Field(..., description="指标名称：gdp/cpi/ppi/pmi/shibor等")
    period: str = Field(..., description="统计周期，格式YYYY-Q1或YYYY-MM")
    value: float = Field(..., description="指标数值")
    unit: Optional[str] = Field(None, description="单位")
    yoy: Optional[float] = Field(None, description="同比增长率（%）")
    mom: Optional[float] = Field(None, description="环比增长率（%）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockSector(BaseModel):
    """板块数据模型"""
    sector_name: str = Field(..., description="板块名称")
    sector_code: str = Field(..., description="板块代码")
    sector_type: str = Field(..., description="板块类型：concept/industry")
    stock_count: Optional[int] = Field(None, description="包含股票数量")
    description: Optional[str] = Field(None, description="板块描述")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockTopList(BaseModel):
    """龙虎榜数据模型"""
    symbol: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易日期")
    close_price: Optional[float] = Field(None, description="收盘价")
    change_pct: Optional[float] = Field(None, description="涨跌幅")
    buy_total: Optional[float] = Field(None, description="买入总额（万元）")
    sell_total: Optional[float] = Field(None, description="卖出总额（万元）")
    net_buy: Optional[float] = Field(None, description="净买入额（万元）")
    reason: Optional[str] = Field(None, description="上榜原因")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockDividend(BaseModel):
    """分红数据模型"""
    symbol: str = Field(..., description="股票代码")
    dividend_year: str = Field(..., description="分红年度")
    ex_dividend_date: Optional[str] = Field(None, description="除权除息日")
    record_date: Optional[str] = Field(None, description="股权登记日")
    cash_dividend: Optional[float] = Field(None, description="每股现金分红（元）")
    dividend_ratio: Optional[float] = Field(None, description="分红率（%）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockMargin(BaseModel):
    """融资融券数据模型"""
    symbol: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易日期")
    margin_buy: Optional[float] = Field(None, description="融资买入额（万元）")
    margin_sell: Optional[float] = Field(None, description="融资偿还额（万元）")
    margin_balance: Optional[float] = Field(None, description="融资余额（万元）")
    short_sell: Optional[float] = Field(None, description="融券卖出量（股）")
    short_buy: Optional[float] = Field(None, description="融券买入量（股）")
    short_balance: Optional[float] = Field(None, description="融券余额（万元）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockNews(BaseModel):
    """股票新闻数据模型"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    title: str = Field(..., description="新闻标题")
    url: str = Field(..., description="新闻链接")
    publish_time: str = Field(..., description="发布时间")
    content: str = Field(default="", description="新闻内容")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


# 从子模块导入其他模型
from modules.market_data.models.datasource import (
    DataSourceStatus,
    DataSourceType,
    SystemDataSourceConfig,
    UserDataSourceConfig,
    DataSourceHealthStatus,
    DataSourceStatusHistory,
)
from modules.market_data.models.watchlist import (
    WatchlistStock,
    UserWatchlist,
)
from modules.market_data.models.sync_task import (
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
