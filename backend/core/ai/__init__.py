"""
核心 AI 配置模块

提供 AI 模型配置管理和 LLM Provider 抽象层，作为项目的公共基础设施。
"""

from core.ai.model import get_model_service
from core.ai.model.schemas import (
    ModelProviderEnum,
    AIModelConfigBase,
    AIModelConfigCreate,
    AIModelConfigUpdate,
    AIModelConfigResponse,
    AIModelTestRequest,
    ConnectionTestResponse,
)
from core.ai.llm.provider import (
    LLMProvider,
    Message,
    Tool,
    ToolCall,
    ToolResponse,
    ChatResponse,
    create_message,
    create_tool,
)

__all__ = [
    # Service
    "get_model_service",
    # Schemas
    "ModelProviderEnum",
    "AIModelConfigBase",
    "AIModelConfigCreate",
    "AIModelConfigUpdate",
    "AIModelConfigResponse",
    "AIModelTestRequest",
    "ConnectionTestResponse",
    # LLM Provider
    "LLMProvider",
    "Message",
    "Tool",
    "ToolCall",
    "ToolResponse",
    "ChatResponse",
    "create_message",
    "create_tool",
]
