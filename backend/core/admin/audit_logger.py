"""
审计日志服务

提供统一的审计日志记录功能。
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from core.db.mongodb import mongodb
from core.admin.audit_models import AuditLogCreate, AUDIT_ACTIONS

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志记录器"""

    @staticmethod
    async def log(
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        记录审计日志

        Args:
            user_id: 用户 ID
            action: 操作类型（参考 AUDIT_ACTIONS）
            resource_type: 资源类型（如 "ai_model", "mcp_server"）
            resource_id: 资源 ID
            details: 详细信息
            ip_address: IP 地址
            user_agent: 用户代理
        """
        try:
            db = mongodb.database
            log_doc = {
                "user_id": ObjectId(user_id),
                "action": action,
                "action_name": AUDIT_ACTIONS.get(action, action),
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow(),
            }

            await db.audit_logs.insert_one(log_doc)

            # 敏感操作记录到文件日志
            if action in [
                "ai_model_access",
                "ai_model_delete",
                "mcp_server_delete",
                "password_reset",
                "role_change",
            ]:
                logger.warning(
                    f"敏感操作: user={user_id}, action={action}, "
                    f"resource={resource_type}:{resource_id}"
                )

        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")

    @staticmethod
    async def log_ai_model_access(
        user_id: str,
        model_id: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """记录 AI 模型访问"""
        await AuditLogger.log(
            user_id=user_id,
            action="ai_model_access",
            resource_type="ai_model",
            resource_id=model_id,
            ip_address=ip_address,
        )

    @staticmethod
    async def log_settings_import(
        user_id: str,
        version: str,
        strategy: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """记录配置导入"""
        await AuditLogger.log(
            user_id=user_id,
            action="settings_import",
            resource_type="user_settings",
            details={"version": version, "strategy": strategy},
            ip_address=ip_address,
        )

    @staticmethod
    async def log_task_quota_exceeded(
        user_id: str,
        quota_type: str,
        limit: int,
        ip_address: Optional[str] = None,
    ) -> None:
        """记录配额超限"""
        await AuditLogger.log(
            user_id=user_id,
            action="task_quota_exceeded",
            resource_type="quota",
            details={"quota_type": quota_type, "limit": limit},
            ip_address=ip_address,
        )


# =============================================================================
# 全局审计日志记录器实例
# =============================================================================

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志记录器实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
