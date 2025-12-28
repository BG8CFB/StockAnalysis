"""
智能体配置管理服务

提供用户智能体配置的 CRUD、初始化和重置功能。
支持公共配置和个人配置的管理。
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

PUBLIC_USER_ID = "system_public"


class AgentConfigService:
    """
    智能体配置管理服务

    提供配置的创建、更新、查询和重置功能。
    支持公共配置（模板）和个人配置的管理。
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
    # 公共配置管理（管理员）
    # ========================================================================

    async def get_public_config(self) -> Optional[UserAgentConfigResponse]:
        """
        获取公共配置（模板）

        Returns:
            公共配置或 None
        """
        collection = self._get_collection()

        doc = await collection.find_one({
            "user_id": PUBLIC_USER_ID,
            "is_public": True
        })

        if not doc:
            return None

        return UserAgentConfigResponse.from_db(doc)

    async def update_public_config(
        self,
        request: UserAgentConfigUpdate,
        admin_id: str
    ) -> Optional[UserAgentConfigResponse]:
        """
        更新公共配置（仅管理员）

        Args:
            request: 更新请求
            admin_id: 管理员 ID

        Returns:
            更新后的公共配置
        """
        collection = self._get_collection()

        # 检查公共配置是否存在
        doc = await collection.find_one({
            "user_id": PUBLIC_USER_ID,
            "is_public": True
        })

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

        if doc:
            # 更新现有公共配置
            await collection.update_one(
                {"user_id": PUBLIC_USER_ID, "is_public": True},
                {"$set": update_data}
            )
            updated_doc = await collection.find_one({
                "user_id": PUBLIC_USER_ID,
                "is_public": True
            })
            logger.info(f"更新公共智能体配置: admin_id={admin_id}")
            return UserAgentConfigResponse.from_db(updated_doc)
        else:
            # 创建公共配置
            return await self._init_public_config(request)

    async def restore_public_config(self) -> Optional[UserAgentConfigResponse]:
        """
        恢复公共配置为默认值（从YAML重新导入）

        管理员在配置被改乱时使用此功能。
        YAML文件作为系统出厂设置备份，只在系统启动时和恢复时使用。

        Returns:
            恢复后的公共配置
        """
        logger.info("开始恢复公共配置为默认值")

        # 1. 删除现有公共配置
        collection = self._get_collection()
        delete_result = await collection.delete_one({
            "user_id": PUBLIC_USER_ID,
            "is_public": True
        })

        if delete_result.deleted_count > 0:
            logger.info(f"已删除旧的公共配置（删除 {delete_result.deleted_count} 条）")
        else:
            logger.warning("未找到现有公共配置，将创建新的")

        # 2. 从YAML重新导入
        try:
            default_config = self._config_loader.load_default_config()
            logger.info("YAML模板加载成功")
        except Exception as e:
            logger.error(f"加载YAML模板失败: {e}")
            raise Exception(f"恢复默认配置失败：{e}")

        # 3. 创建新的公共配置（不含model_id）
        phase1 = Phase1Config(**default_config.get("phase1", {}))

        if default_config.get("phase2"):
            phase2 = Phase2Config(**default_config["phase2"])
        else:
            phase2 = None

        if default_config.get("phase3"):
            phase3 = Phase3Config(**default_config["phase3"])
        else:
            phase3 = None

        if default_config.get("phase4"):
            phase4 = Phase4Config(**default_config["phase4"])
        else:
            phase4 = None

        # 4. 插入新配置
        doc = {
            "user_id": PUBLIC_USER_ID,
            "is_public": True,
            "is_customized": False,
            "phase1": phase1.model_dump(),
            "phase2": phase2.model_dump() if phase2 else None,
            "phase3": phase3.model_dump() if phase3 else None,
            "phase4": phase4.model_dump() if phase4 else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info("公共配置已恢复为默认值")

        return UserAgentConfigResponse.from_db(doc)

    async def _init_public_config(
        self,
        request: Optional[UserAgentConfigUpdate] = None
    ) -> Optional[UserAgentConfigResponse]:
        """
        初始化公共配置

        Args:
            request: 可选的初始配置

        Returns:
            创建的公共配置
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
            "user_id": PUBLIC_USER_ID,
            "is_public": True,
            "is_customized": False,
            "phase1": phase1.model_dump(),
            "phase2": phase2.model_dump() if phase2 else None,
            "phase3": phase3.model_dump() if phase3 else None,
            "phase4": phase4.model_dump() if phase4 else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(f"初始化公共智能体配置")

        return UserAgentConfigResponse.from_db(doc)

    # ========================================================================
    # 用户配置管理
    # ========================================================================

    async def get_effective_config(
        self,
        user_id: str,
        include_prompts: bool = False
    ) -> Optional[UserAgentConfigResponse]:
        """
        获取用户的生效配置

        逻辑：
        1. 如果用户未自定义过配置 → 返回公共配置
        2. 如果用户已自定义 → 返回个人配置
        3. 如果都没有 → 创建用户配置并返回

        Args:
            user_id: 用户 ID
            include_prompts: 是否包含提示词（role_definition）
                - True: 返回完整配置（包含 role_definition）
                - False: 返回精简配置（不包含 role_definition）

        Returns:
            生效配置
        """
        collection = self._get_collection()

        # 查询用户个人配置
        user_doc = await collection.find_one({"user_id": user_id})

        # 如果用户有个人配置且已自定义，返回个人配置
        if user_doc and user_doc.get("is_customized", False):
            logger.debug(f"用户使用个人配置: user_id={user_id}, include_prompts={include_prompts}")
            return self._build_response(user_doc, include_prompts)

        # 否则返回公共配置
        public_doc = await collection.find_one({
            "user_id": PUBLIC_USER_ID,
            "is_public": True
        })

        if public_doc:
            logger.debug(f"用户使用公共配置: user_id={user_id}, include_prompts={include_prompts}")
            return self._build_response(public_doc, include_prompts)

        # 公共配置不存在，创建它
        await self._init_public_config()
        public_doc = await collection.find_one({
            "user_id": PUBLIC_USER_ID,
            "is_public": True
        })

        if public_doc:
            return self._build_response(public_doc, include_prompts)

        return None

    def _build_response(
        self,
        doc: Dict[str, Any],
        include_prompts: bool = False
    ) -> UserAgentConfigResponse:
        """
        构建配置响应对象

        Args:
            doc: 数据库文档
            include_prompts: 是否包含提示词

        Returns:
            配置响应对象
        """
        # 如果需要包含提示词，使用原始的 from_db 方法
        if include_prompts:
            return UserAgentConfigResponse.from_db(doc)

        # 否则，移除 role_definition 字段
        doc_copy = dict(doc)
        for phase_key in ["phase1", "phase2", "phase3", "phase4"]:
            phase_data = doc_copy.get(phase_key)
            if phase_data and "agents" in phase_data:
                for agent in phase_data["agents"]:
                    # 移除 role_definition 字段
                    agent.pop("role_definition", None)

        return UserAgentConfigResponse.from_db(doc_copy)

    async def get_user_config(
        self,
        user_id: str,
        create_if_missing: bool = True
    ) -> Optional[UserAgentConfigResponse]:
        """
        获取用户个人配置（不考虑公共配置）

        Args:
            user_id: 用户 ID
            create_if_missing: 配置不存在时是否创建默认配置

        Returns:
            用户个人配置或 None
        """
        collection = self._get_collection()

        doc = await collection.find_one({"user_id": user_id})

        if not doc:
            if create_if_missing:
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

        更新时会标记为已自定义。

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
            # 创建新配置，直接标记为已自定义
            return await self._init_user_config(user_id, request, is_customized=True)

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

        # 标记为已自定义
        update_data["is_customized"] = True
        update_data["updated_at"] = datetime.utcnow()

        # 执行更新
        await collection.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )

        # 获取更新后的配置
        updated_doc = await collection.find_one({"user_id": user_id})

        logger.info(f"更新用户智能体配置: user_id={user_id}, is_customized=True")

        return UserAgentConfigResponse.from_db(updated_doc)

    async def reset_to_public_config(
        self,
        user_id: str
    ) -> Optional[UserAgentConfigResponse]:
        """
        重置用户配置为公共配置

        删除个人配置，下次访问时使用公共配置。

        Args:
            user_id: 用户 ID

        Returns:
            重置后的配置（即公共配置）
        """
        collection = self._get_collection()

        # 删除用户的个人配置
        await collection.delete_many({"user_id": user_id})

        logger.info(f"重置用户配置为公共配置: user_id={user_id}")

        # 返回公共配置
        return await self.get_public_config()

    async def reset_to_default(
        self,
        user_id: str
    ) -> Optional[UserAgentConfigResponse]:
        """
        重置为默认配置（兼容旧接口）

        Args:
            user_id: 用户 ID

        Returns:
            重置后的配置
        """
        return await self.reset_to_public_config(user_id)

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
        config = await self.get_effective_config(user_id)
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
            "is_public": False,
            "is_customized": True,
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
        request: Optional[UserAgentConfigUpdate] = None,
        is_customized: bool = False
    ) -> Optional[UserAgentConfigResponse]:
        """
        初始化用户配置

        Args:
            user_id: 用户 ID
            request: 可选的初始配置
            is_customized: 是否标记为已自定义

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
            "is_public": False,
            "is_customized": is_customized,
            "phase1": phase1.model_dump(),
            "phase2": phase2.model_dump() if phase2 else None,
            "phase3": phase3.model_dump() if phase3 else None,
            "phase4": phase4.model_dump() if phase4 else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(f"初始化用户智能体配置: user_id={user_id}, is_customized={is_customized}")

        return UserAgentConfigResponse.from_db(doc)

    async def ensure_public_config_exists(self):
        """
        确保公共配置存在
        如果不存在，则从默认配置创建
        """
        collection = self._get_collection()

        public_config = await collection.find_one({
            "user_id": PUBLIC_USER_ID,
            "is_public": True
        })

        if not public_config:
            await self._init_public_config()
            logger.info("公共配置已初始化")


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
