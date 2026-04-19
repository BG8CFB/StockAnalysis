"""
用户自选股数据模型

Collection: user_favorites
Indexes: user_id, user_id + stock_code (unique)
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class FavoriteStock(BaseModel):
    """自选股文档模型"""
    user_id: str = Field(..., description="用户ID")
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    market: str = Field(default="A_STOCK", description="市场: A_STOCK, US_STOCK, HK_STOCK")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    notes: str = Field(default="", description="备注")
    alert_price_high: Optional[float] = Field(default=None, description="高价预警")
    alert_price_low: Optional[float] = Field(default=None, description="低价预警")
    current_price: Optional[float] = Field(default=None, description="当前价格")
    change_percent: Optional[float] = Field(default=None, description="涨跌幅")
    volume: Optional[float] = Field(default=None, description="成交量")
    added_at: datetime = Field(default_factory=datetime.now, description="添加时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class AddFavoriteRequest(BaseModel):
    """添加自选股请求"""
    stock_code: str
    stock_name: str
    market: str = "A_STOCK"
    tags: List[str] = Field(default_factory=list)
    notes: str = ""
    alert_price_high: Optional[float] = None
    alert_price_low: Optional[float] = None


class UpdateFavoriteRequest(BaseModel):
    """更新自选股请求"""
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    alert_price_high: Optional[float] = None
    alert_price_low: Optional[float] = None
