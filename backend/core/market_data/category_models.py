"""
市场分类 Pydantic 模型

对应前端 config.types.ts 中的 MarketCategory / DataSourceGrouping 类型。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class MarketCategoryCreateRequest(BaseModel):
    """市场分类创建请求"""
    id: str = Field(..., min_length=1, description="分类 ID")
    name: str = Field(..., min_length=1, description="分类名称")
    display_name: str = Field(..., min_length=1, description="显示名称")
    description: Optional[str] = None
    enabled: bool = True
    sort_order: Optional[int] = None


class MarketCategoryResponse(BaseModel):
    """市场分类响应"""
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    enabled: bool = True
    sort_order: Optional[int] = None


class DataSourceGroupingCreateRequest(BaseModel):
    """数据源分组创建请求"""
    data_source_name: str = Field(..., description="数据源名称")
    market_category_id: str = Field(..., description="市场分类 ID")
    priority: int = Field(default=1, description="优先级")
    enabled: bool = Field(default=True, description="是否启用")


class DataSourceGroupingUpdateRequest(BaseModel):
    """数据源分组更新请求"""
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class DataSourceGroupingResponse(BaseModel):
    """数据源分组响应"""
    data_source_name: str
    market_category_id: str
    priority: int = 1
    enabled: bool = True


class DataSourceOrderItem(BaseModel):
    """数据源排序项"""
    name: str
    priority: int


class DataSourceOrderRequest(BaseModel):
    """数据源排序请求"""
    data_sources: List[DataSourceOrderItem]
