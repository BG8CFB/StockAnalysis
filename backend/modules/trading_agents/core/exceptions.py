"""
TradingAgents 模块异常定义

定义模块内所有自定义异常类，并提供异常到 HTTP 状态码的映射。
"""

from typing import Optional, Any, Dict
from fastapi import status


# =============================================================================
# 基础异常类
# =============================================================================

class TradingAgentsException(Exception):
    """TradingAgents 模块基础异常类"""

    def __init__(
        self,
        message: str,
        code: str = "TRADING_AGENTS_ERROR",
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.http_status = http_status
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details if self.details else None,
            },
        }


# =============================================================================
# 任务相关异常
# =============================================================================

class TaskNotFoundException(TradingAgentsException):
    """任务不存在异常"""

    def __init__(
        self,
        task_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"任务不存在: {task_id}",
            code="TASK_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"task_id": task_id, **(details or {})}
        )


class TaskAlreadyRunningException(TradingAgentsException):
    """任务已在执行中异常"""

    def __init__(
        self,
        task_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"任务已在执行中: {task_id}",
            code="TASK_ALREADY_RUNNING",
            http_status=status.HTTP_409_CONFLICT,
            details={"task_id": task_id, **(details or {})}
        )


class TaskCancelledException(TradingAgentsException):
    """任务被取消异常（用于控制流，非错误）"""

    def __init__(
        self,
        task_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"任务已被取消: {task_id}",
            code="TASK_CANCELLED",
            http_status=status.HTTP_200_OK,
            details={"task_id": task_id, **(details or {})}
        )


class TaskExpiredException(TradingAgentsException):
    """任务已过期异常"""

    def __init__(
        self,
        task_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"任务已过期: {task_id}",
            code="TASK_EXPIRED",
            http_status=status.HTTP_410_GONE,
            details={"task_id": task_id, **(details or {})}
        )


class TaskExecutionException(TradingAgentsException):
    """任务执行异常"""

    def __init__(
        self,
        task_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"任务执行失败: {task_id} - {reason}",
            code="TASK_EXECUTION_FAILED",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"task_id": task_id, "reason": reason, **(details or {})}
        )


class TaskRecoveryException(TradingAgentsException):
    """任务恢复异常"""

    def __init__(
        self,
        task_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"任务恢复失败: {task_id} - {reason}",
            code="TASK_RECOVERY_FAILED",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"task_id": task_id, "reason": reason, **(details or {})}
        )


# =============================================================================
# 配置相关异常
# =============================================================================

