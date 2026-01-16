"""
统一用户配置管理服务

提供用户配置的 CRUD、导入导出、配额管理等功能。
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId, json_util

from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import settings
from core.db.mongodb import mongodb
from core.db.redis import UserRedisKey, get_redis
from core.settings.models.user import (
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
                # 使用 from_db 方法清理可能的无效数据
                return UserSettingsResponse.from_db(data)
            except Exception as e:
                logger.warning(f"解析缓存的用户配置失败: {e}")

        # 从数据库获取
        collection = self.db.user_settings
        doc = await collection.find_one({"user_id": ObjectId(user_id)})

        if not doc:
            if create_if_missing:
                return await self._create_default_settings(user_id)
            return None

        # 缓存到 Redis（直接序列化原始文档，保留 _id 字段）
        response = UserSettingsResponse.from_db(doc)
        # 使用 bson.json_util 序列化，确保 ObjectId 等类型正确转换
        await redis.set(
            cache_key,
            json.dumps(doc, default=json_util.default),
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
        logger.info(f"[配额检查] user_id={user_id}, quota={quota}")

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
        logger.info(f"[配额检查] 并发检查: {quota.concurrent_tasks} >= {quota.concurrent_limit} = {quota.concurrent_tasks >= quota.concurrent_limit}")
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
        """
        增加任务使用计数

        确保 quota_info 记录存在，如果不存在则使用 upsert 创建默认值
        """
        collection = self.db.user_settings

        # 使用 update_one with upsert 确保配额记录存在
        result = await collection.update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$inc": {
                    "quota_info.tasks_used": 1,
                    "quota_info.concurrent_tasks": 1
                },
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=False  # 配额记录应该在用户注册时创建
        )

        # 如果没有匹配到文档，说明用户配额记录不存在
        if result.matched_count == 0:
            logger.warning(f"用户配额记录不存在，创建默认配额: user_id={user_id}")
            # 创建默认配额记录
            await collection.update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        "quota_info.tasks_used": 1,
                        "quota_info.concurrent_tasks": 1,
                        "quota_info.tasks_limit": 100,
                        "quota_info.reports_count": 0,
                        "quota_info.reports_limit": 1000,
                        "quota_info.storage_used_mb": 0.0,
                        "quota_info.storage_limit_mb": 500,
                        "quota_info.concurrent_limit": 5,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )

        # 清除缓存
        redis = await get_redis()
        await redis.delete(UserRedisKey.preferences(user_id))

    async def decrement_concurrent_tasks(self, user_id: str) -> None:
        """
        减少并发任务计数

        使用聚合管道确保 concurrent_tasks 不会小于 0：
        1. 先获取当前值
        2. 如果值 > 0 才减少
        3. 防止因为回滚操作多次调用导致负数
        """
        collection = self.db.user_settings

        # 使用聚合管道确保不会变成负数
        # 先用 $max 确保 concurrent_tasks >= 1，然后再 -1
        # 如果 concurrent_tasks 已经是 0，$max 会保持为 0，-1 后变成 -1（仍然有问题）
        # 正确的做法：先判断是否 > 0

        # 方案：先获取当前值，只有当值 > 0 时才减少
        user_doc = await collection.find_one(
            {"user_id": ObjectId(user_id)},
            {"quota_info.concurrent_tasks": 1}
        )

        if user_doc:
            current_concurrent = user_doc.get("quota_info", {}).get("concurrent_tasks", 0)
            if current_concurrent > 0:
                # 只有当前值大于 0 时才减少
                await collection.update_one(
                    {"user_id": ObjectId(user_id)},
                    {
                        "$inc": {"quota_info.concurrent_tasks": -1},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
            else:
                # 当前值已经是 0，不执行减少操作
                logger.debug(f"concurrent_tasks 已经是 0，跳过减少: user_id={user_id}")
        else:
            logger.warning(f"用户配额记录不存在，跳过减少并发计数: user_id={user_id}")

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
# 数据库索引初始化（从 settings_database.py 合并）
# =============================================================================

async def init_user_settings_indexes() -> None:
    """初始化用户配置集合的数据库索引"""
    db: AsyncIOMotorDatabase = mongodb.database

    # ========================================
    # 用户配置集合
    # ========================================
    try:
        await db.user_settings.create_index("user_id", name="idx_user_id", unique=True)
    except Exception as e:
        if "duplicate key error" in str(e) or "E11000" in str(e):
            logger.warning(f"user_settings 索引已存在或存在重复数据，跳过创建: {e}")
        else:
            raise
    await db.user_settings.create_index("created_at", name="idx_created_at")
    await db.user_settings.create_index("updated_at", name="idx_updated_at")

    # 配额信息索引（用于配额查询）
    await db.user_settings.create_index("quota_info.tasks_used", name="idx_tasks_used")
    await db.user_settings.create_index("quota_info.storage_used_mb", name="idx_storage_used")

    logger.info("用户配置索引初始化成功")


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
