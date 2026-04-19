"""
LLM 厂家管理 Pydantic 模型

对应前端 config.types.ts 中的 LLM Provider 相关类型。
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SupportedFeature(str, Enum):
    """支持的功能标签"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image_generation"
    VISION = "vision"
    TOOL_CALLING = "tool_calling"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"


class AggregatorType(str, Enum):
    """聚合渠道类型"""
    OPENROUTER = "openrouter"
    AI302 = "302ai"
    SILICONFLOW = "siliconflow"
    CUSTOM = "custom"


class LLMProviderCreateRequest(BaseModel):
    """LLM 厂家创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="厂家标识名")
    display_name: str = Field(..., min_length=1, max_length=200, description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    website: Optional[str] = Field(None, description="官网地址")
    api_doc_url: Optional[str] = Field(None, description="API 文档地址")
    logo_url: Optional[str] = Field(None, description="Logo URL")
    is_active: bool = Field(default=True, description="是否启用")
    supported_features: List[SupportedFeature] = Field(
        default_factory=list, description="支持的功能"
    )
    default_base_url: Optional[str] = Field(None, description="默认 API Base URL")
    api_key: Optional[str] = Field(None, description="API Key")
    api_secret: Optional[str] = Field(None, description="API Secret")
    is_aggregator: bool = Field(default=False, description="是否为聚合渠道")
    aggregator_type: Optional[AggregatorType] = Field(None, description="聚合渠道类型")
    model_name_format: Optional[str] = Field(None, description="模型名称格式")


class LLMProviderUpdateRequest(BaseModel):
    """LLM 厂家更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    website: Optional[str] = None
    api_doc_url: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None
    supported_features: Optional[List[SupportedFeature]] = None
    default_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    is_aggregator: Optional[bool] = None
    aggregator_type: Optional[AggregatorType] = None
    model_name_format: Optional[str] = None


class LLMProviderResponse(BaseModel):
    """LLM 厂家响应（API Key 脱敏）"""
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    website: Optional[str] = None
    api_doc_url: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool
    supported_features: List[SupportedFeature] = Field(default_factory=list)
    default_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    extra_config: Dict[str, bool] = Field(default_factory=dict)
    is_aggregator: bool = False
    aggregator_type: Optional[AggregatorType] = None
    model_name_format: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LLMProviderToggleRequest(BaseModel):
    """启用/禁用厂家请求"""
    is_active: bool


class MigrateEnvResult(BaseModel):
    """环境变量迁移结果"""
    success: bool
    message: str
    migrated_count: int = 0
    skipped_count: int = 0


class InitAggregatorsResult(BaseModel):
    """初始化聚合器结果"""
    success: bool
    message: str
    added_count: int = 0
    skipped_count: int = 0
