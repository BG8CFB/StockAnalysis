"""
核心 AI 模块

提供基于 LangChain 的统一 AI 调用接口。
支持聊天补全、流式输出、思考能力等功能。
"""

# 新架构：基于 LangChain 的统一服务
from .concurrency import ConcurrencyConfig, ConcurrencyManager
from .langchain.adapter import LangChainAdapter

# 模型配置（保留兼容）
from .model import get_model_service
from .model.schemas import (
    AIModelConfigBase,
    AIModelConfigCreate,
    AIModelConfigResponse,
    AIModelConfigUpdate,
    AIModelTestRequest,
    ConnectionTestResponse,
    ModelProviderEnum,
    ThinkingModeEnum,
)
from .service import AIService, get_ai_service, set_ai_service
from .thinking_manager import ThinkingContentManager, get_thinking_manager
from .types import (
    AIMessage,
    AIResponse,
    AIStreamChunk,
    AITool,
    create_message,
    create_tool,
)

__all__ = [
    # 新架构：AI 统一服务
    "AIService",
    "get_ai_service",
    "set_ai_service",
    # 新架构：统一数据类型
    "AIMessage",
    "AITool",
    "AIResponse",
    "AIStreamChunk",
    "create_message",
    "create_tool",
    # 新架构：适配器和并发管理
    "LangChainAdapter",
    "ThinkingContentManager",
    "get_thinking_manager",
    "ConcurrencyManager",
    "ConcurrencyConfig",
    # 模型配置
    "get_model_service",
    "ModelProviderEnum",
    "AIModelConfigBase",
    "AIModelConfigCreate",
    "AIModelConfigUpdate",
    "AIModelConfigResponse",
    "AIModelTestRequest",
    "ConnectionTestResponse",
    "ThinkingModeEnum",
]


# =============================================================================
# 版本说明
# =============================================================================
# v4.0 - 全面采用 LangChain 统一架构
#   - 使用 AIService 作为统一调用入口
#   - AIMessage/AITool/AIResponse 统一数据格式
#   - LangChainAdapter 负责模型创建
#   - ConcurrencyManager 负责并发控制
#
# 旧版本兼容（将逐步废弃）：
#   - LLMProvider 及相关类型保留向后兼容
#   - 建议新代码使用 AIService
# =============================================================================
