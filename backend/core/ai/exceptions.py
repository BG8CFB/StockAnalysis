"""
核心 AI 模块异常定义

定义 AI 配置和 LLM Provider 相关的异常类。
"""

from typing import Optional, Dict, Any
from fastapi import status


class AIException(Exception):
    """核心 AI 模块基础异常类"""

    def __init__(
        self,
        message: str,
        code: str = "AI_ERROR",
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.http_status = http_status
        self.details = details or {}
        super().__init__(self.message)


class ModelConnectionException(AIException):
    """AI 模型连接异常"""

    def __init__(
        self,
        model_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"AI 模型连接失败: {model_id} - {reason}",
            code="MODEL_CONNECTION_FAILED",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"model_id": model_id, "reason": reason, **(details or {})}
        )


class ModelNotFoundException(AIException):
    """AI 模型不存在异常"""

    def __init__(
        self,
        model_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"AI 模型不存在: {model_id}",
            code="MODEL_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"model_id": model_id, **(details or {})}
        )


class ToolCallException(AIException):
    """工具调用异常"""

    def __init__(
        self,
        tool_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"工具调用失败: {tool_name} - {reason}",
            code="TOOL_CALL_FAILED",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"tool_name": tool_name, "reason": reason, **(details or {})}
        )
