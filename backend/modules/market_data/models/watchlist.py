"""
用户自选股模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class WatchlistStock(BaseModel):
    """自选股信息"""
    symbol: str = Field(..., description="股票代码")
    market: str = Field(..., description="市场类型")
    added_at: datetime = Field(default_factory=datetime.now, description="添加时间")
    notes: Optional[str] = Field(None, description="用户备注")
    sync_status: str = Field(default="pending", description="同步状态:pending/syncing/completed/failed")
    last_sync_at: Optional[datetime] = Field(None, description="最后同步时间")
    config: Optional[Dict[str, Any]] = Field(None, description="同步配置")
    sync_result: Optional[Dict[str, Any]] = Field(None, description="同步结果统计")


class UserWatchlist(BaseModel):
    """用户自选股列表"""
    user_id: str = Field(..., description="用户ID")
    stocks: List[WatchlistStock] = Field(default_factory=list, description="自选股列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
