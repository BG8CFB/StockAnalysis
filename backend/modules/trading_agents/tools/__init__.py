"""
工具管理模块

包含 MCP 适配器、本地工具适配器、循环检测器等。
"""

# Local Tools (LangChain adapter)
from .local_tools_adapter import (
    LocalToolsManager,
    create_local_tools,
    GetStockQuotesTool,
    GetStockInfoTool,
    GetStockListTool,
)

# Loop detector
from .loop_detector import (
    ToolLoopDetector,
    LoopDetectionResult,
    get_loop_detector,
    reset_loop_detector,
    DEFAULT_LOOP_THRESHOLD,
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
