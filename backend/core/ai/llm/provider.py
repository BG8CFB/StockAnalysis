"""
LLM Provider 抽象层

定义大语言模型提供商的抽象接口，支持多种模型接入。
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field

from core.ai.exceptions import ModelConnectionException, ToolCallException

logger = logging.getLogger(__name__)


# =============================================================================
# 类型定义
# =============================================================================

@dataclass
class Message:
    """聊天消息"""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class Tool:
    """工具定义"""
    type: str = "function"
    function: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    type: str = "function"
    function: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResponse:
    """工具响应"""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional[Dict[str, int]] = None
    model: str = ""


# =============================================================================
# LLM Provider 抽象基类
# =============================================================================

class LLMProvider(ABC):
    """
    大语言模型提供商抽象基类

    所有 LLM 提供商必须实现此接口。
    """

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model_id: str,
        timeout_seconds: int = 60,
        temperature: float = 0.5,
        max_retries: int = 3,
    ):
        """
        初始化 LLM Provider

        Args:
            api_base_url: API 基础 URL
            api_key: API 密钥
            model_id: 模型 ID
            timeout_seconds: 请求超时时间（秒）
            temperature: 温度参数
            max_retries: 最大重试次数
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_retries = max_retries

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """
        聊天补全

        Args:
            messages: 消息列表
            tools: 可用工具列表
            temperature: 温度参数（覆盖默认值）
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数

        Returns:
            ChatResponse 对象

        Raises:
            ModelConnectionException: 连接失败
            ToolCallException: 工具调用失败
        """
        pass

    @abstractmethod
    async def stream_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天补全

        Args:
            messages: 消息列表
            tools: 可用工具列表
            temperature: 温度参数（覆盖默认值）
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数

        Yields:
            生成的文本片段

        Raises:
            ModelConnectionException: 连接失败
            ToolCallException: 工具调用失败
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        测试 API 连接

        Returns:
            连接是否成功

        Raises:
            ModelConnectionException: 连接失败
        """
        pass

    def get_temperature(self, override: Optional[float] = None) -> float:
        """获取温度参数"""
        return override if override is not None else self.temperature

    def get_model_id(self) -> str:
        """获取模型 ID"""
        return self.model_id


# =============================================================================
# 辅助函数
# =============================================================================

def create_message(role: str, content: str, **kwargs) -> Message:
    """
    创建消息对象

    Args:
        role: 消息角色
        content: 消息内容
        **kwargs: 其他字段

    Returns:
        Message 对象
    """
    return Message(role=role, content=content, **kwargs)


def create_tool(name: str, description: str, parameters: Dict[str, Any]) -> Tool:
    """
    创建工具定义

    Args:
        name: 工具名称
        description: 工具描述
        parameters: 参数模式（JSON Schema 格式）

    Returns:
        Tool 对象
    """
    return Tool(
        type="function",
        function={
            "name": name,
            "description": description,
            "parameters": parameters,
        }
    )


def format_messages_for_logging(messages: List[Message]) -> List[Dict[str, Any]]:
    """
    格式化消息用于日志记录（脱敏）

    Args:
        messages: 消息列表

    Returns:
        格式化后的消息列表
    """
    formatted = []
    for msg in messages:
        formatted_msg = {
            "role": msg.role,
            "content": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content,
        }
        if msg.tool_calls:
            formatted_msg["tool_calls"] = f"[{len(msg.tool_calls)} tool calls]"
        formatted.append(formatted_msg)
    return formatted


async def retry_on_failure(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,),
):
    """
    重试装饰器

    Args:
        func: 要重试的异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        exceptions: 要捕获的异常类型

    Returns:
        函数执行结果

    Raises:
        最后一次异常
    """
    import asyncio

    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # 指数退避
                logger.warning(f"请求失败，{delay}秒后重试 (第{attempt + 1}/{max_retries}次): {e}")
                await asyncio.sleep(delay)
            else:
                logger.error(f"请求失败，已达最大重试次数: {e}")

    raise last_exception
