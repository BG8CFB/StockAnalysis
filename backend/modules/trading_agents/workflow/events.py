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
    PHASE_AGENTS = "phase_agents"  # 阶段智能体列表

    # 并发组相关
    CONCURRENT_GROUP_STARTED = "concurrent_group_started"
    CONCURRENT_GROUP_COMPLETED = "concurrent_group_completed"

    # 智能体相关
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_MESSAGE = "agent_message"  # 智能体消息（思考过程）

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
class PhaseAgentsEvent(TaskEvent):
    """阶段智能体列表事件"""
    phase: int = 0
    phase_name: str = ""
    execution_mode: str = "serial"  # "serial" 或 "concurrent"
    max_concurrency: int = 1
    concurrent_group: str = ""
    agents: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.event_type = EventType.PHASE_AGENTS
        self.data = {
            "phase": self.phase,
            "phase_name": self.phase_name,
            "execution_mode": self.execution_mode,
            "max_concurrency": self.max_concurrency,
            "concurrent_group": self.concurrent_group,
            "agents": self.agents,
        }


@dataclass
class ConcurrentGroupStartedEvent(TaskEvent):
    """并发组开始事件"""
    group_id: str = ""
    phase: int = 0
    agents: List[str] = field(default_factory=list)
    max_concurrency: int = 1
    estimated_duration_sec: int = 0

    def __post_init__(self):
        self.event_type = EventType.CONCURRENT_GROUP_STARTED
        self.data = {
            "group_id": self.group_id,
            "phase": self.phase,
            "agents": self.agents,
            "max_concurrency": self.max_concurrency,
            "estimated_duration_sec": self.estimated_duration_sec,
        }


@dataclass
class ConcurrentGroupCompletedEvent(TaskEvent):
    """并发组完成事件"""
    group_id: str = ""
    phase: int = 0
    total_agents: int = 0

    def __post_init__(self):
        self.event_type = EventType.CONCURRENT_GROUP_COMPLETED
        self.data = {
            "group_id": self.group_id,
            "phase": self.phase,
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
class AgentMessageEvent(TaskEvent):
    """智能体消息事件（思考过程）"""
    agent_slug: str = ""
    agent_name: str = ""
    message_type: str = "thinking"  # thinking, reasoning, final
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = EventType.AGENT_MESSAGE
        self.data = {
            "agent_slug": self.agent_slug,
            "agent_name": self.agent_name,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": self.metadata,
        }

@dataclass
class ToolCalledEvent(TaskEvent):
    """工具调用事件"""
    agent_slug: str = ""
    agent_name: str = ""
    tool_name: str = ""
    tool_input: str = ""

    def __post_init__(self):
        self.event_type = EventType.TOOL_CALLED
        self.data = {
            "agent_slug": self.agent_slug,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "input": self.tool_input,  # 前端兼容
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


def create_phase_agents_event(
    task_id: str,
    phase: int,
    phase_name: str,
    execution_mode: str,
    max_concurrency: int,
    concurrent_group: str = "",
    agents: Optional[List[Dict[str, Any]]] = None
) -> PhaseAgentsEvent:
    """创建阶段智能体列表事件"""
    return PhaseAgentsEvent(
        task_id=task_id,
        phase=phase,
        phase_name=phase_name,
        execution_mode=execution_mode,
        max_concurrency=max_concurrency,
        concurrent_group=concurrent_group,
        agents=agents or []
    )


def create_concurrent_group_started_event(
    task_id: str,
    group_id: str,
    phase: int,
    agents: List[str],
    max_concurrency: int,
    estimated_duration_sec: int = 0
) -> ConcurrentGroupStartedEvent:
    """创建并发组开始事件"""
    return ConcurrentGroupStartedEvent(
        task_id=task_id,
        group_id=group_id,
        phase=phase,
        agents=agents,
        max_concurrency=max_concurrency,
        estimated_duration_sec=estimated_duration_sec
    )


def create_concurrent_group_completed_event(
    task_id: str,
    group_id: str,
    phase: int,
    total_agents: int
) -> ConcurrentGroupCompletedEvent:
    """创建并发组完成事件"""
    return ConcurrentGroupCompletedEvent(
        task_id=task_id,
        group_id=group_id,
        phase=phase,
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


def create_agent_message_event(
    task_id: str,
    agent_slug: str,
    agent_name: str,
    message_type: str = "thinking",
    content: str = "",
    metadata: Optional[Dict[str, Any]] = None
) -> AgentMessageEvent:
    """创建智能体消息事件（思考过程）"""
    return AgentMessageEvent(
        task_id=task_id,
        agent_slug=agent_slug,
        agent_name=agent_name,
        message_type=message_type,
        content=content,
        metadata=metadata or {}
    )


def create_tool_called_event(
    task_id: str,
    agent_slug: str,
    tool_name: str,
    tool_input: str,
    agent_name: str = "",
) -> ToolCalledEvent:
    """创建工具调用事件"""
    return ToolCalledEvent(
        task_id=task_id,
        agent_slug=agent_slug,
        agent_name=agent_name or agent_slug,
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
