"""
系统设置核心服务
管理系统配置、用户偏好等
"""
import json
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import settings
from core.auth.rbac import Role
from core.db.mongodb import mongodb
from core.db.redis import get_redis, redis_manager


class SystemConfig:
    """系统配置模型"""

    # 用户审核相关
    REQUIRE_APPROVAL: bool = True  # 是否需要审核

    # 密码策略
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = False
    PASSWORD_REQUIRE_LOWERCASE: bool = False
    PASSWORD_REQUIRE_DIGIT: bool = False
    PASSWORD_REQUIRE_SPECIAL: bool = False

    # 会话配置
    SESSION_TIMEOUT: int = 1800  # 30分钟

    # 数据保留
    REJECTED_USER_RETENTION_DAYS: int = 1  # 被拒绝用户保留天数

    # 功能开关
    ENABLE_REGISTRATION: bool = True  # 是否开放注册
    ENABLE_PASSWORD_RESET: bool = True  # 是否开放密码重置


class SettingsService:
    """系统设置服务"""

    def __init__(self) -> None:
        self.startup_time = datetime.utcnow()

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """获取数据库实例"""
        return mongodb.database

    async def get_system_config(self) -> dict:
        """获取系统配置"""
        # 从 Redis 缓存获取
        redis = await get_redis()
        cache_key = "system:config"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 从数据库获取
        config_doc = await self.db.system_config.find_one({"key": "main_config"})
        if config_doc:
            config = config_doc.get("value", {})
        else:
            # 返回默认配置
            config = {
                "REQUIRE_APPROVAL": settings.REQUIRE_APPROVAL,
                "PASSWORD_MIN_LENGTH": settings.PASSWORD_MIN_LENGTH,
                "ENABLE_REGISTRATION": True,
                "ENABLE_PASSWORD_RESET": True,
                "SESSION_TIMEOUT": 1800,
                "REJECTED_USER_RETENTION_DAYS": 1,
            }

        # 缓存到 Redis
        await redis.set(cache_key, json.dumps(config, default=str), ex=3600)

        return config

    async def update_system_config(
        self,
        config_updates: dict,
        admin_id: str,
    ) -> dict:
        """更新系统配置"""
        # 获取当前配置
        current_config = await self.get_system_config()

        # 更新配置
        current_config.update(config_updates)

        # 保存到数据库
        await self.db.system_config.update_one(
            {"key": "main_config"},
            {
                "$set": {
                    "value": current_config,
                    "updated_by": admin_id,
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )

        # 清除缓存
        redis = await get_redis()
        await redis.delete("system:config")

        # 记录审计日志
        await self._create_audit_log(
            action="system_config",
            user_id=admin_id,
        )

        return await self.get_system_config()

    async def _create_audit_log(
        self,
        action: str,
        user_id: str,
        details: Optional[dict] = None,
    ) -> None:
        """创建审计日志"""
        log_doc = {
            "user_id": user_id,
            "action": action,
            "details": details,
            "created_at": datetime.utcnow(),
        }
        await self.db.audit_logs.insert_one(log_doc)

    async def get_system_info(self) -> dict:
        """获取完整系统信息"""
        # 1. 检查数据库连接状态
        try:
            # 尝试 Ping MongoDB
            await self.db.client.admin.command('ping')
            mongodb_connected = True
        except Exception:
            mongodb_connected = False

        # 尝试 Ping Redis
        redis_connected = await redis_manager.ping()

        # 2. 获取用户统计
        try:
            total_users = await self.db.users.count_documents({})
            active_users = await self.db.users.count_documents({"status": "active"})
            pending_users = await self.db.users.count_documents({"status": "pending"})
            disabled_users = await self.db.users.count_documents({"status": "disabled"})
            
            # 检查是否有管理员 (初始化状态)
            admin_count = await self.db.users.count_documents({
                "role": {"$in": [Role.ADMIN.value, Role.SUPER_ADMIN.value]}
            })
            initialized = admin_count > 0
        except Exception:
            # 数据库未连接时的默认值
            total_users = 0
            active_users = 0
            pending_users = 0
            disabled_users = 0
            initialized = False

        # 3. 获取系统配置
        config = await self.get_system_config()

        # 4. 构造符合前端 SystemInfo 接口的返回数据
        return {
            # SystemStatus 字段
            "initialized": initialized,
            "mongodb_connected": mongodb_connected,
            "redis_connected": redis_connected,
            "user_stats": {
                "total": total_users,
                "active": active_users,
                "pending": pending_users,
                "disabled": disabled_users
            },
            
            # SystemConfig 字段 (扁平化)
            "require_approval": config.get("REQUIRE_APPROVAL", True),
            "app_name": getattr(settings, "APP_NAME", "StockAnalysis"),
            "app_version": getattr(settings, "APP_VERSION", "1.0.0"),
            "debug": getattr(settings, "DEBUG", False),
            "registration_open": config.get("ENABLE_REGISTRATION", True),
            
            # 其他信息
            "server_time": datetime.utcnow().isoformat(),
            "uptime": int((datetime.utcnow() - self.startup_time).total_seconds()),
            
            # 兼容旧字段 (可选)
            "config": config,
        }


# 全局服务实例
settings_service = SettingsService()
