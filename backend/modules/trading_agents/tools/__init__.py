"""
工具管理模块

包含工具注册表、MCP适配器、循环检测器等。
"""

from .registry import (
    ToolRegistry,
    ToolStatus,
    ToolDefinition,
    tool_registry,
    get_tool_registry,
    local_tool,
)
from .loop_detector import (
    ToolLoopDetector,
    CallRecord,
    loop_detector,
    get_loop_detector,
    check_tool_loop,
    clear_agent_history,
)
from .local_tools import (
    LocalTool,
    LocalToolExecutor,
    ExampleLocalTool,
    local_tool_executor,
    get_local_tool_executor,
)

__all__ = [
    # Registry
    "ToolRegistry",
    "ToolStatus",
    "ToolDefinition",
    "tool_registry",
    "get_tool_registry",
    "local_tool",
    # Loop Detector
    "ToolLoopDetector",
    "CallRecord",
    "loop_detector",
    "get_loop_detector",
    "check_tool_loop",
    "clear_agent_history",
    # Local Tools
    "LocalTool",
    "LocalToolExecutor",
    "ExampleLocalTool",
    "local_tool_executor",
    "get_local_tool_executor",
]
