"""
智能体配置管理服务

提供用户智能体配置的 CRUD、初始化和重置功能。
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
import yaml

from core.db.mongodb import mongodb
from modules.trading_agents.config.loader import ConfigLoader
from modules.trading_agents.schemas import (
    UserAgentConfigCreate,
    UserAgentConfigUpdate,
    UserAgentConfigResponse,
    Phase1Config,
    Phase2Config,
    Phase3Config,
    Phase4Config,
)

logger = logging.getLogger(__name__)


class AgentConfigService:
    """
    智能体配置管理服务

    提供配置的创建、更新、查询和重置功能。
    """

    COLLECTION_NAME = "agent_configs"

    def __init__(self):
        """初始化服务"""
        self._db = None
        self._config_loader = ConfigLoader()

    def _get_collection(self):
        """获取数据库集合"""
        return mongodb.get_collection(self.COLLECTION_NAME)

    # ========================================================================
    # CRUD 操作
    # ========================================================================

    async def get_user_config(
        self,
        user_id: str,
        create_if_missing: bool = True
    ) -> Optional[UserAgentConfigResponse]:
        """
        获取用户智能体配置

        Args:
            user_id: 用户 ID
            create_if_missing: 配置不存在时是否创建默认配置

        Returns:
            用户配置或 None
        """
        collection = self._get_collection()

        doc = await collection.find_one({"user_id": user_id})

        if not doc:
            if create_if_missing:
                # 创建默认配置
                return await self._init_user_config(user_id)
            return None

        return UserAgentConfigResponse.from_db(doc)

    async def update_user_config(
        self,
        user_id: str,
        request: UserAgentConfigUpdate
    ) -> Optional[UserAgentConfigResponse]:
        """
        更新用户智能体配置

        Args:
            user_id: 用户 ID
            request: 更新请求

        Returns:
            更新后的配置或 None
        """
        collection = self._get_collection()

        # 获取原配置
        doc = await collection.find_one({"user_id": user_id})
        if not doc:
            # 创建新配置
            return await self._init_user_config(user_id, request)

        # 构建更新数据
        update_data = {}
        if request.phase1 is not None:
            update_data["phase1"] = request.phase1.model_dump()
        if request.phase2 is not None:
            update_data["phase2"] = request.phase2.model_dump()
        if request.phase3 is not None:
            update_data["phase3"] = request.phase3.model_dump()
        if request.phase4 is not None:
            update_data["phase4"] = request.phase4.model_dump()

        update_data["updated_at"] = datetime.utcnow()

        # 执行更新
        await collection.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )

        # 获取更新后的配置
        updated_doc = await collection.find_one({"user_id": user_id})

        logger.info(f"更新用户智能体配置: user_id={user_id}")

        return UserAgentConfigResponse.from_db(updated_doc)

    async def reset_to_default(
        self,
        user_id: str
    ) -> Optional[UserAgentConfigResponse]:
        """
        重置为默认配置

        Args:
            user_id: 用户 ID

        Returns:
            重置后的配置
        """
        collection = self._get_collection()

        # 删除旧配置
        await collection.delete_many({"user_id": user_id})

        # 创建新配置
        return await self._init_user_config(user_id)

    async def export_config(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        导出配置

        Args:
            user_id: 用户 ID

        Returns:
            配置数据
        """
        config = await self.get_user_config(user_id, create_if_missing=False)
        if not config:
            return None

        return {
            "phase1": config.phase1.model_dump(),
            "phase2": config.phase2.model_dump() if config.phase2 else None,
            "phase3": config.phase3.model_dump() if config.phase3 else None,
            "phase4": config.phase4.model_dump() if config.phase4 else None,
        }

    async def import_config(
        self,
        user_id: str,
        config_data: Dict[str, Any]
    ) -> Optional[UserAgentConfigResponse]:
        """
        导入配置

        Args:
            user_id: 用户 ID
            config_data: 配置数据

        Returns:
            导入后的配置
        """
        collection = self._get_collection()

        # 验证配置格式
        try:
            phase1 = Phase1Config(**config_data.get("phase1", {}))
            phase2 = Phase2Config(**config_data["phase2"]) if config_data.get("phase2") else None
            phase3 = Phase3Config(**config_data["phase3"]) if config_data.get("phase3") else None
            phase4 = Phase4Config(**config_data["phase4"]) if config_data.get("phase4") else None
        except Exception as e:
            logger.error(f"配置格式验证失败: {e}")
            raise ValueError(f"配置格式无效: {e}")

        # 创建或更新配置
        doc = {
            "user_id": user_id,
            "phase1": phase1.model_dump(),
            "phase2": phase2.model_dump() if phase2 else None,
            "phase3": phase3.model_dump() if phase3 else None,
            "phase4": phase4.model_dump() if phase4 else None,
            "updated_at": datetime.utcnow(),
        }

        # 使用 upsert
        await collection.update_one(
            {"user_id": user_id},
            {"$set": doc},
            upsert=True
        )

        # 获取导入后的配置
        imported_doc = await collection.find_one({"user_id": user_id})

        logger.info(f"导入用户智能体配置: user_id={user_id}")

        return UserAgentConfigResponse.from_db(imported_doc)

    # ========================================================================
    # 配置初始化
    # ========================================================================

    async def _init_user_config(
        self,
        user_id: str,
        request: Optional[UserAgentConfigUpdate] = None
    ) -> Optional[UserAgentConfigResponse]:
        """
        初始化用户配置

        Args:
            user_id: 用户 ID
            request: 可选的初始配置

        Returns:
            创建的配置
        """
        # 加载默认配置模板
        default_config = self._config_loader.load_default_config()

        if request and request.phase1:
            phase1 = request.phase1
        else:
            phase1 = Phase1Config(**default_config.get("phase1", {}))

        if request and request.phase2:
            phase2 = request.phase2
        elif default_config.get("phase2"):
            phase2 = Phase2Config(**default_config["phase2"])
        else:
            phase2 = None

        if request and request.phase3:
            phase3 = request.phase3
        elif default_config.get("phase3"):
            phase3 = Phase3Config(**default_config["phase3"])
        else:
            phase3 = None

        if request and request.phase4:
            phase4 = request.phase4
        elif default_config.get("phase4"):
            phase4 = Phase4Config(**default_config["phase4"])
        else:
            phase4 = None

        # 创建文档
        collection = self._get_collection()
        doc = {
            "user_id": user_id,
            "phase1": phase1.model_dump(),
            "phase2": phase2.model_dump() if phase2 else None,
            "phase3": phase3.model_dump() if phase3 else None,
            "phase4": phase4.model_dump() if phase4 else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(f"初始化用户智能体配置: user_id={user_id}")

        return UserAgentConfigResponse.from_db(doc)


# =============================================================================
# 全局服务实例
# =============================================================================

_agent_config_service: Optional[AgentConfigService] = None


def get_agent_config_service() -> AgentConfigService:
    """获取全局智能体配置服务实例"""
    global _agent_config_service
    if _agent_config_service is None:
        _agent_config_service = AgentConfigService()
    return _agent_config_service
