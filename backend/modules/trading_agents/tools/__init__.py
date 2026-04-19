"""
工具管理模块

包含 MCP 适配器、本地工具适配器、循环检测器等。
"""

# Local Tools (LangChain adapter)
from .local_tools_adapter import (
    GetStockInfoTool,
    GetStockListTool,
    GetStockQuotesTool,
    LocalToolsManager,
    create_local_tools,
)

# Loop detector
from .loop_detector import (
    DEFAULT_LOOP_THRESHOLD,
    LoopDetectionResult,
    ToolLoopDetector,
    get_loop_detector,
    reset_loop_detector,
)

__all__ = [
    # Local Tools (LangChain adapter)
    "LocalToolsManager",
    "create_local_tools",
    "GetStockQuotesTool",
    "GetStockInfoTool",
    "GetStockListTool",
    # Loop detector
    "ToolLoopDetector",
    "LoopDetectionResult",
    "get_loop_detector",
    "reset_loop_detector",
    "DEFAULT_LOOP_THRESHOLD",
]
