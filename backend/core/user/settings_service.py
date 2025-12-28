"""
统一用户配置管理服务

提供用户配置的 CRUD、导入导出、配额管理等功能。
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import settings
from core.db.mongodb import mongodb
from core.db.redis import UserRedisKey, get_redis
from core.user.settings_models import (
    UserSettings,
    CoreSettings,
    NotificationSettings,
    TradingAgentsSettings,
    UserQuotaInfo,
    CoreSettingsUpdate,
    NotificationSettingsUpdate,
    TradingAgentsSettingsUpdate,
    UserSettingsResponse,
    SettingsExport,
    SettingsImport,
)
from core.admin.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)


class UserSettingsService:
    """统一用户配置管理服务"""

    def __init__(self):
        """初始化服务"""
        self._cache_ttl = 3600  # 缓存1小时

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """获取数据库实例"""
        return mongodb.database

    # ========================================================================
    # 配置获取与创建
    # ========================================================================

    async def get_user_settings(
        self,
        user_id: str,
        create_if_missing: bool = True
    ) -> Optional[UserSettingsResponse]:
        """
        获取用户配置

        Args:
            user_id: 用户 ID
            create_if_missing: 配置不存在时是否创建默认配置

        Returns:
            用户配置或 None
        """
        # 先从 Redis 缓存获取
        redis = await get_redis()
        cache_key = UserRedisKey.preferences(user_id)
        cached = await redis.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return UserSettingsResponse(**data)
            except Exception as e:
                logger.warning(f"解析缓存的用户配置失败: {e}")

        # 从数据库获取
        collection = self.db.user_settings
        doc = await collection.find_one({"user_id": ObjectId(user_id)})

        if not doc:
            if create_if_missing:
                return await self._create_default_settings(user_id)
            return None

        # 缓存到 Redis
        response = UserSettingsResponse.from_db(doc)
        await redis.set(
            cache_key,
            response.model_dump_json(),
            ex=self._cache_ttl
        )

        return response

    async def _create_default_settings(
        self,
        user_id: str
    ) -> Optional[UserSettingsResponse]:
        """
        创建默认用户配置

        Args:
            user_id: 用户 ID

        Returns:
            创建的配置
        """
        # 尝试从旧的 user_preferences 迁移数据
        old_prefs = await self._migrate_from_old_preferences(user_id)

        # 创建默认配置
        default_settings = UserSettings(
            user_id=ObjectId(user_id),
            core_settings=CoreSettings(**old_prefs.get("core", {})),
            notification_settings=NotificationSettings(**old_prefs.get("notification", {})),
            trading_agents_settings=TradingAgentsSettings(),
            quota_info=UserQuotaInfo(),
        )

        # 插入数据库
        collection = self.db.user_settings
        doc = default_settings.model_dump()
        # 确保 user_id 以 ObjectId 形式存储
        if isinstance(doc.get("user_id"), str):
            doc["user_id"] = ObjectId(doc["user_id"])
            
        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(f"创建默认用户配置: user_id={user_id}")

        return UserSettingsResponse.from_db(doc)

    async def _migrate_from_old_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        从旧的 user_preferences 迁移数据

        Args:
            user_id: 用户 ID

        Returns:
            迁移的数据
        """
        migrated = {"core": {}, "notification": {}}

        try:
            # 从旧表读取
            old_prefs = await self.db.user_preferences.find_one({
                "user_id": ObjectId(user_id)
            })

            if old_prefs:
                # 迁移核心设置
                if "theme" in old_prefs:
                    migrated["core"]["theme"] = old_prefs["theme"]
                if "language" in old_prefs:
                    migrated["core"]["language"] = old_prefs["language"]
                if "timezone" in old_prefs:
                    migrated["core"]["timezone"] = old_prefs["timezone"]
                if "watchlist" in old_prefs:
                    migrated["core"]["watchlist"] = old_prefs["watchlist"]

                # 迁移通知设置
                if "notification_enabled" in old_prefs:
                    migrated["notification"]["enabled"] = old_prefs["notification_enabled"]
                if "email_alerts" in old_prefs:
                    migrated["notification"]["email_alerts"] = old_prefs["email_alerts"]

                logger.info(f"迁移旧用户配置: user_id={user_id}, fields={len(migrated)}")

        except Exception as e:
            logger.warning(f"迁移旧用户配置失败: {e}")

        return migrated

    # ========================================================================
    # 配置更新
    # ========================================================================

    async def update_core_settings(
        self,
        user_id: str,
        request: CoreSettingsUpdate
    ) -> Optional[UserSettingsResponse]:
        """更新核心设置"""
        return await self._update_settings(user_id, {
            "core_settings": request.model_dump(exclude_unset=True)
        })

    async def update_notification_settings(
        self,
        user_id: str,
        request: NotificationSettingsUpdate
    ) -> Optional[UserSettingsResponse]:
        """更新通知设置"""
        return await self._update_settings(user_id, {
            "notification_settings": request.model_dump(exclude_unset=True)
        })

    async def update_trading_agents_settings(
        self,
        user_id: str,
        request: TradingAgentsSettingsUpdate
    ) -> Optional[UserSettingsResponse]:
        """更新 TradingAgents 设置"""
        return await self._update_settings(user_id, {
            "trading_agents_settings": request.model_dump(exclude_unset=True)
        })

    async def _update_settings(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[UserSettingsResponse]:
        """
        内部更新方法

        Args:
            user_id: 用户 ID
            update_data: 更新数据

        Returns:
            更新后的配置
        """
        collection = self.db.user_settings

        # 构建更新字段（使用 $set 更新嵌套字段）
        set_fields = {"updated_at": datetime.utcnow()}

        for key, value in update_data.items():
            if value:  # 跳过空字典
                for field, field_value in value.items():
                    set_fields[f"{key}.{field}"] = field_value

        # 更新数据库
        await collection.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": set_fields}
        )

        # 清除缓存
        redis = await get_redis()
        cache_key = UserRedisKey.preferences(user_id)
        await redis.delete(cache_key)

        # 返回更新后的配置
        return await self.get_user_settings(user_id)

    # ========================================================================
    # 配额管理
    # ========================================================================

    async def get_quota_info(self, user_id: str) -> Optional[UserQuotaInfo]:
        """获取用户配额信息"""
        settings = await self.get_user_settings(user_id)
        if not settings:
            return None
        return settings.quota_info

    async def check_task_quota(self, user_id: str) -> tuple[bool, str]:
        """
        检查任务配额

        Returns:
            (是否允许创建, 错误消息)
        """
        quota = await self.get_quota_info(user_id)
        if not quota:
            return True, ""

        # 检查任务限制
        if quota.tasks_used >= quota.tasks_limit:
            # 记录配额超限审计日志
            audit_logger = get_audit_logger()
            await audit_logger.log_task_quota_exceeded(
                user_id=user_id,
                quota_type="monthly_tasks",
                limit=quota.tasks_limit,
            )
            return False, f"已达到本月任务限制（{quota.tasks_limit}）"

        # 检查并发限制
        if quota.concurrent_tasks >= quota.concurrent_limit:
            # 记录配额超限审计日志
            audit_logger = get_audit_logger()
            await audit_logger.log_task_quota_exceeded(
                user_id=user_id,
                quota_type="concurrent_tasks",
                limit=quota.concurrent_limit,
            )
            return False, f"已达到并发任务限制（{quota.concurrent_limit}）"

        return True, ""

    async def increment_task_usage(self, user_id: str) -> None:
        """增加任务使用计数"""
        collection = self.db.user_settings

        await collection.update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$inc": {
                    "quota_info.tasks_used": 1,
                    "quota_info.concurrent_tasks": 1
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        # 清除缓存
        redis = await get_redis()
        await redis.delete(UserRedisKey.preferences(user_id))

    async def decrement_concurrent_tasks(self, user_id: str) -> None:
        """减少并发任务计数"""
        collection = self.db.user_settings

        await collection.update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$inc": {"quota_info.concurrent_tasks": -1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        # 清除缓存
        redis = await get_redis()
        await redis.delete(UserRedisKey.preferences(user_id))

    async def update_storage_usage(
        self,
        user_id: str,
        size_mb: float
    ) -> None:
        """
        更新存储使用量

        Args:
            user_id: 用户 ID
            size_mb: 增加的存储大小（MB），负数表示减少
        """
        collection = self.db.user_settings

        await collection.update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$inc": {"quota_info.storage_used_mb": size_mb},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        # 清除缓存
        redis = await get_redis()
        await redis.delete(UserRedisKey.preferences(user_id))

    # ========================================================================
    # 配置导入导出
    # ========================================================================

    async def export_settings(self, user_id: str) -> SettingsExport:
        """
        导出用户配置（不包含敏感信息和配额信息）

        Args:
            user_id: 用户 ID

        Returns:
            导出的配置
        """
        settings = await self.get_user_settings(user_id)
        if not settings:
            raise ValueError(f"用户配置不存在: {user_id}")

        return SettingsExport(
            version="1.0",
            exported_at=datetime.utcnow(),
            core_settings=settings.core_settings,
            notification_settings=settings.notification_settings,
            trading_agents_settings=settings.trading_agents_settings,
        )

    async def import_settings(
        self,
        user_id: str,
        import_data: SettingsImport
    ) -> UserSettingsResponse:
        """
        导入用户配置

        Args:
            user_id: 用户 ID
            import_data: 导入的配置数据

        Returns:
            导入后的配置
        """
        collection = self.db.user_settings

        if import_data.merge_strategy == "replace":
            # 完全覆盖模式：直接替换所有配置
            update_doc = {
                "updated_at": datetime.utcnow()
            }

            if import_data.core_settings:
                update_doc["core_settings"] = import_data.core_settings.model_dump()
            if import_data.notification_settings:
                update_doc["notification_settings"] = import_data.notification_settings.model_dump()
            if import_data.trading_agents_settings:
                update_doc["trading_agents_settings"] = import_data.trading_agents_settings.model_dump()

            await collection.update_one(
                {"user_id": ObjectId(user_id)},
                {"$set": update_doc},
                upsert=True
            )

        else:
            # 合并模式：只更新提供的字段
            set_fields = {"updated_at": datetime.utcnow()}

            if import_data.core_settings:
                for key, value in import_data.core_settings.model_dump(exclude_unset=True).items():
                    set_fields[f"core_settings.{key}"] = value

            if import_data.notification_settings:
                for key, value in import_data.notification_settings.model_dump(exclude_unset=True).items():
                    set_fields[f"notification_settings.{key}"] = value

            if import_data.trading_agents_settings:
                for key, value in import_data.trading_agents_settings.model_dump(exclude_unset=True).items():
                    set_fields[f"trading_agents_settings.{key}"] = value

            await collection.update_one(
                {"user_id": ObjectId(user_id)},
                {"$set": set_fields}
            )

        # 清除缓存
        redis = await get_redis()
        await redis.delete(UserRedisKey.preferences(user_id))

        # 记录审计日志
        audit_logger = get_audit_logger()
        await audit_logger.log_settings_import(
            user_id=user_id,
            version=import_data.version,
            strategy=import_data.merge_strategy,
        )

        logger.info(f"导入用户配置: user_id={user_id}, strategy={import_data.merge_strategy}")

        return await self.get_user_settings(user_id)


# =============================================================================
# 全局服务实例
# =============================================================================

_user_settings_service: Optional[UserSettingsService] = None


def get_user_settings_service() -> UserSettingsService:
    """获取全局用户配置服务实例"""
    global _user_settings_service
    if _user_settings_service is None:
        _user_settings_service = UserSettingsService()
    return _user_settings_service
