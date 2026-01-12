"""
实时通信模块

包含 WebSocket 管理器和事件定义。
"""

from .manager import (
    WebSocketManager,
    websocket_manager,
    get_websocket_manager,
    get_ws_manager,
)
from .events import (
    EventType,
    TaskEvent,
    PhaseStartedEvent,
    AgentStartedEvent,
    AgentCompletedEvent,
    AgentMessageEvent,
    ToolCalledEvent,
    ToolResultEvent,
    ToolDisabledEvent,
    ReportGeneratedEvent,
    ReportStreamChunkEvent,
    ProgressUpdateEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    create_event,
    create_phase_started_event,
    create_agent_started_event,
    create_agent_completed_event,
    create_agent_message_event,
    create_tool_called_event,
    create_tool_result_event,
    create_report_generated_event,
    create_task_completed_event,
    create_task_failed_event,
)

__all__ = [
    # Manager
    "WebSocketManager",
    "websocket_manager",
    "get_websocket_manager",
    "get_ws_manager",
    # Event Types
    "EventType",
    # Event Classes
    "TaskEvent",
    "PhaseStartedEvent",
    "AgentStartedEvent",
    "AgentCompletedEvent",
    "AgentMessageEvent",
    "ToolCalledEvent",
    "ToolResultEvent",
    "ToolDisabledEvent",
    "ReportGeneratedEvent",
    "ReportStreamChunkEvent",
    "ProgressUpdateEvent",
    "TaskCompletedEvent",
    "TaskFailedEvent",
    # Factory Functions
    "create_event",
    "create_phase_started_event",
    "create_agent_started_event",
    "create_agent_completed_event",
    "create_agent_message_event",
    "create_tool_called_event",
    "create_tool_result_event",
    "create_report_generated_event",
    "create_task_completed_event",
    "create_task_failed_event",
]
