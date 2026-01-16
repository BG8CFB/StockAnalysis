"""
数据源配置和状态监控模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class DataSourceStatus(str, Enum):
    """数据源状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class DataSourceType(str, Enum):
    """数据源类型"""
    SYSTEM = "system"  # 系统公共数据源
    USER = "user"      # 用户个人数据源


class SystemDataSourceConfig(BaseModel):
    """系统公共数据源配置"""
    source_id: str = Field(..., description="数据源标识(tushare/akshare等)")
    market: str = Field(..., description="市场类型:A_STOCK/US_STOCK/HK_STOCK")
    enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(..., description="优先级(数字越小优先级越高)")
    is_system_public: bool = Field(default=True, description="标识为系统公共配置")

    # 配置信息(加密存储)
    config: Dict[str, Any] = Field(..., description="数据源配置(包含api_key等)")

    # 限流配置
    rate_limit: Optional[Dict[str, int]] = Field(None, description="限流配置")

    # 支持的数据类型
    supported_data_types: List[str] = Field(default_factory=list, description="支持的数据类型")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    last_tested_at: Optional[datetime] = Field(None, description="最后测试时间")
    test_status: Optional[str] = Field(None, description="测试状态:success/failed")
    last_error: Optional[str] = Field(None, description="最后错误信息")


class UserDataSourceConfig(BaseModel):
    """用户个人数据源配置"""
    user_id: str = Field(..., description="用户ID")
    source_id: str = Field(..., description="数据源标识")
    market: str = Field(..., description="市场类型")
    enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(..., description="优先级")

    # 配置信息(加密存储)
    config: Dict[str, Any] = Field(..., description="数据源配置(包含api_key等)")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    last_tested_at: Optional[datetime] = Field(None, description="最后测试时间")
    test_status: Optional[str] = Field(None, description="测试状态")
    last_error: Optional[str] = Field(None, description="最后错误信息")


class DataSourceHealthStatus(BaseModel):
    """数据源健康状态"""
    market: str = Field(..., description="市场类型")
    data_type: str = Field(..., description="数据类型:daily_quote/financials等")
    source_type: DataSourceType = Field(..., description="数据源类型")
    source_id: str = Field(..., description="数据源标识")
    user_id: Optional[str] = Field(None, description="用户ID(source_type=user时必填)")

    # 当前状态
    status: DataSourceStatus = Field(..., description="状态")
    last_check_at: datetime = Field(default_factory=datetime.now, description="最后检查时间")
    last_check_type: str = Field(..., description="检查类型:sync_task/manual_retry/tool_call")
    response_time_ms: Optional[int] = Field(None, description="响应时间(毫秒)")
    avg_response_time_ms: Optional[int] = Field(None, description="平均响应时间(24小时)")

    # 失败信息
    failure_count: int = Field(default=0, description="连续失败次数")
    max_failure_count: int = Field(default=3, description="最大失败次数阈值")
    last_error: Optional[Dict[str, Any]] = Field(None, description="最后错误信息")

    # 降级信息
    is_fallback: bool = Field(default=False, description="是否为降级状态")
    fallback_info: Optional[Dict[str, Any]] = Field(None, description="降级详情")

    # 接口明细
    api_endpoints: Optional[List[Dict[str, Any]]] = Field(None, description="接口明细列表")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class DataSourceStatusHistory(BaseModel):
    """数据源状态变更历史"""
    market: str = Field(..., description="市场类型")
    data_type: str = Field(..., description="数据类型")
    source_type: DataSourceType = Field(..., description="数据源类型")
    source_id: str = Field(..., description="数据源标识")
    user_id: Optional[str] = Field(None, description="用户ID")

    # 事件信息
    event_type: str = Field(..., description="事件类型:status_changed/fallback/recovered/api_failed")
    from_status: Optional[str] = Field(None, description="变化前状态")
    to_status: Optional[str] = Field(None, description="变化后状态")
    error_code: Optional[str] = Field(None, description="错误码")
    error_message: Optional[str] = Field(None, description="错误信息")
    response_time_ms: Optional[int] = Field(None, description="响应时间")
    check_type: Optional[str] = Field(None, description="检查类型")

    # 接口级别事件
    api_endpoint: Optional[str] = Field(None, description="接口名称")
    from_source: Optional[str] = Field(None, description="变化前数据源")
    to_source: Optional[str] = Field(None, description="变化后数据源")

    # 时间
    timestamp: datetime = Field(default_factory=datetime.now, description="事件发生时间")
