"""
API请求和响应模型
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from core.market_data.models import MarketType


# ==================== 请求模型 ====================

class StockListRequest(BaseModel):
    """股票列表请求"""
    market: MarketType = Field(..., description="市场类型")
    status: str = Field(default="L", description="上市状态：L上市/D退市/P暂停")


class QuoteQueryRequest(BaseModel):
    """行情查询请求"""
    symbol: str = Field(..., description="股票代码")
    start_date: Optional[str] = Field(None, description="开始日期（YYYYMMDD）")
    end_date: Optional[str] = Field(None, description="结束日期（YYYYMMDD）")
    limit: int = Field(default=0, description="返回数量限制，0表示不限制")


class FinancialQueryRequest(BaseModel):
    """财务数据查询请求"""
    symbol: str = Field(..., description="股票代码")
    report_type: Optional[str] = Field(None, description="报告类型")
    limit: int = Field(default=0, description="返回数量限制")


class DataSyncRequest(BaseModel):
    """数据同步请求"""
    symbol: Optional[str] = Field(None, description="股票代码，不指定则同步全市场")
    data_types: List[str] = Field(
        default=["stock_info", "quotes"],
        description="数据类型列表：stock_info/quotes/financials/indicators"
    )
    force_refresh: bool = Field(default=False, description="是否强制刷新（忽略缓存）")


# ==================== 响应模型 ====================

class StockInfoResponse(BaseModel):
    """股票信息响应"""
    symbol: str
    market: MarketType
    name: str
    industry: Optional[str] = None
    sector: Optional[str] = None
    listing_date: str
    exchange: str
    status: str
    data_source: str


class QuoteResponse(BaseModel):
    """行情数据响应"""
    symbol: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    data_source: str


class FinancialResponse(BaseModel):
    """财务数据响应"""
    symbol: str
    report_date: str
    report_type: str
    publish_date: Optional[str] = None
    income_statement: Optional[dict] = None
    balance_sheet: Optional[dict] = None
    cash_flow: Optional[dict] = None
    data_source: str


class IndicatorResponse(BaseModel):
    """财务指标响应"""
    symbol: str
    report_date: str
    roe: Optional[float] = None
    debt_to_assets: Optional[float] = None
    current_ratio: Optional[float] = None
    eps: Optional[float] = None
    data_source: str


class DataSourceHealthResponse(BaseModel):
    """数据源健康状态响应"""
    source_name: str
    is_available: bool
    response_time_ms: Optional[int] = None
    last_check_time: Optional[str] = None
    failure_count: int = 0
    error: Optional[str] = None


class CurrentSourceResponse(BaseModel):
    """当前数据源信息"""
    source_type: str
    source_id: str
    source_name: str
    status: str
    last_check: str
    last_check_relative: str


class MarketDataTypeResponse(BaseModel):
    """市场数据类型响应"""
    data_type: str
    data_type_name: str
    current_source: CurrentSourceResponse
    is_fallback: bool
    can_retry: bool
    fallback_reason: Optional[str] = None


class MarketDetailResponse(BaseModel):
    """市场详细状态响应"""
    market: str
    market_name: str
    data_types: List[MarketDataTypeResponse]


class MarketOverviewItem(BaseModel):
    """市场概览单项"""
    status: str
    last_update: str
    last_update_relative: str
    reason: Optional[str] = None


class DashboardOverviewResponse(BaseModel):
    """数据源状态监控仪表板概览响应"""
    a_stock: Optional[MarketOverviewItem] = None
    us_stock: Optional[MarketOverviewItem] = None
    hk_stock: Optional[MarketOverviewItem] = None


class SourceDetailResponse(BaseModel):
    """数据源详细信息"""
    source_type: str
    source_id: str
    source_name: str
    status: str
    priority: int
    last_check: str
    response_time_ms: Optional[int] = None
    avg_response_time_ms: Optional[int] = None
    failure_count: int = 0


class DataSourceEventResponse(BaseModel):
    """数据源事件响应"""
    timestamp: str
    event_type: str
    description: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    from_source: Optional[str] = None
    to_source: Optional[str] = None
    source_id: Optional[str] = None


class DataTypeDetailResponse(BaseModel):
    """数据类型详细信息响应"""
    market: str
    data_type: str
    data_type_name: str
    sources: List[SourceDetailResponse]
    recent_events: List[DataSourceEventResponse]


class DataSyncResponse(BaseModel):
    """数据同步响应"""
    success: bool
    message: str
    synced_count: int = 0
    failed_count: int = 0
    source_used: Optional[str] = None
    duration_ms: Optional[int] = None
