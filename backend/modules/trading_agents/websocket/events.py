"""
WebSocket 事件定义

定义所有 WebSocket 事件类型和格式。
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# 事件类型枚举
# =============================================================================

class EventType(str, Enum):
    """WebSocket 事件类型"""

    # 任务相关
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_STOPPED = "task_stopped"
    TASK_EXPIRED = "task_expired"

    # 阶段相关
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"

    # 智能体相关
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"

    # 工具相关
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    TOOL_DISABLED = "tool_disabled"

    # 报告相关
    REPORT_GENERATED = "report_generated"
    REPORT_STREAM_CHUNK = "report_stream_chunk"  # 流式报告片段

    # 进度相关
    PROGRESS_UPDATE = "progress_update"


# =============================================================================
# 事件数据结构
# =============================================================================

@dataclass
class TaskEvent:
    """
    任务事件

    所有 WebSocket 事件的基础数据结构。
    """
    event_type: EventType = None  # Set by subclasses in __post_init__
    task_id: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }


@dataclass
class PhaseStartedEvent(TaskEvent):
    """阶段开始事件"""
    phase: int = 0
    phase_name: str = ""
    total_agents: int = 0

    def __post_init__(self):
        self.event_type = EventType.PHASE_STARTED
        self.data = {
            "phase": self.phase,
            "phase_name": self.phase_name,
            "total_agents": self.total_agents,
        }


@dataclass
class AgentStartedEvent(TaskEvent):
    """智能体开始事件"""
    agent_slug: str = ""
    agent_name: str = ""

    def __post_init__(self):
        self.event_type = EventType.AGENT_STARTED
        self.data = {
            "agent_slug": self.agent_slug,
            "agent_name": self.agent_name,
        }


@dataclass
class AgentCompletedEvent(TaskEvent):
    """智能体完成事件"""
    agent_slug: str = ""
    agent_name: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = EventType.AGENT_COMPLETED
        self.data = {
            "agent_slug": self.agent_slug,
            "agent_name": self.agent_name,
            "token_usage": self.token_usage,
        }


@dataclass
class ToolCalledEvent(TaskEvent):
    """工具调用事件"""
    agent_slug: str = ""
    tool_name: str = ""
    tool_input: str = ""

    def __post_init__(self):
        self.event_type = EventType.TOOL_CALLED
        self.data = {
            "agent_slug": self.agent_slug,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
        }


@dataclass
class ToolResultEvent(TaskEvent):
    """工具结果事件"""
    agent_slug: str = ""
    tool_name: str = ""
    success: bool = False
    output: str = ""
    error: Optional[str] = None

    def __post_init__(self):
        self.event_type = EventType.TOOL_RESULT
        self.data = {
            "agent_slug": self.agent_slug,
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class ToolDisabledEvent(TaskEvent):
    """工具禁用事件"""
    agent_slug: str = ""
    tool_name: str = ""
    reason: str = ""

    def __post_init__(self):
        self.event_type = EventType.TOOL_DISABLED
        self.data = {
            "agent_slug": self.agent_slug,
            "tool_name": self.tool_name,
            "reason": self.reason,
        }


@dataclass
class ReportGeneratedEvent(TaskEvent):
    """报告生成事件"""
    agent_slug: str = ""
    agent_name: str = ""
    content: str = ""

    def __post_init__(self):
        self.event_type = EventType.REPORT_GENERATED
        self.data = {
            "agent_slug": self.agent_slug,
            "agent_name": self.agent_name,
            "content": self.content,
        }


@dataclass
class ReportStreamChunkEvent(TaskEvent):
    """报告流式片段事件"""
    agent_slug: str = ""
    chunk: str = ""
    is_final: bool = False

    def __post_init__(self):
        self.event_type = EventType.REPORT_STREAM_CHUNK
        self.data = {
            "agent_slug": self.agent_slug,
            "chunk": self.chunk,
            "is_final": self.is_final,
        }


@dataclass
class ProgressUpdateEvent(TaskEvent):
    """进度更新事件"""
    progress: float = 0.0
    message: str = ""

    def __post_init__(self):
        self.event_type = EventType.PROGRESS_UPDATE
        self.data = {
            "progress": self.progress,
            "message": self.message,
        }


@dataclass
class TaskCompletedEvent(TaskEvent):
    """任务完成事件"""
    final_recommendation: Optional[str] = None
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None
    total_token_usage: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = EventType.TASK_COMPLETED
        self.data = {
            "final_recommendation": self.final_recommendation,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "total_token_usage": self.total_token_usage,
        }


@dataclass
class TaskFailedEvent(TaskEvent):
    """任务失败事件"""
    error_message: str = ""
    error_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.event_type = EventType.TASK_FAILED
        self.data = {
            "error_message": self.error_message,
            "error_details": self.error_details,
        }


# =============================================================================
# 事件工厂函数
# =============================================================================

def create_event(
    event_type: EventType,
    task_id: str,
    **kwargs
) -> TaskEvent:
    """
    创建事件对象

    Args:
        event_type: 事件类型
        task_id: 任务 ID
        **kwargs: 事件数据

    Returns:
        事件对象
    """
    return TaskEvent(
        event_type=event_type,
        task_id=task_id,
        data=kwargs
    )


def create_phase_started_event(
    task_id: str,
    phase: int,
    phase_name: str,
    total_agents: int = 0
) -> PhaseStartedEvent:
    """创建阶段开始事件"""
    return PhaseStartedEvent(
        task_id=task_id,
        phase=phase,
        phase_name=phase_name,
        total_agents=total_agents
    )


def create_agent_started_event(
    task_id: str,
    agent_slug: str,
    agent_name: str
) -> AgentStartedEvent:
    """创建智能体开始事件"""
    return AgentStartedEvent(
        task_id=task_id,
        agent_slug=agent_slug,
        agent_name=agent_name
    )


def create_agent_completed_event(
    task_id: str,
    agent_slug: str,
    agent_name: str,
    token_usage: Dict[str, int]
) -> AgentCompletedEvent:
    """创建智能体完成事件"""
    return AgentCompletedEvent(
        task_id=task_id,
        agent_slug=agent_slug,
        agent_name=agent_name,
        token_usage=token_usage
    )


def create_tool_called_event(
    task_id: str,
    agent_slug: str,
    tool_name: str,
    tool_input: str
) -> ToolCalledEvent:
    """创建工具调用事件"""
    return ToolCalledEvent(
        task_id=task_id,
        agent_slug=agent_slug,
        tool_name=tool_name,
        tool_input=tool_input
    )


def create_tool_result_event(
    task_id: str,
    agent_slug: str,
    tool_name: str,
    success: bool,
    output: str = "",
    error: Optional[str] = None
) -> ToolResultEvent:
    """创建工具结果事件"""
    return ToolResultEvent(
        task_id=task_id,
        agent_slug=agent_slug,
        tool_name=tool_name,
        success=success,
        output=output,
        error=error
    )


def create_report_generated_event(
    task_id: str,
    agent_slug: str,
    agent_name: str,
    content: str
) -> ReportGeneratedEvent:
    """创建报告生成事件"""
    return ReportGeneratedEvent(
        task_id=task_id,
        agent_slug=agent_slug,
        agent_name=agent_name,
        content=content
    )


def create_task_completed_event(
    task_id: str,
    final_recommendation: Optional[str] = None,
    buy_price: Optional[float] = None,
    sell_price: Optional[float] = None,
    total_token_usage: Optional[Dict[str, int]] = None
) -> TaskCompletedEvent:
    """创建任务完成事件"""
    return TaskCompletedEvent(
        task_id=task_id,
        final_recommendation=final_recommendation,
        buy_price=buy_price,
        sell_price=sell_price,
        total_token_usage=total_token_usage or {}
    )


def create_task_failed_event(
    task_id: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None
) -> TaskFailedEvent:
    """创建任务失败事件"""
    return TaskFailedEvent(
        task_id=task_id,
        error_message=error_message,
        error_details=error_details
    )


def create_progress_update_event(
    task_id: str,
    progress: float,
    message: str = ""
) -> ProgressUpdateEvent:
    """创建进度更新事件"""
    return ProgressUpdateEvent(
        task_id=task_id,
        progress=progress,
        message=message
    )
