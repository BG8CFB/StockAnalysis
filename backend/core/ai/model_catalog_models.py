"""
模型目录 Pydantic 模型

对应前端 config.types.ts 中的 ModelCatalog / ModelInfo 类型。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelCatalogItem(BaseModel):
    """模型信息"""

    name: str = Field(..., description="模型名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = None
    context_length: Optional[int] = None
    max_tokens: Optional[int] = None
    input_price_per_1k: Optional[float] = None
    output_price_per_1k: Optional[float] = None
    currency: Optional[str] = None
    is_deprecated: Optional[bool] = None
    release_date: Optional[str] = None
    capabilities: Optional[List[str]] = None


class ModelCatalogCreateRequest(BaseModel):
    """模型目录保存请求"""

    provider: str = Field(..., description="厂家标识")
    provider_name: str = Field(..., description="厂家显示名称")
    models: List[ModelCatalogItem] = Field(default_factory=list)


class ModelCatalogResponse(BaseModel):
    """模型目录响应"""

    provider: str
    provider_name: str
    models: List[ModelCatalogItem] = Field(default_factory=list)


class AvailableModelItem(BaseModel):
    """可用模型项"""

    name: str
    display_name: str


class AvailableModelsByProvider(BaseModel):
    """按厂家分组的可用模型"""

    provider: str
    provider_name: str
    models: List[AvailableModelItem] = Field(default_factory=list)
