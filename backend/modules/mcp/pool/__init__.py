"""
MCP 连接池子模块

提供任务级长连接管理和统一并发控制。
"""

from .pool import MCPConnectionPool
from .connection import MCPConnection, ConnectionState

__all__ = [
    "MCPConnectionPool",
    "MCPConnection",
    "ConnectionState",
]
