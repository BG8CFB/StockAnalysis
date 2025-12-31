"""
MCP 核心功能模块

提供 MCP 适配器、会话管理和自定义异常。
"""

from .adapter import (
    build_stdio_connection,
    build_sse_connection,
    build_streamable_http_connection,
    build_websocket_connection,
    get_mcp_tools,
)
from .exceptions import (
    MCPConnectionError,
    MCPTimeoutError,
    MCPProtocolError,
    MCPUnavailableError,
)

__all__ = [
    "build_stdio_connection",
    "build_sse_connection",
    "build_streamable_http_connection",
    "build_websocket_connection",
    "get_mcp_tools",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPProtocolError",
    "MCPUnavailableError",
]
