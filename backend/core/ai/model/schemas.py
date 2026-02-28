"""
AI 模型配置数据模型

定义 AI 模型配置的 Pydantic 模型，用于请求验证、响应序列化和数据存储。
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

# =============================================================================
# 通用辅助函数
# =============================================================================

def _parse_datetime(value: Any) -> Optional[datetime]:
    """
    解析 datetime，兼容多种格式

    支持格式：
    - Python datetime 对象（直接返回）
    - MongoDB 扩展 JSON 格式: {'$date': '2026-01-13T06:59:30.154Z'}
    - ISO 8601 字符串

    Args:
        value: 输入值

    Returns:
        datetime 对象，解析失败返回 None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, dict) and "$date" in value:
        try:

            from dateutil import parser
            return parser.isoparse(value["$date"])
        except Exception:
            return None
    if isinstance(value, str):
        try:
            from dateutil import parser
            return parser.isoparse(value)
        except Exception:
            return None
    return None


class PlatformTypeEnum(str, Enum):
    """平台类型枚举"""

    PRESET = "preset"  # 预设平台
    CUSTOM = "custom"  # 自定义平台


class PresetPlatformEnum(str, Enum):
    """预设平台枚举"""

    BAIDU = "baidu"
    ALIBABA = "alibaba"
    TENCENT = "tencent"
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"
    ZHIPU = "zhipu"
    ZHIPU_CODING = "zhipu_coding"  # 智谱AI编程套餐
    OPENAI = "openai"  # OpenAI
    ANTHROPIC = "anthropic"  # Anthropic (Claude)
    AZURE_OPENAI = "azure_openai"  # Azure OpenAI
    QWEN = "qwen"  # 通义千问


class ModelProviderEnum(str, Enum):
    """AI 模型提供商枚举（保留兼容性）"""

    ZHIPU = "zhipu"  # 智谱AI
    DEEPSEEK = "deepseek"  # DeepSeek
    QWEN = "qwen"  # 通义千问
    OPENAI = "openai"  # OpenAI
    OLLAMA = "ollama"  # Ollama
    CUSTOM = "custom"  # 自定义


# 思考模式已简化：只使用 thinking_enabled 布尔值
# 保留兼容性：旧的枚举值会被映射到布尔值
class ThinkingModeEnum(str, Enum):
    """思考模式类型枚举（已弃用，保留向后兼容）"""

    PRESERVED = "preserved"
    CLEAR_ON_NEW = "clear_on_new"
    AUTO = "auto"


