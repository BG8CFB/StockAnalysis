"""
配置合并器

**版本**: v1.0
**最后更新**: 2026-01-16

负责将用户个人配置与最新的 YAML 模板配置进行智能合并，
确保用户配置始终包含完整的智能体结构，同时保留用户自定义的提示词。

合并策略：
1. 结构对齐：确保用户配置包含所有必需的智能体
2. 自定义保留：保留用户修改的 roleDefinition
3. 新增处理：自动添加用户新配置中缺失的智能体
4. 验证保护：确保合并后的配置符合验证规则
"""

import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional

from modules.trading_agents.config.loader import AgentConfigLoader, get_config_loader
from modules.trading_agents.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigMerger:
    """
    配置合并器

    将用户个人配置与 YAML 模板配置进行智能合并。
    """

    def __init__(self, loader: Optional[AgentConfigLoader] = None):
        """
        初始化配置合并器

        Args:
            loader: 配置加载器
        """
        self.loader = loader or get_config_loader()

    async def merge_user_config(
        self,
        user_config: Dict[str, Any],
        include_prompts: bool = True
    ) -> Dict[str, Any]:
        """
        合并用户配置与最新的 YAML 模板

        Args:
            user_config: 用户个人配置（从数据库加载）
            include_prompts: 是否包含提示词

        Returns:
            合并后的配置
        """
        logger.info(f"开始合并用户配置: user_id={user_config.get('user_id')}")

        # 加载最新的公共配置作为模板
        template_config = self.loader.load_public_config()

        # 深拷贝避免修改原始数据
        merged_config = deepcopy(user_config)

        # 合并每个阶段
        for phase in ["phase1", "phase2", "phase3", "phase4"]:
            if phase not in template_config:
                logger.warning(f"模板配置缺少阶段: {phase}")
                continue

            if phase not in merged_config:
                # 用户配置缺少该阶段，直接使用模板
                logger.info(f"用户配置缺少阶段 {phase}，使用模板配置")
                merged_config[phase] = deepcopy(template_config[phase])
                continue

            # 合并该阶段的智能体
            merged_config[phase] = self._merge_phase_agents(
                phase=phase,
                user_agents=merged_config[phase].get("agents", []),
                template_agents=template_config[phase].get("agents", []),
                include_prompts=include_prompts
            )

        # Phase 4 强制启用
        if "phase4" in merged_config:
            merged_config["phase4"]["enabled"] = True

        logger.info(f"用户配置合并完成: user_id={user_config.get('user_id')}")

        # 验证合并后的配置
        try:
            self.loader.validate_config(merged_config)
        except ConfigurationError as e:
            logger.error(f"合并后的配置验证失败: {e}")
            # 验证失败时，返回模板配置（兜底）
            logger.warning("验证失败，返回模板配置（兜底）")
            # 保留用户的元数据，使用模板的配置
            fallback_config = self._build_fallback_config(
                user_config=user_config,
                template_config=template_config,
                include_prompts=include_prompts
            )
            return fallback_config

        return merged_config

    def _merge_phase_agents(
        self,
        phase: str,
        user_agents: List[Dict[str, Any]],
        template_agents: List[Dict[str, Any]],
        include_prompts: bool
    ) -> Dict[str, Any]:
        """
        合并单个阶段的智能体列表

        Args:
            phase: 阶段名称
            user_agents: 用户的智能体列表
            template_agents: 模板的智能体列表
            include_prompts: 是否包含提示词

        Returns:
            合并后的阶段配置
        """
        # 创建 slug -> agent 的映射
        template_map = {agent["slug"]: agent for agent in template_agents}

        merged_agents = []
        processed_slugs = set()

        # 首先处理用户已有的智能体（保留自定义内容）
        for user_agent in user_agents:
            slug = user_agent.get("slug")
            if not slug:
                continue

            processed_slugs.add(slug)

            if slug in template_map:
                # 智能体存在于模板中，合并
                template_agent = template_map[slug]
                merged_agent = deepcopy(template_agent)

                # 保留用户自定义的 roleDefinition
                if "roleDefinition" in user_agent and include_prompts:
                    merged_agent["roleDefinition"] = user_agent["roleDefinition"]

                # 保留用户的 enabled 状态（Phase 2-3 可以禁用阶段，但智能体本身的状态）
                if "enabled" in user_agent:
                    merged_agent["enabled"] = user_agent["enabled"]

                merged_agents.append(merged_agent)
                logger.debug(f"[{phase}] 合并智能体: {slug}（保留用户自定义）")

            else:
                # 智能体不存在于模板中（Phase 1 允许自定义智能体）
                merged_agent = deepcopy(user_agent)
                merged_agents.append(merged_agent)
                logger.debug(f"[{phase}] 保留用户自定义智能体: {slug}")

        # 添加模板中存在但用户配置中缺失的智能体
        for template_slug, template_agent in template_map.items():
            if template_slug not in processed_slugs:
                merged_agent = deepcopy(template_agent)
                merged_agents.append(merged_agent)
                logger.debug(f"[{phase}] 添加缺失的智能体: {template_slug}")

        # 获取 enabled 状态：优先使用用户的，否则使用模板的
        if user_agents:
            enabled = user_agents[0].get("enabled", True)
        else:
            enabled = template_agents[0].get("enabled", True) if template_agents else True

        # 标准化字段名（role_definition -> roleDefinition）
        for agent in merged_agents:
            if "role_definition" in agent and "roleDefinition" not in agent:
                agent["roleDefinition"] = agent.pop("role_definition")

        return {
            "enabled": enabled,
            "agents": merged_agents
        }

    def _build_fallback_config(
        self,
        user_config: Dict[str, Any],
        template_config: Dict[str, Any],
        include_prompts: bool
    ) -> Dict[str, Any]:
        """
        构建兜底配置（保留用户元数据，使用模板的配置）

        Args:
            user_config: 用户配置（从数据库加载，包含元数据）
            template_config: 模板配置（从 YAML 加载）
            include_prompts: 是否包含提示词

        Returns:
            兜底配置
        """
        # 创建兜底配置，保留用户的元数据
        fallback = {
            "_id": user_config.get("_id"),
            "user_id": user_config.get("user_id"),
            "is_public": user_config.get("is_public", False),
            "is_customized": user_config.get("is_customized", False),
            "created_at": user_config.get("created_at"),
            "updated_at": user_config.get("updated_at"),
        }

        # 添加模板的配置（根据 include_prompts 决定是否包含提示词）
        phase_config = template_config if include_prompts else self._strip_prompts(template_config)

        for phase in ["phase1", "phase2", "phase3", "phase4"]:
            if phase in phase_config:
                fallback[phase] = phase_config[phase]

        # 标准化字段名（role_definition -> roleDefinition）
        for phase in ["phase1", "phase2", "phase3", "phase4"]:
            if phase in fallback and "agents" in fallback[phase]:
                for agent in fallback[phase]["agents"]:
                    if "role_definition" in agent and "roleDefinition" not in agent:
                        agent["roleDefinition"] = agent.pop("role_definition")

        return fallback

    def _strip_prompts(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        移除配置中的提示词（返回精简版）

        Args:
            config: 完整配置

        Returns:
            精简配置（不含 roleDefinition）
        """
        stripped = deepcopy(config)

        for phase_key in ["phase1", "phase2", "phase3", "phase4"]:
            phase_data = stripped.get(phase_key)
            if phase_data and "agents" in phase_data:
                for agent in phase_data["agents"]:
                    agent.pop("roleDefinition", None)
                    agent.pop("role_definition", None)

        return stripped


# =============================================================================
# 便捷函数
# =============================================================================

_merger: Optional[ConfigMerger] = None


def get_config_merger() -> ConfigMerger:
    """获取全局配置合并器实例"""
    global _merger
    if _merger is None:
        _merger = ConfigMerger()
    return _merger
