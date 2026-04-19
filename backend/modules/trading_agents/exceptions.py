"""
TradingAgents 模块异常定义

定义模块内所有自定义异常类，并提供异常到 HTTP 状态码的映射。
"""

from typing import Any, Dict, Optional

from fastapi import status

# =============================================================================
# 基础异常类
# =============================================================================


class TradingAgentsError(Exception):
    """TradingAgents 模块基础异常类"""

    def __init__(
        self,
        message: str,
        code: str = "TRADING_AGENTS_ERROR",
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
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


class TaskNotFoundError(TradingAgentsError):
    """任务不存在异常"""

    def __init__(self, task_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"任务不存在: {task_id}",
            code="TASK_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"task_id": task_id, **(details or {})},
        )


class TaskAlreadyRunningError(TradingAgentsError):
    """任务已在执行中异常"""

    def __init__(self, task_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"任务已在执行中: {task_id}",
            code="TASK_ALREADY_RUNNING",
            http_status=status.HTTP_409_CONFLICT,
            details={"task_id": task_id, **(details or {})},
        )


class TaskCancelledError(TradingAgentsError):
    """任务被取消异常（用于控制流，非错误）"""

    def __init__(self, task_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"任务已被取消: {task_id}",
            code="TASK_CANCELLED",
            http_status=status.HTTP_200_OK,
            details={"task_id": task_id, **(details or {})},
        )


class TaskExpiredError(TradingAgentsError):
    """任务已过期异常"""

    def __init__(self, task_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"任务已过期: {task_id}",
            code="TASK_EXPIRED",
            http_status=status.HTTP_410_GONE,
            details={"task_id": task_id, **(details or {})},
        )


class TaskExecutionError(TradingAgentsError):
    """任务执行异常"""

    def __init__(self, task_id: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"任务执行失败: {task_id} - {reason}",
            code="TASK_EXECUTION_FAILED",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"task_id": task_id, "reason": reason, **(details or {})},
        )


class TaskRecoveryError(TradingAgentsError):
    """任务恢复异常"""

    def __init__(self, task_id: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"任务恢复失败: {task_id} - {reason}",
            code="TASK_RECOVERY_FAILED",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"task_id": task_id, "reason": reason, **(details or {})},
        )


# =============================================================================
# 配置相关异常
# =============================================================================


