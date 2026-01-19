"""
接口监控模型
用于监控各个数据接口的可用性，实现自动故障切换 (Failover)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ApiMonitor(BaseModel):
    """接口监控数据模型"""
    data_type: str = Field(..., description="数据类型 (主键)，如: minute_data, daily_data")
    primary_source: str = Field(..., description="主数据源，如: TU")
    backup_source: str = Field(..., description="备用数据源，如: AK")
    current_status: str = Field(default="healthy", description="当前状态: healthy, failed")
    last_check_time: datetime = Field(default_factory=datetime.now, description="最后检查时间")
    fail_count: int = Field(default=0, description="连续失败次数")
    is_using_backup: bool = Field(default=False, description="是否正在使用备用源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_schema_extra = {
            "example": {
                "data_type": "minute_data",
                "primary_source": "TU",
                "backup_source": "AK",
                "current_status": "healthy",
                "fail_count": 0,
                "is_using_backup": False
            }
        }
