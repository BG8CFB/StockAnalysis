"""
AI 模型配置数据模型

定义 AI 模型配置的 Pydantic 模型，用于请求验证、响应序列化和数据存储。
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class ModelProviderEnum(str, Enum):
    """AI 模型提供商枚举"""
    ZHIPU = "zhipu"             # 智谱AI
    DEEPSEEK = "deepseek"       # DeepSeek
    QWEN = "qwen"               # 通义千问
    OPENAI = "openai"           # OpenAI
    OLLAMA = "ollama"           # Ollama
    CUSTOM = "custom"           # 自定义


class AIModelConfigBase(BaseModel):
    """AI 模型配置基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    provider: ModelProviderEnum = Field(..., description="提供商")
    api_base_url: str = Field(..., min_length=1, description="API 基础 URL")
    api_key: str = Field(..., min_length=1, description="API Key")
    model_id: str = Field(..., min_length=1, max_length=100, description="模型 ID")
    max_concurrency: int = Field(default=40, ge=1, le=200, description="模型最大并发数")
    task_concurrency: int = Field(default=2, ge=1, le=10, description="单任务并发数（单个任务可同时运行的智能体数）")
    batch_concurrency: int = Field(default=1, ge=1, le=50, description="批量任务并发数（用户可同时运行的批量任务数，公共模型由管理员控制）")
    timeout_seconds: int = Field(default=60, ge=10, le=600, description="超时时间（秒）")
    temperature: float = Field(default=0.5, ge=0.0, le=1.0, description="温度参数")
    enabled: bool = Field(default=True, description="是否启用")

    @model_validator(mode='after')
    def validate_concurrency(self):
        """验证并发参数的合理性"""
        if self.task_concurrency > self.max_concurrency:
            raise ValueError(
                f"单任务并发数({self.task_concurrency})不能大于模型最大并发数({self.max_concurrency})"
            )

        if self.batch_concurrency * self.task_concurrency > self.max_concurrency:
            raise ValueError(
                f"批量任务并发数({self.batch_concurrency}) × 单任务并发数({self.task_concurrency}) "
                f"不能超过模型最大并发数({self.max_concurrency})"
            )

        return self


class AIModelConfigCreate(AIModelConfigBase):
    """创建 AI 模型配置请求"""
    is_system: bool = Field(default=False, description="是否为系统级配置")


class AIModelConfigUpdate(BaseModel):
    """更新 AI 模型配置请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[ModelProviderEnum] = None
    api_base_url: Optional[str] = Field(None, min_length=1)
    api_key: Optional[str] = Field(None, min_length=1)
    model_id: Optional[str] = Field(None, min_length=1, max_length=100)
    max_concurrency: Optional[int] = Field(None, ge=1, le=200)
    task_concurrency: Optional[int] = Field(None, ge=1, le=10)
    batch_concurrency: Optional[int] = Field(None, ge=1, le=50)
    timeout_seconds: Optional[int] = Field(None, ge=10, le=600)
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    enabled: Optional[bool] = None

    @model_validator(mode='after')
    def validate_concurrency(self):
        """验证并发参数的合理性（仅当所有相关参数都提供时才验证）"""
        if all([
            self.max_concurrency is not None,
            self.task_concurrency is not None,
        ]):
            if self.task_concurrency > self.max_concurrency:
                raise ValueError(
                    f"单任务并发数({self.task_concurrency})不能大于模型最大并发数({self.max_concurrency})"
                )

        if all([
            self.max_concurrency is not None,
            self.task_concurrency is not None,
            self.batch_concurrency is not None,
        ]):
            if self.batch_concurrency * self.task_concurrency > self.max_concurrency:
                raise ValueError(
                    f"批量任务并发数({self.batch_concurrency}) × 单任务并发数({self.task_concurrency}) "
                    f"不能超过模型最大并发数({self.max_concurrency})"
                )

        return self


class AIModelConfigResponse(AIModelConfigBase):
    """AI 模型配置响应"""
    id: str
    is_system: bool
    owner_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    masked_api_key: str = Field(..., description="脱敏后的 API Key")

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "AIModelConfigResponse":
        """从数据库数据创建响应对象"""
        api_key = data.get("api_key", "")
        masked = cls._mask_api_key(api_key)

        return cls(
            id=str(data["_id"]),
            name=data["name"],
            provider=ModelProviderEnum(data["provider"]),
            api_base_url=data["api_base_url"],
            api_key=api_key,
            model_id=data["model_id"],
            max_concurrency=data.get("max_concurrency", 40),
            task_concurrency=data.get("task_concurrency", 2),
            batch_concurrency=data.get("batch_concurrency", 1),
            timeout_seconds=data["timeout_seconds"],
            temperature=data["temperature"],
            enabled=data["enabled"],
            is_system=data.get("is_system", False),
            owner_id=data.get("owner_id"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            masked_api_key=masked,
        )

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """脱敏 API Key"""
        if len(api_key) <= 8:
            return "****"
        return f"{api_key[:4]}****{api_key[-4:]}"


class AIModelTestRequest(BaseModel):
    """测试 AI 模型连接请求"""
    api_base_url: str
    api_key: str
    model_id: str
    timeout_seconds: int = Field(default=10, ge=5, le=30)


class ConnectionTestResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str
    latency_ms: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