class ConfigurationError(TradingAgentsError):
    """配置错误异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            http_status=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class AgentNotFoundError(TradingAgentsError):
    """智能体不存在异常"""

    def __init__(self, agent_slug: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"智能体不存在: {agent_slug}",
            code="AGENT_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"agent_slug": agent_slug, **(details or {})},
        )


class InvalidConfigurationError(TradingAgentsError):
    """无效配置异常"""

    def __init__(self, config_type: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"无效的{config_type}配置: {reason}",
            code="INVALID_CONFIGURATION",
            http_status=status.HTTP_400_BAD_REQUEST,
            details={"config_type": config_type, "reason": reason, **(details or {})},
        )


# =============================================================================
# AI 模型相关异常
# =============================================================================


class ModelNotFoundError(TradingAgentsError):
    """AI 模型不存在异常"""

    def __init__(self, model_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"AI 模型不存在: {model_id}",
            code="MODEL_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"model_id": model_id, **(details or {})},
        )


class ModelConnectionError(TradingAgentsError):
    """AI 模型连接异常"""

    def __init__(self, model_id: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"AI 模型连接失败: {model_id} - {reason}",
            code="MODEL_CONNECTION_FAILED",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"model_id": model_id, "reason": reason, **(details or {})},
        )


class ModelQuotaExhaustedError(TradingAgentsError):
    """模型配额耗尽异常"""

    def __init__(
        self,
        model_id: str,
        queue_position: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"模型配额已满: {model_id}"
        if queue_position is not None:
            message += f"，排队位置: {queue_position}"

        super().__init__(
            message=message,
            code="MODEL_QUOTA_EXHAUSTED",
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"model_id": model_id, "queue_position": queue_position, **(details or {})},
        )


class ModelInUseError(TradingAgentsError):
    """模型正在使用中异常（无法删除）"""

    def __init__(self, model_id: str, active_tasks: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"模型正在使用中，无法删除: {model_id}，活动任务数: {active_tasks}",
            code="MODEL_IN_USE",
            http_status=status.HTTP_409_CONFLICT,
            details={"model_id": model_id, "active_tasks": active_tasks, **(details or {})},
        )


# =============================================================================
# MCP 服务器相关异常
# =============================================================================


class MCPServerNotFoundError(TradingAgentsError):
    """MCP 服务器不存在异常"""

    def __init__(self, server_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"MCP 服务器不存在: {server_id}",
            code="MCP_SERVER_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"server_id": server_id, **(details or {})},
        )


class MCPConnectionError(TradingAgentsError):
    """MCP 服务器连接异常"""

    def __init__(self, server_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"MCP 服务器连接失败: {server_name} - {reason}",
            code="MCP_CONNECTION_FAILED",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"server_name": server_name, "reason": reason, **(details or {})},
        )


class MCPUnavailableError(TradingAgentsError):
    """MCP 服务器不可用异常"""

    def __init__(self, server_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"MCP 服务器不可用: {server_name}",
            code="MCP_UNAVAILABLE",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"server_name": server_name, **(details or {})},
        )


# =============================================================================
# 工具相关异常
# =============================================================================


class ToolNotFoundError(TradingAgentsError):
    """工具不存在异常"""

    def __init__(self, tool_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"工具不存在: {tool_name}",
            code="TOOL_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"tool_name": tool_name, **(details or {})},
        )


class ToolCallError(TradingAgentsError):
    """工具调用异常"""

    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"工具调用失败: {tool_name} - {reason}",
            code="TOOL_CALL_FAILED",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"tool_name": tool_name, "reason": reason, **(details or {})},
        )


class ToolTimeoutError(TradingAgentsError):
    """工具调用超时异常"""

    def __init__(self, tool_name: str, timeout: float, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"工具调用超时: {tool_name} - 超时{timeout}秒",
            code="TOOL_TIMEOUT",
            http_status=status.HTTP_408_REQUEST_TIMEOUT,
            details={"tool_name": tool_name, "timeout": timeout, **(details or {})},
        )


class ToolCallTimeoutError(TradingAgentsError):
    """工具调用超时异常"""

    def __init__(
        self, tool_name: str, timeout_seconds: int, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"工具调用超时: {tool_name}（超过 {timeout_seconds} 秒）",
            code="TOOL_CALL_TIMEOUT",
            http_status=status.HTTP_504_GATEWAY_TIMEOUT,
            details={"tool_name": tool_name, "timeout_seconds": timeout_seconds, **(details or {})},
        )


class ToolLoopDetectedError(TradingAgentsError):
    """检测到工具循环调用异常"""

    def __init__(
        self,
        tool_name: str,
        agent_slug: str,
        call_count: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"检测到工具循环调用: {tool_name}（连续调用 {call_count} 次）",
            code="TOOL_LOOP_DETECTED",
            http_status=status.HTTP_400_BAD_REQUEST,
            details={
                "tool_name": tool_name,
                "agent_slug": agent_slug,
                "call_count": call_count,
                **(details or {}),
            },
        )


# =============================================================================
# 并发控制相关异常
# =============================================================================


class ConcurrencyLimitError(TradingAgentsError):
    """并发限制异常"""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        limit: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"{resource_type} 并发限制已满: {resource_id}（限制: {limit}）",
            code="CONCURRENCY_LIMIT_EXCEEDED",
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "limit": limit,
                **(details or {}),
            },
        )


class QueueTimeoutError(TradingAgentsError):
    """队列等待超时异常"""

    def __init__(
        self, queue_name: str, timeout_seconds: int, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"队列等待超时: {queue_name}（超过 {timeout_seconds} 秒）",
            code="QUEUE_TIMEOUT",
            http_status=status.HTTP_504_GATEWAY_TIMEOUT,
            details={
                "queue_name": queue_name,
                "timeout_seconds": timeout_seconds,
                **(details or {}),
            },
        )


# =============================================================================
# 报告相关异常
# =============================================================================


class ReportNotFoundError(TradingAgentsError):
    """报告不存在异常"""

    def __init__(self, report_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"报告不存在: {report_id}",
            code="REPORT_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND,
            details={"report_id": report_id, **(details or {})},
        )


# =============================================================================
# 异常到 HTTP 状态码映射
# =============================================================================

EXCEPTION_TO_STATUS: Dict[type, int] = {
    TaskNotFoundError: status.HTTP_404_NOT_FOUND,
    TaskAlreadyRunningError: status.HTTP_409_CONFLICT,
    TaskCancelledError: status.HTTP_200_OK,
    TaskExpiredError: status.HTTP_410_GONE,
    TaskExecutionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    TaskRecoveryError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ConfigurationError: status.HTTP_400_BAD_REQUEST,
    AgentNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidConfigurationError: status.HTTP_400_BAD_REQUEST,
    ModelNotFoundError: status.HTTP_404_NOT_FOUND,
    ModelConnectionError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ModelQuotaExhaustedError: status.HTTP_429_TOO_MANY_REQUESTS,
    ModelInUseError: status.HTTP_409_CONFLICT,
    MCPServerNotFoundError: status.HTTP_404_NOT_FOUND,
    MCPConnectionError: status.HTTP_503_SERVICE_UNAVAILABLE,
    MCPUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ToolNotFoundError: status.HTTP_404_NOT_FOUND,
    ToolCallError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ToolCallTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
    ToolLoopDetectedError: status.HTTP_400_BAD_REQUEST,
    ConcurrencyLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    QueueTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
    ReportNotFoundError: status.HTTP_404_NOT_FOUND,
}


def get_http_status_from_exception(exc: Exception) -> int:
    """
    从异常获取 HTTP 状态码

    Args:
        exc: 异常对象

    Returns:
        HTTP 状态码
    """
    if isinstance(exc, TradingAgentsError):
        return exc.http_status

    # 查找映射表
    for exc_type, status_code in EXCEPTION_TO_STATUS.items():
        if isinstance(exc, exc_type):
            return status_code

    # 默认返回 500
    return status.HTTP_500_INTERNAL_SERVER_ERROR
