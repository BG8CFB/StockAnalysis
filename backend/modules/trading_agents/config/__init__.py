"""
配置管理模块

包含配置加载器和默认模板。
"""

from .loader import (
    ConfigLoader,
    config_loader,
    get_config_loader,
    load_default_config,
    get_phase1_config,
    get_phase2_config,
    get_phase3_config,
    get_phase4_config,
    validate_agent_config,
)

__all__ = [
    "ConfigLoader",
    "config_loader",
    "get_config_loader",
    "load_default_config",
    "get_phase1_config",
    "get_phase2_config",
    "get_phase3_config",
    "get_phase4_config",
    "validate_agent_config",
]
