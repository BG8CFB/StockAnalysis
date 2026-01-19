"""
智能体配置管理服务

提供用户智能体配置的 CRUD、初始化和重置功能。
支持公共配置和个人配置的管理。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db.mongodb import mongodb
from modules.trading_agents.config.loader import AgentConfigLoader
from modules.trading_agents.schemas import (
    Phase1Config,
    Phase2Config,
    Phase3Config,
    Phase4Config,
    UserAgentConfigResponse,
    UserAgentConfigUpdate,
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
        self._config_loader = AgentConfigLoader()

    # ========================================================================
    # 阶段配置验证
    # ========================================================================

    def _deduplicate_agents_by_slug(
        self,
        agents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根据 slug 去重智能体列表（保留第一次出现的）

        Args:
            agents: 智能体列表

        Returns:
            去重后的智能体列表
        """
        seen_slugs = set()
        deduplicated_agents = []

        for agent in agents:
            slug = agent.get("slug")
            if not slug:
                continue

            if slug not in seen_slugs:
                seen_slugs.add(slug)
                deduplicated_agents.append(agent)
            else:
                logger.warning(f"发现重复的智能体 slug: {slug}，已自动去重")

        return deduplicated_agents

    def _validate_phase_update(
        self,
        phase_key: str,
        new_phase_data,
        old_doc: dict
    ):
        """
        验证阶段配置更新

        规则：
        - phase1: 允许所有修改（添加、删除、编辑智能体）
        - phase2/3/4: 只能修改 role_definition，不能修改其他字段

        Args:
            phase_key: 阶段键 (phase1, phase2, phase3, phase4)
            new_phase_data: 新的阶段配置数据
            old_doc: 旧的数据库文档

        Raises:
            ValueError: 验证失败
        """

        # phase1 允许所有修改
        if phase_key == "phase1":
            return

        # phase2/3/4 只能修改 role_definition
        if phase_key in ["phase2", "phase3", "phase4"]:
            old_phase = old_doc.get(phase_key)
            if not old_phase:
                # 如果旧配置不存在，不允许创建新的智能体列表
                has_agents = (
                    new_phase_data and
                    hasattr(new_phase_data, 'agents') and
                    len(new_phase_data.agents) > 0
                )
                if has_agents:
                    raise ValueError(f"{phase_key} 不允许添加智能体，只能修改提示词")
                return

            old_agents = old_phase.get("agents", [])

            # 检查智能体数量是否改变
            if new_phase_data and hasattr(new_phase_data, 'agents'):
                new_agents = new_phase_data.agents or []
                if len(old_agents) != len(new_agents):
                    raise ValueError(f"{phase_key} 不允许添加或删除智能体，只能修改提示词")

                # 检查智能体 slug、name 是否改变（只允许修改 role_definition 和 enabled）
                for i, (old_agent, new_agent) in enumerate(zip(old_agents, new_agents)):
                    # 检查 slug 是否改变
                    if old_agent.get("slug") != new_agent.slug:
                        raise ValueError(f"{phase_key} 不允许修改智能体的 slug，只能修改提示词")

                    # 检查 name 是否改变
                    if old_agent.get("name") != new_agent.name:
                        raise ValueError(f"{phase_key} 不允许修改智能体的名称，只能修改提示词")

                    # 检查其他字段是否被修改
                    allowed_fields = {"slug", "name", "role_definition", "enabled"}
                    if hasattr(new_agent, 'model_dump'):
                        new_agent_dict = new_agent.model_dump(mode='json')
                    else:
                        new_agent_dict = dict(new_agent)

                    for field in new_agent_dict:
                        if field not in allowed_fields:
                            old_value = old_agent.get(field)
                            new_value = new_agent_dict[field]
                            if old_value != new_value:
                                raise ValueError(
                                    f"{phase_key} 不允许修改 {field} 字段，只能修改提示词"
                                )

        logger.debug(f"阶段配置验证通过: {phase_key}")

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

        # 如果是更新现有配置，进行验证
        if doc:
            # 验证各阶段配置更新
            for phase_key, phase_data in [
                ("phase1", request.phase1),
                ("phase2", request.phase2),
                ("phase3", request.phase3),
                ("phase4", request.phase4),
            ]:
                if phase_data is not None:
                    try:
                        self._validate_phase_update(phase_key, phase_data, doc)
                    except ValueError as e:
                        logger.warning(f"公共配置验证失败: {e}")
                        raise ValueError(str(e))

        # 构建更新数据（保留用户的选择）
        update_data = {}
        if request.phase1 is not None:
            phase1_data = request.phase1.model_dump(mode='json')
            # 去重：根据 slug 去除重复的智能体
            if "agents" in phase1_data:
                phase1_data["agents"] = self._deduplicate_agents_by_slug(phase1_data["agents"])
            update_data["phase1"] = phase1_data
        if request.phase2 is not None:
            phase2_data = request.phase2.model_dump(mode='json')
            # 去重：根据 slug 去除重复的智能体
            if "agents" in phase2_data:
                phase2_data["agents"] = self._deduplicate_agents_by_slug(phase2_data["agents"])
            update_data["phase2"] = phase2_data
        if request.phase3 is not None:
            phase3_data = request.phase3.model_dump(mode='json')
            # 去重：根据 slug 去除重复的智能体
            if "agents" in phase3_data:
                phase3_data["agents"] = self._deduplicate_agents_by_slug(phase3_data["agents"])
            update_data["phase3"] = phase3_data
        if request.phase4 is not None:
            phase4_data = request.phase4.model_dump(mode='json')
            # 去重：根据 slug 去除重复的智能体
            if "agents" in phase4_data:
                phase4_data["agents"] = self._deduplicate_agents_by_slug(phase4_data["agents"])
            update_data["phase4"] = phase4_data

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
            "phase1": phase1.model_dump(mode='json'),
            "phase2": phase2.model_dump(mode='json') if phase2 else None,
            "phase3": phase3.model_dump(mode='json') if phase3 else None,
            "phase4": phase4.model_dump(mode='json') if phase4 else None,
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
            "phase1": phase1.model_dump(mode='json'),
            "phase2": phase2.model_dump(mode='json') if phase2 else None,
            "phase3": phase3.model_dump(mode='json') if phase3 else None,
            "phase4": phase4.model_dump(mode='json') if phase4 else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info("初始化公共智能体配置")

        return UserAgentConfigResponse.from_db(doc)

    # ========================================================================
    # 用户配置管理
    # ========================================================================

    def _load_public_config_from_yaml(
        self,
        include_prompts: bool = False
    ) -> Optional[UserAgentConfigResponse]:
        """
        从 YAML 文件加载公共配置（实时加载）

        **重要**：此方法用于公共配置用户，确保修改 YAML 文件后实时生效。

        Args:
            include_prompts: 是否包含提示词

        Returns:
            公共配置对象
        """
        try:
            # 从 YAML 文件加载公共配置
            yaml_config = self._config_loader.load_public_config()

            # 验证配置
            validated_config = self._config_loader.validate_config(yaml_config)

            # 构建响应对象
            phase1 = Phase1Config(**validated_config.get("phase1", {}))
            phase2 = (
                Phase2Config(**validated_config["phase2"])
                if validated_config.get("phase2") else None
            )
            phase3 = (
                Phase3Config(**validated_config["phase3"])
                if validated_config.get("phase3") else None
            )
            phase4 = (
                Phase4Config(**validated_config["phase4"])
                if validated_config.get("phase4") else None
            )

            # 构建伪文档对象
            doc = {
                "_id": "public_config",  # 使用固定的 ID 表示公共配置
                "user_id": PUBLIC_USER_ID,
                "is_public": True,
                "is_customized": False,
                "phase1": phase1.model_dump(mode='json'),
                "phase2": phase2.model_dump(mode='json') if phase2 else None,
                "phase3": phase3.model_dump(mode='json') if phase3 else None,
                "phase4": phase4.model_dump(mode='json') if phase4 else None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "_source": "yaml",  # 标记来源
            }

            logger.debug(f"从 YAML 加载公共配置: include_prompts={include_prompts}")
            return self._build_response(doc, include_prompts)

        except Exception as e:
            logger.error(f"从 YAML 加载公共配置失败: {e}", exc_info=True)
            return None

    async def get_effective_config(
        self,
        user_id: str,
        include_prompts: bool = False
    ) -> Optional[UserAgentConfigResponse]:
        """
        获取用户的生效配置

        **配置加载逻辑**：
        1. 如果用户已自定义配置 → 返回个人配置（从数据库，与模板合并）
        2. 如果用户未自定义 → 返回公共配置（从 YAML 文件实时加载）

        **配置合并机制**：
        - 个人配置会与最新的 YAML 模板进行智能合并
        - 保留用户自定义的 roleDefinition（提示词）
        - 自动添加缺失的智能体（如新添加的 trader）
        - 确保配置始终符合最新的结构要求

        **重要**：
        - 公共配置从 YAML 文件实时加载，修改 YAML 文件后立即生效
        - 个人配置从数据库加载，通过 API 更新
        - 合并后的配置会进行验证，确保符合固定智能体约束

        Args:
            user_id: 用户 ID
            include_prompts: 是否包含提示词（role_definition）
                - True: 返回完整配置（包含 role_definition）
                - False: 返回精简配置（不包含 role_definition）

        Returns:
            生效配置
        """
        from modules.trading_agents.config.merger import get_config_merger

        collection = self._get_collection()

        # 查询用户个人配置
        user_doc = await collection.find_one({"user_id": user_id})

        # 如果用户有个人配置且已自定义，进行合并
        if user_doc and user_doc.get("is_customized", False):
            logger.debug(
                f"用户使用个人配置（与模板合并）: "
                f"user_id={user_id}, include_prompts={include_prompts}"
            )

            # 使用配置合并器进行智能合并
            merger = get_config_merger()
            merged_config = await merger.merge_user_config(
                user_config=user_doc,
                include_prompts=include_prompts
            )

            # 构建响应
            return self._build_response(merged_config, include_prompts)

        # 否则返回公共配置（从 YAML 文件实时加载）
        logger.debug(
            f"用户使用公共配置（从 YAML）: "
            f"user_id={user_id}, include_prompts={include_prompts}"
        )
        return self._load_public_config_from_yaml(include_prompts)

    def _build_response(
        self,
        config: Dict[str, Any],
        include_prompts: bool = False
    ) -> UserAgentConfigResponse:
        """
        构建配置响应对象

        Args:
            config: 配置字典（可能是从数据库或合并后的配置）
            include_prompts: 是否包含提示词

        Returns:
            配置响应对象
        """
        import copy

        # 使用深拷贝避免修改原始数据
        config_copy = copy.deepcopy(config)

        # 处理 _id 到 id 的转换（MongoDB 使用 _id，Pydantic 需要 id）
        if "_id" in config_copy and "id" not in config_copy:
            config_copy["id"] = str(config_copy.pop("_id"))
        elif "id" not in config_copy:
            # 如果既没有 _id 也没有 id，生成一个
            import uuid
            config_copy["id"] = str(uuid.uuid4())

        # 确保必需字段存在
        if "user_id" not in config_copy:
            raise ValueError("配置缺少 user_id 字段")
        if "created_at" not in config_copy:
            raise ValueError("配置缺少 created_at 字段")
        if "updated_at" not in config_copy:
            raise ValueError("配置缺少 updated_at 字段")

        # 如果需要包含提示词，直接返回
        if include_prompts:
            return UserAgentConfigResponse(**config_copy)

        # 否则，移除 role_definition 字段
        for phase_key in ["phase1", "phase2", "phase3", "phase4"]:
            phase_data = config_copy.get(phase_key)
            if phase_data and "agents" in phase_data:
                for agent in phase_data["agents"]:
                    # 移除 role_definition 字段
                    agent.pop("roleDefinition", None)
                    agent.pop("role_definition", None)

        return UserAgentConfigResponse(**config_copy)

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

        # 验证各阶段配置更新
        for phase_key, phase_data in [
            ("phase1", request.phase1),
            ("phase2", request.phase2),
            ("phase3", request.phase3),
            ("phase4", request.phase4),
        ]:
            if phase_data is not None:
                try:
                    self._validate_phase_update(phase_key, phase_data, doc)
                except ValueError as e:
                    logger.warning(f"用户配置验证失败: user_id={user_id}, error={e}")
                    raise ValueError(str(e))

        # 构建更新数据（保留用户的选择）
        update_data = {}
        if request.phase1 is not None:
            phase1_data = request.phase1.model_dump(mode='json')
            # 去重：根据 slug 去除重复的智能体
            if "agents" in phase1_data:
                phase1_data["agents"] = self._deduplicate_agents_by_slug(phase1_data["agents"])
            update_data["phase1"] = phase1_data
        if request.phase2 is not None:
            phase2_data = request.phase2.model_dump(mode='json')
            # 去重：根据 slug 去除重复的智能体
            if "agents" in phase2_data:
                phase2_data["agents"] = self._deduplicate_agents_by_slug(phase2_data["agents"])
            update_data["phase2"] = phase2_data
        if request.phase3 is not None:
            phase3_data = request.phase3.model_dump(mode='json')
            # 去重：根据 slug 去除重复的智能体
            if "agents" in phase3_data:
                phase3_data["agents"] = self._deduplicate_agents_by_slug(phase3_data["agents"])
            update_data["phase3"] = phase3_data
        if request.phase4 is not None:
            phase4_data = request.phase4.model_dump(mode='json')
            # 去重：根据 slug 去除重复的智能体
            if "agents" in phase4_data:
                phase4_data["agents"] = self._deduplicate_agents_by_slug(phase4_data["agents"])
            update_data["phase4"] = phase4_data

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

        # 调试：打印保存的数据
        if updated_doc and "phase1" in updated_doc:
            logger.info(f"[DEBUG] Saved phase1 data: {updated_doc['phase1']}")
            if 'agents' in updated_doc['phase1'] and updated_doc['phase1']['agents']:
                first_agent = updated_doc['phase1']['agents'][0]
                logger.info(
                    f"[DEBUG] First agent enabled_mcp_servers: "
                    f"{first_agent.get('enabled_mcp_servers', 'MISSING')}"
                )
                logger.info(
                    f"[DEBUG] Type of enabled_mcp_servers: "
                    f"{type(first_agent.get('enabled_mcp_servers'))}"
                )

        # 调试：打印 update_data
        logger.info(
            f"[DEBUG] update_data phase1 agents: "
            f"{update_data.get('phase1', {}).get('agents', [])}"
        )

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
            "phase1": config.phase1.model_dump(mode='json'),
            "phase2": config.phase2.model_dump(mode='json') if config.phase2 else None,
            "phase3": config.phase3.model_dump(mode='json') if config.phase3 else None,
            "phase4": config.phase4.model_dump(mode='json') if config.phase4 else None,
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
            "phase1": phase1.model_dump(mode='json'),
            "phase2": phase2.model_dump(mode='json') if phase2 else None,
            "phase3": phase3.model_dump(mode='json') if phase3 else None,
            "phase4": phase4.model_dump(mode='json') if phase4 else None,
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
            "phase1": phase1.model_dump(mode='json'),
            "phase2": phase2.model_dump(mode='json') if phase2 else None,
            "phase3": phase3.model_dump(mode='json') if phase3 else None,
            "phase4": phase4.model_dump(mode='json') if phase4 else None,
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