class ConfigurationError(TradingAgentsException):
    """配置错误异常"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            http_status=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class AgentNotFoundException(TradingAgentsException):
    """智能体不存在异常"""

    def __init__(
        self,
        agent_slug: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"智能体不存在: {agent_slug}",
            code="AGENT_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"agent_slug": agent_slug, **(details or {})}
        )


class InvalidConfigurationError(TradingAgentsException):
    """无效配置异常"""

    def __init__(
        self,
        config_type: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"无效的{config_type}配置: {reason}",
            code="INVALID_CONFIGURATION",
            http_status=status.HTTP_400_BAD_REQUEST,
            details={"config_type": config_type, "reason": reason, **(details or {})}
        )


# =============================================================================
# AI 模型相关异常
# =============================================================================

class ModelNotFoundException(TradingAgentsException):
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


class ModelConnectionException(TradingAgentsException):
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


class ModelQuotaExhaustedError(TradingAgentsException):
    """模型配额耗尽异常"""

    def __init__(
        self,
        model_id: str,
        queue_position: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"模型配额已满: {model_id}"
        if queue_position is not None:
            message += f"，排队位置: {queue_position}"

        super().__init__(
            message=message,
            code="MODEL_QUOTA_EXHAUSTED",
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "model_id": model_id,
                "queue_position": queue_position,
                **(details or {})
            }
        )


class ModelInUseException(TradingAgentsException):
    """模型正在使用中异常（无法删除）"""

    def __init__(
        self,
        model_id: str,
        active_tasks: int,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"模型正在使用中，无法删除: {model_id}，活动任务数: {active_tasks}",
            code="MODEL_IN_USE",
            http_status=status.HTTP_409_CONFLICT,
            details={
                "model_id": model_id,
                "active_tasks": active_tasks,
                **(details or {})
            }
        )


# =============================================================================
# MCP 服务器相关异常
# =============================================================================

class MCPServerNotFoundException(TradingAgentsException):
    """MCP 服务器不存在异常"""

    def __init__(
        self,
        server_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"MCP 服务器不存在: {server_id}",
            code="MCP_SERVER_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"server_id": server_id, **(details or {})}
        )


class MCPConnectionException(TradingAgentsException):
    """MCP 服务器连接异常"""

    def __init__(
        self,
        server_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"MCP 服务器连接失败: {server_name} - {reason}",
            code="MCP_CONNECTION_FAILED",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"server_name": server_name, "reason": reason, **(details or {})}
        )


class MCPUnavailableException(TradingAgentsException):
    """MCP 服务器不可用异常"""

    def __init__(
        self,
        server_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"MCP 服务器不可用: {server_name}",
            code="MCP_UNAVAILABLE",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"server_name": server_name, **(details or {})}
        )


# =============================================================================
# 工具相关异常
# =============================================================================

class ToolNotFoundException(TradingAgentsException):
    """工具不存在异常"""

    def __init__(
        self,
        tool_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"工具不存在: {tool_name}",
            code="TOOL_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"tool_name": tool_name, **(details or {})}
        )


class ToolCallException(TradingAgentsException):
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


class ToolCallTimeoutException(TradingAgentsException):
    """工具调用超时异常"""

    def __init__(
        self,
        tool_name: str,
        timeout_seconds: int,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"工具调用超时: {tool_name}（超过 {timeout_seconds} 秒）",
            code="TOOL_CALL_TIMEOUT",
            http_status=status.HTTP_504_GATEWAY_TIMEOUT,
            details={
                "tool_name": tool_name,
                "timeout_seconds": timeout_seconds,
                **(details or {})
            }
        )


class ToolLoopDetectedException(TradingAgentsException):
    """检测到工具循环调用异常"""

    def __init__(
        self,
        tool_name: str,
        agent_slug: str,
        call_count: int,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"检测到工具循环调用: {tool_name}（连续调用 {call_count} 次）",
            code="TOOL_LOOP_DETECTED",
            http_status=status.HTTP_400_BAD_REQUEST,
            details={
                "tool_name": tool_name,
                "agent_slug": agent_slug,
                "call_count": call_count,
                **(details or {})
            }
        )


# =============================================================================
# 并发控制相关异常
# =============================================================================

class ConcurrencyLimitException(TradingAgentsException):
    """并发限制异常"""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        limit: int,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{resource_type} 并发限制已满: {resource_id}（限制: {limit}）",
            code="CONCURRENCY_LIMIT_EXCEEDED",
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "limit": limit,
                **(details or {})
            }
        )


class QueueTimeoutException(TradingAgentsException):
    """队列等待超时异常"""

    def __init__(
        self,
        queue_name: str,
        timeout_seconds: int,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"队列等待超时: {queue_name}（超过 {timeout_seconds} 秒）",
            code="QUEUE_TIMEOUT",
            http_status=status.HTTP_504_GATEWAY_TIMEOUT,
            details={
                "queue_name": queue_name,
                "timeout_seconds": timeout_seconds,
                **(details or {})
            }
        )


# =============================================================================
# 报告相关异常
# =============================================================================

class ReportNotFoundException(TradingAgentsException):
    """报告不存在异常"""

    def __init__(
        self,
        report_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"报告不存在: {report_id}",
            code="REPORT_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"report_id": report_id, **(details or {})}
        )


# =============================================================================
# 异常到 HTTP 状态码映射
# =============================================================================

EXCEPTION_TO_STATUS: Dict[type, int] = {
    TaskNotFoundException: status.HTTP_404_NOT_FOUND,
    TaskAlreadyRunningException: status.HTTP_409_CONFLICT,
    TaskCancelledException: status.HTTP_200_OK,
    TaskExpiredException: status.HTTP_410_GONE,
    TaskExecutionException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    TaskRecoveryException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ConfigurationError: status.HTTP_400_BAD_REQUEST,
    AgentNotFoundException: status.HTTP_404_NOT_FOUND,
    InvalidConfigurationError: status.HTTP_400_BAD_REQUEST,
    ModelNotFoundException: status.HTTP_404_NOT_FOUND,
    ModelConnectionException: status.HTTP_503_SERVICE_UNAVAILABLE,
    ModelQuotaExhaustedError: status.HTTP_429_TOO_MANY_REQUESTS,
    ModelInUseException: status.HTTP_409_CONFLICT,
    MCPServerNotFoundException: status.HTTP_404_NOT_FOUND,
    MCPConnectionException: status.HTTP_503_SERVICE_UNAVAILABLE,
    MCPUnavailableException: status.HTTP_503_SERVICE_UNAVAILABLE,
    ToolNotFoundException: status.HTTP_404_NOT_FOUND,
    ToolCallException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ToolCallTimeoutException: status.HTTP_504_GATEWAY_TIMEOUT,
    ToolLoopDetectedException: status.HTTP_400_BAD_REQUEST,
    ConcurrencyLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
    QueueTimeoutException: status.HTTP_504_GATEWAY_TIMEOUT,
    ReportNotFoundException: status.HTTP_404_NOT_FOUND,
}


def get_http_status_from_exception(exc: Exception) -> int:
    """
    从异常获取 HTTP 状态码

    Args:
        exc: 异常对象

    Returns:
        HTTP 状态码
    """
    if isinstance(exc, TradingAgentsException):
        return exc.http_status

    # 查找映射表
    for exc_type, status_code in EXCEPTION_TO_STATUS.items():
        if isinstance(exc, exc_type):
            return status_code

    # 默认返回 500
    return status.HTTP_500_INTERNAL_SERVER_ERROR
