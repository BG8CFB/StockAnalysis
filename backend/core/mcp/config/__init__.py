"""
MCP 配置模块

提供 MCP 模块的配置加载和管理功能。
"""

from .loader import get_mcp_config, load_mcp_config

__all__ = [
    "load_mcp_config",
    "get_mcp_config",
]
