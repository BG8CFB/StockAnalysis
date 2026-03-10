"""
AI 统一数据类型定义

定义整个 AI 模块使用的统一数据结构。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AIMessage:
    """统一消息格式"""

    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    reasoning_content: Optional[str] = None  # 思考内容（用于支持思考模式的模型）

    def to_langchain(self):
        """转换为 LangChain 消息格式"""
        from langchain_core.messages import (
            AIMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
        )

        if self.role == "system":
            return SystemMessage(content=self.content)
        elif self.role == "user":
            return HumanMessage(content=self.content)
        elif self.role == "assistant":
            msg = AIMessage(content=self.content)
            if self.tool_calls:
                msg.tool_calls = self.tool_calls
            if self.reasoning_content:
                # 思考内容通过 additional_kwargs 传递，支持保留式思考
                msg.additional_kwargs["reasoning_content"] = self.reasoning_content
            return msg
        elif self.role == "tool":
            return ToolMessage(content=self.content, tool_call_id=self.tool_call_id or "")
        else:
            raise ValueError(f"未知的消息角色: {self.role}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result: Dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.reasoning_content:
            result["reasoning_content"] = self.reasoning_content
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIMessage":
        """从字典创建消息"""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            reasoning_content=data.get("reasoning_content"),
        )


@dataclass
class AITool:
    """统一工具格式"""

    name: str
    description: str
    parameters: Dict[str, Any]

    def to_langchain_format(self) -> Dict[str, Any]:
        """转换为 LangChain 工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class AIResponse:
    """统一响应格式"""

    content: str
    reasoning_content: Optional[str] = None  # 思考内容
    thinking_tokens: Optional[int] = None  # 思考 token 数
    usage: Optional[Dict[str, int]] = None
    tool_calls: Optional[List[Dict]] = None
    raw_response: Optional[Dict] = None  # 原始响应

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result: Dict[str, Any] = {
            "content": self.content,
        }
        if self.reasoning_content is not None:
            result["reasoning_content"] = self.reasoning_content
        if self.thinking_tokens is not None:
            result["thinking_tokens"] = self.thinking_tokens
        if self.usage:
            result["usage"] = self.usage
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result


@dataclass
class AIStreamChunk:
    """流式响应块"""

    content: str
    reasoning_content: Optional[str] = None
    is_complete: bool = False
    usage: Optional[Dict[str, int]] = None


# =============================================================================
# 辅助函数
# =============================================================================


def create_message(role: str, content: str, **kwargs) -> AIMessage:
    """创建消息对象"""
    return AIMessage(role=role, content=content, **kwargs)


def create_tool(name: str, description: str, parameters: Dict[str, Any]) -> AITool:
    """创建工具定义"""
    return AITool(name=name, description=description, parameters=parameters)
