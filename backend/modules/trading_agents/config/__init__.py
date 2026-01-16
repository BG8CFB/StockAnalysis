"""
配置管理模块

**版本**: v4.0 (配置合并重构版)
**最后更新**: 2026-01-16

包含智能体配置加载器、路径管理和配置合并器。
"""

from .loader import (
    AgentConfigLoader,
    ConfigPaths,
    get_agent_by_slug,
    get_config_loader,
    get_enabled_agents,
    load_default_config,
    load_public_config,
)
from .merger import (
    ConfigMerger,
    get_config_merger,
)

__all__ = [
    "ConfigPaths",
    "AgentConfigLoader",
    "get_config_loader",
    "load_default_config",
    "load_public_config",
    "get_enabled_agents",
    "get_agent_by_slug",
    "ConfigMerger",
    "get_config_merger",
]