class AIModelConfigBase(BaseModel):
    """AI 模型配置基础模型"""

    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    platform_type: PlatformTypeEnum = Field(
        default=PlatformTypeEnum.CUSTOM, description="平台类型（预设/自定义）"
    )
    platform_name: Optional[PresetPlatformEnum] = Field(
        None, description="预设平台名称（仅预设平台需要）"
    )
    provider: Optional[ModelProviderEnum] = Field(None, description="提供商（保留兼容性）")
    api_base_url: str = Field(..., min_length=1, description="API 基础 URL")
    api_key: str = Field(..., min_length=1, description="API Key")
    model_id: str = Field(..., min_length=1, max_length=100, description="模型 ID")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="自定义请求头")
    max_concurrency: int = Field(default=40, ge=1, le=200, description="模型最大并发数")
    task_concurrency: int = Field(
        default=2, ge=1, le=10, description="单任务并发数（单个任务可同时运行的智能体数）"
    )
    batch_concurrency: int = Field(
        default=1,
        ge=1,
        le=50,
        description=("批量任务并发数（用户可同时运行的批量任务数，" "公共模型由管理员控制）"),
    )
    timeout_seconds: int = Field(default=60, ge=10, le=600, description="超时时间（秒）")
    temperature: float = Field(default=0.5, ge=0.0, le=1.0, description="温度参数")
    enabled: bool = Field(default=True, description="是否启用")
    thinking_enabled: bool = Field(default=False, description="启用思考模式（Chain of Thought）")
    # 保留向后兼容：旧的 thinking_mode 字段
    thinking_mode: Optional[ThinkingModeEnum] = Field(
        None,
        description="思考模式类型（已弃用，仅保留向后兼容）",
    )

    # 价格配置（用户自定义）
    custom_input_price: Optional[float] = Field(
        None, ge=0, description="自定义输入价格（元/百万tokens），留空使用内置价格"
    )
    custom_output_price: Optional[float] = Field(
        None, ge=0, description="自定义输出价格（元/百万tokens），留空使用内置价格"
    )
    custom_thinking_price: Optional[float] = Field(
        None, ge=0, description="自定义思考价格（元/百万tokens），留空使用内置价格"
    )

    @model_validator(mode="after")
    def validate_concurrency(self) -> "AIModelConfigBase":
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
    platform_type: Optional[PlatformTypeEnum] = None
    platform_name: Optional[PresetPlatformEnum] = None
    provider: Optional[ModelProviderEnum] = None
    api_base_url: Optional[str] = Field(None, min_length=1)
    api_key: Optional[str] = Field(None, min_length=1)
    model_id: Optional[str] = Field(None, min_length=1, max_length=100)
    custom_headers: Optional[Dict[str, str]] = None
    max_concurrency: Optional[int] = Field(None, ge=1, le=200)
    task_concurrency: Optional[int] = Field(None, ge=1, le=10)
    batch_concurrency: Optional[int] = Field(None, ge=1, le=50)
    timeout_seconds: Optional[int] = Field(None, ge=10, le=600)
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    enabled: Optional[bool] = None
    thinking_enabled: Optional[bool] = None
    # 保留向后兼容
    thinking_mode: Optional[ThinkingModeEnum] = None

    # 价格配置（用户自定义）
    custom_input_price: Optional[float] = Field(None, ge=0)
    custom_output_price: Optional[float] = Field(None, ge=0)
    custom_thinking_price: Optional[float] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_concurrency(self) -> "AIModelConfigUpdate":
        """验证并发参数的合理性（仅当所有相关参数都提供时才验证）"""
        if all(
            [
                self.max_concurrency is not None,
                self.task_concurrency is not None,
            ]
        ):
            if self.task_concurrency > self.max_concurrency:
                raise ValueError(
                    f"单任务并发数({self.task_concurrency})不能大于模型最大并发数({self.max_concurrency})"
                )

        if all(
            [
                self.max_concurrency is not None,
                self.task_concurrency is not None,
                self.batch_concurrency is not None,
            ]
        ):
            if self.batch_concurrency * self.task_concurrency > self.max_concurrency:
                raise ValueError(
                    f"批量任务并发数({self.batch_concurrency}) × "
                    f"单任务并发数({self.task_concurrency}) "
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

    # 覆盖基类的 api_key 字段：响应对象中不返回完整 API Key
    api_key: Optional[str] = Field(None, description="API Key（响应中不返回）")

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "AIModelConfigResponse":
        """从数据库数据创建响应对象"""
        api_key_encrypted = data.get("api_key", "")

        # Base64 解码 API Key（先检查是否为有效 Base64）
        api_key = ""
        if api_key_encrypted:
            try:
                from core.security.encryption import decrypt_sensitive_data, is_encrypted
                # 先检查是否为 Base64 格式
                if is_encrypted(api_key_encrypted):
                    api_key = decrypt_sensitive_data(api_key_encrypted)
                else:
                    # 不是 Base64，可能是明文存储的旧数据
                    api_key = api_key_encrypted
            except Exception:
                # 解码失败，返回空字符串
                api_key = ""

        masked = cls._mask_api_key(api_key)

        # 兼容旧数据：provider 字段映射到 platform_type 和 platform_name
        provider = data.get("provider")
        platform_type = data.get("platform_type")
        platform_name = data.get("platform_name")

        # 如果旧数据只有 provider，尝试映射到新字段
        if provider and not platform_type:
            platform_type = PlatformTypeEnum.CUSTOM  # 旧数据默认为自定义
            # 尝试匹配预设平台
            try:
                platform_name = PresetPlatformEnum(provider)
                platform_type = PlatformTypeEnum.PRESET
            except ValueError:
                pass  # 无法匹配，保持 CUSTOM

        return cls(
            id=str(data["_id"]),
            name=data["name"],
            platform_type=platform_type or PlatformTypeEnum.CUSTOM,
            platform_name=(PresetPlatformEnum(platform_name) if platform_name else None),
            provider=ModelProviderEnum(provider) if provider else None,
            api_base_url=data["api_base_url"],
            api_key=None,  # 响应中不返回完整 API Key
            model_id=data["model_id"],
            custom_headers=data.get("custom_headers", {}),
            max_concurrency=data.get("max_concurrency", 40),
            task_concurrency=data.get("task_concurrency", 2),
            batch_concurrency=data.get("batch_concurrency", 1),
            timeout_seconds=data["timeout_seconds"],
            temperature=data["temperature"],
            enabled=data["enabled"],
            thinking_enabled=data.get("thinking_enabled", False),
            thinking_mode=data.get("thinking_mode"),  # 保留用于向后兼容
            custom_input_price=data.get("custom_input_price"),
            custom_output_price=data.get("custom_output_price"),
            custom_thinking_price=data.get("custom_thinking_price"),
            is_system=data.get("is_system", False),
            owner_id=data.get("owner_id"),
            created_at=_parse_datetime(data.get("created_at")) or datetime.now(timezone.utc),
            updated_at=_parse_datetime(data.get("updated_at")) or datetime.now(timezone.utc),
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


class ListModelsRequest(BaseModel):
    """获取模型列表请求"""

    platform_type: PlatformTypeEnum = Field(..., description="平台类型")
    platform_name: Optional[PresetPlatformEnum] = Field(
        None, description="预设平台名称（预设平台时必填）"
    )
    api_base_url: str = Field(..., description="API 基础 URL")
    api_key: str = Field(..., description="API Key")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="自定义请求头")
    timeout_seconds: int = Field(default=10, ge=5, le=30, description="超时时间（秒）")


class ModelInfo(BaseModel):
    """模型信息"""

    id: str = Field(..., description="模型 ID")
    name: Optional[str] = Field(None, description="模型名称")
    created_at: Optional[int] = Field(None, description="创建时间戳")
    owned_by: Optional[str] = Field(None, description="所有者")


class ListModelsResponse(BaseModel):
    """获取模型列表响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    models: List[ModelInfo] = Field(default_factory=list, description="模型列表")
    is_from_api: bool = Field(
        default=False, description="是否从 API 获取（True=API获取，False=预设列表）"
    )
    fallback_used: bool = Field(default=False, description="是否使用了预设列表作为兜底")
