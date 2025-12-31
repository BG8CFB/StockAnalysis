"""
用户配置数据库索引初始化
"""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)


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
