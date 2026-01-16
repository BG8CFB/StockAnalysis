"""
MCP 连接池子模块

提供任务级长连接管理和统一并发控制。
"""

from .connection import ConnectionState, MCPConnection
from .pool import MCPConnectionPool

__all__ = [
    "MCPConnectionPool",
    "MCPConnection",
    "ConnectionState",
]
