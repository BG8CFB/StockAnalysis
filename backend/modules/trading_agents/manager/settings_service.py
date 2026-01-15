"""
TradingAgents 用户设置服务

管理用户的 TradingAgents 模块配置设置，包括：
- AI 模型配置（数据收集模型、辩论模型）
- 辩论配置（默认轮次、最大轮次）
- 超时配置
- 其他配置（任务过期、归档等）
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.schemas import (
    TradingAgentsSettings,
    TradingAgentsSettingsResponse,
)

logger = logging.getLogger(__name__)


class TradingAgentsSettingsService:
    """TradingAgents 设置服务"""

    COLLECTION_NAME = "trading_agents_settings"

    def __init__(self):
        """初始化服务"""
        self._db = None

    def _get_collection(self):
        """获取数据库集合"""
        return mongodb.get_collection(self.COLLECTION_NAME)

    async def get_user_settings(self, user_id: str) -> Optional[TradingAgentsSettingsResponse]:
        """
        获取用户设置

        Args:
            user_id: 用户 ID

        Returns:
            用户设置或 None
        """
        collection = self._get_collection()

        doc = await collection.find_one({"user_id": user_id})

        if not doc:
            logger.debug(f"用户设置不存在: user_id={user_id}")
            return None

        logger.debug(f"获取用户设置: user_id={user_id}")
        return TradingAgentsSettingsResponse.from_db(doc)

    async def update_user_settings(
        self,
        user_id: str,
        settings: TradingAgentsSettings,
    ) -> TradingAgentsSettingsResponse:
        """
        更新用户设置

        Args:
            user_id: 用户 ID
            settings: 设置数据

        Returns:
            更新后的设置
        """
        collection = self._get_collection()

        # 构建更新数据
        update_data = {
            "user_id": user_id,
            "settings": settings.model_dump(),
            "updated_at": datetime.utcnow(),
        }

        # 使用 upsert：如果不存在则创建，存在则更新
        await collection.update_one(
            {"user_id": user_id},
            {"$set": update_data, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True
        )

        logger.info(f"更新用户设置: user_id={user_id}")

        # 返回更新后的设置
        return await self.get_user_settings(user_id)

    async def delete_user_settings(self, user_id: str) -> bool:
        """
        删除用户设置

        Args:
            user_id: 用户 ID

        Returns:
            是否删除成功
        """
        collection = self._get_collection()

        result = await collection.delete_one({"user_id": user_id})

        if result.deleted_count > 0:
            logger.info(f"删除用户设置: user_id={user_id}")
            return True

        return False

    async def ensure_index(self):
        """确保索引存在"""
        collection = self._get_collection()

        # 为 user_id 创建索引
        await collection.create_index([("user_id", 1)], unique=True)

        logger.info("trading_agents_settings 集合索引已创建")


# =============================================================================
# 全局服务实例
# =============================================================================

_settings_service: Optional[TradingAgentsSettingsService] = None


def get_trading_agents_settings_service() -> TradingAgentsSettingsService:
    """获取全局 TradingAgents 设置服务实例"""
    global _settings_service
    if _settings_service is None:
        _settings_service = TradingAgentsSettingsService()
    return _settings_service
