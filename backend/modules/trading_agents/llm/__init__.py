"""
LLM 管理模块

包含 LLM Provider 抽象层和 OpenAI 兼容适配器。
"""

from .provider import (
    LLMProvider,
    Message,
    Tool,
    ToolCall,
    ChatResponse,
    ToolResponse,
    create_message,
    create_tool,
    format_messages_for_logging,
)
from .openai_compat import (
    OpenAICompatProvider,
    LLMProviderFactory,
)

__all__ = [
    # Provider
    "LLMProvider",
    "OpenAICompatProvider",
    "LLMProviderFactory",
    # Types
    "Message",
    "Tool",
    "ToolCall",
    "ChatResponse",
    "ToolResponse",
    # Helpers
    "create_message",
    "create_tool",
    "format_messages_for_logging",
]
