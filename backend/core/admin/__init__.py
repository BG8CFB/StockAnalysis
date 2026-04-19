"""
管理员核心模块
"""

from core.admin.api import router as admin_router
from core.admin.service import AdminService, admin_service

__all__ = [
    "AdminService",
    "admin_service",
    "admin_router",
]
