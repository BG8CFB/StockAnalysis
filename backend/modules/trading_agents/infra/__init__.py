"""
TradingAgents 基础设施模块

包含数据库操作、告警机制等基础设施功能。
"""

from .database import init_indexes, get_collection_stats, drop_collections
from .alerts import AlertManager, get_alert_manager, AlertEventType, AlertSeverity

__all__ = [
    # database
    "init_indexes",
    "get_collection_stats",
    "drop_collections",
    # alerts
    "AlertManager",
    "get_alert_manager",
    "AlertEventType",
    "AlertSeverity",
]
