"""
数据同步任务模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DataSyncTask(BaseModel):
    """数据同步任务"""

    task_type: str = Field(..., description="任务类型")
    symbol: Optional[str] = Field(None, description="股票代码")
    market: Optional[str] = Field(None, description="市场类型")
    data_types: List[str] = Field(..., description="数据类型列表")
    status: str = Field(..., description="任务状态:pending/running/completed/failed")
    progress: int = Field(default=0, ge=0, le=100, description="进度(0-100)")
    result: Optional[Dict[str, Any]] = Field(None, description="结果统计")

    # 时间
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    # 触发信息
    triggered_by: str = Field(..., description="触发来源:manual/scheduled/api")
    user_id: Optional[str] = Field(None, description="关联用户ID")
    error_message: Optional[str] = Field(None, description="错误信息")
