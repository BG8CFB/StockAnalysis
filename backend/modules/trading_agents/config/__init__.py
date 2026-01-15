"""
配置管理模块

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15

包含智能体配置加载器和路径管理。
"""

from .loader import (
    ConfigPaths,
    AgentConfigLoader,
    get_config_loader,
    load_default_config,
    load_public_config,
    get_enabled_agents,
    get_agent_by_slug,
)

__all__ = [
    "ConfigPaths",
    "AgentConfigLoader",
    "get_config_loader",
    "load_default_config",
    "load_public_config",
    "get_enabled_agents",
    "get_agent_by_slug",
]
