"""
智能体配置加载器

负责加载、验证和管理智能体配置。

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15

配置层级结构：
1. 默认配置 (agents_default.yaml) - 项目内置，永不修改
2. 公共配置 (agents_public.yaml) - 管理员可修改，所有用户共享
3. 用户个人配置 (MongoDB) - 用户自定义，优先级最高
"""

import logging
import yaml
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from modules.trading_agents.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# =============================================================================
# 配置路径管理
# =============================================================================

class ConfigPaths:
    """配置路径管理"""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化配置路径

        Args:
            base_dir: trading_agents 模块根目录
        """
        if base_dir is None:
            base_dir = Path(__file__).parent.parent

        self.base_dir = Path(base_dir)
        self.config_dir = self.base_dir / "config" / "agents"
        self.default_config_path = self.config_dir / "agents_default.yaml"
        self.public_config_path = self.config_dir / "agents_public.yaml"

    def ensure_public_config(self) -> None:
        """
        确保公共配置文件存在

        如果不存在，从默认配置复制
        """
        if not self.public_config_path.exists():
            logger.info("公共配置不存在，从默认配置复制")
            shutil.copy(self.default_config_path, self.public_config_path)
            logger.info(f"创建公共配置: {self.public_config_path}")


# =============================================================================
# 配置加载器
# =============================================================================

class AgentConfigLoader:
    """
    智能体配置加载器

    支持三层配置优先级：
    1. 用户个人配置 (MongoDB) - 优先级最高
    2. 公共配置 (agents_public.yaml)
    3. 默认配置 (agents_default.yaml) - 兜底
    """

    def __init__(self, paths: Optional[ConfigPaths] = None):
        """
        初始化配置加载器

        Args:
            paths: 配置路径管理器
        """
        self.paths = paths or ConfigPaths()
        self.paths.ensure_public_config()

        # 缓存
        self._default_config: Optional[Dict[str, Any]] = None
        self._public_config: Optional[Dict[str, Any]] = None

    def load_default_config(self) -> Dict[str, Any]:
        """
        加载默认配置

        Returns:
            默认配置字典
        """
        if self._default_config is not None:
            return self._default_config

        self._default_config = self._load_yaml_file(self.paths.default_config_path)
        logger.info("加载默认配置成功")
        return self._default_config

    def load_public_config(self) -> Dict[str, Any]:
        """
        加载公共配置

        Returns:
            公共配置字典
        """
        if self._public_config is not None:
            return self._public_config

        if not self.paths.public_config_path.exists():
            logger.warning("公共配置不存在，使用默认配置")
            return self.load_default_config()

        self._public_config = self._load_yaml_file(self.paths.public_config_path)
        logger.info("加载公共配置成功")
        return self._public_config

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """
        从 YAML 文件加载配置

        Args:
            file_path: 文件路径

        Returns:
            配置字典
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ConfigurationError(
                    f"配置文件格式错误: 期望字典类型",
                    details={"file": str(file_path), "type": type(config).__name__}
                )

            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"YAML 解析失败: {e}",
                details={"file": str(file_path), "error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"加载配置文件失败: {e}",
                details={"file": str(file_path), "error": str(e)}
            )

    # Phase 2-4 固定智能体定义（只能修改提示词，不能删除或添加）
    FIXED_AGENTS = {
        "phase2": ["bull-researcher", "bear-researcher", "research-manager", "trader"],
        "phase3": ["aggressive-debator", "neutral-debator", "conservative-debator", "risk-manager"],
        "phase4": ["summarizer"]
    }

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证配置结构

        Args:
            config: 配置字典

        Returns:
            验证后的配置字典

        Raises:
            ConfigurationError: 配置验证失败
        """
        # 验证必需的阶段
        required_phases = ["phase1", "phase2", "phase3", "phase4"]
        for phase in required_phases:
            if phase not in config:
                raise ConfigurationError(
                    f"缺少必需的阶段配置: {phase}",
                    details={"missing_phase": phase}
                )

            phase_config = config[phase]

            # Phase 4 是必须执行的
            if phase == "phase4":
                phase_config["enabled"] = True

            # 验证必需字段
            if "enabled" not in phase_config:
                raise ConfigurationError(
                    f"阶段配置缺少 enabled 字段: {phase}",
                    details={"phase": phase}
                )

            if "agents" not in phase_config:
                raise ConfigurationError(
                    f"阶段配置缺少 agents 字段: {phase}",
                    details={"phase": phase}
                )

            # 验证智能体列表
            agents = phase_config["agents"]
            if not isinstance(agents, list):
                raise ConfigurationError(
                    f"agents 字段必须是列表: {phase}",
                    details={"phase": phase, "type": type(agents).__name__}
                )

            # Phase 1: 完全动态，不限制智能体
            if phase == "phase1":
                self._validate_phase1_agents(agents)
            # Phase 2-4: 固定智能体，只能修改提示词
            elif phase in self.FIXED_AGENTS:
                self._validate_fixed_agents(phase, agents)

        return config

    def _validate_phase1_agents(self, agents: List[Dict[str, Any]]) -> None:
        """
        验证 Phase 1 智能体配置（完全动态，不限制智能体）

        Args:
            agents: 智能体列表

        Raises:
            ConfigurationError: 验证失败
        """
        for agent in agents:
            if not isinstance(agent, dict):
                raise ConfigurationError(
                    f"智能体配置必须是字典: phase1",
                    details={"type": type(agent).__name__}
                )

            if "slug" not in agent:
                raise ConfigurationError(
                    f"智能体配置缺少 slug 字段: phase1",
                    details={"agent": agent}
                )

            if "name" not in agent:
                raise ConfigurationError(
                    f"智能体配置缺少 name 字段: phase1, slug={agent.get('slug')}",
                    details={"slug": agent.get("slug")}
                )

            if "roleDefinition" not in agent:
                raise ConfigurationError(
                    f"智能体配置缺少 roleDefinition 字段: phase1, slug={agent.get('slug')}",
                    details={"slug": agent.get("slug")}
                )

    def _validate_fixed_agents(self, phase: str, agents: List[Dict[str, Any]]) -> None:
        """
        验证 Phase 2-4 固定智能体配置（只能修改提示词，不能删除或添加）

        Args:
            phase: 阶段名称
            agents: 智能体列表

        Raises:
            ConfigurationError: 验证失败
        """
        fixed_slugs = self.FIXED_AGENTS[phase]
        agent_slugs = [agent.get("slug") for agent in agents]

        # 验证智能体数量
        if len(agents) != len(fixed_slugs):
            raise ConfigurationError(
                f"{phase} 智能体数量错误: 期望 {len(fixed_slugs)} 个，实际 {len(agents)} 个",
                details={
                    "phase": phase,
                    "expected": len(fixed_slugs),
                    "actual": len(agents),
                    "expected_agents": fixed_slugs,
                    "actual_agents": agent_slugs
                }
            )

        # 验证每个必需的智能体是否存在
        for fixed_slug in fixed_slugs:
            if fixed_slug not in agent_slugs:
                raise ConfigurationError(
                    f"{phase} 缺少必需的智能体: {fixed_slug}（不能删除固定智能体）",
                    details={
                        "phase": phase,
                        "missing_agent": fixed_slug,
                        "required_agents": fixed_slugs
                    }
                )

        # 验证不允许添加额外的智能体
        for agent_slug in agent_slugs:
            if agent_slug not in fixed_slugs:
                raise ConfigurationError(
                    f"{phase} 不允许添加智能体: {agent_slug}（固定智能体不能修改）",
                    details={
                        "phase": phase,
                        "invalid_agent": agent_slug,
                        "allowed_agents": fixed_slugs
                    }
                )

        # 验证每个智能体的必需字段
        for agent in agents:
            if not isinstance(agent, dict):
                raise ConfigurationError(
                    f"智能体配置必须是字典: {phase}",
                    details={"phase": phase, "type": type(agent).__name__}
                )

            if "slug" not in agent:
                raise ConfigurationError(
                    f"智能体配置缺少 slug 字段: {phase}",
                    details={"phase": phase}
                )

            if "name" not in agent:
                raise ConfigurationError(
                    f"智能体配置缺少 name 字段: {phase}, slug={agent.get('slug')}",
                    details={"phase": phase, "slug": agent.get("slug")}
                )

            if "roleDefinition" not in agent:
                raise ConfigurationError(
                    f"智能体配置缺少 roleDefinition 字段: {phase}, slug={agent.get('slug')}",
                    details={"phase": phase, "slug": agent.get("slug")}
                )

            # Phase 4 的 summarizer 必须 enabled
            if phase == "phase4" and not agent.get("enabled", True):
                raise ConfigurationError(
                    f"{phase} 的总结智能体必须启用（不能禁用）",
                    details={"phase": phase, "slug": agent.get("slug")}
                )

    def export_to_yaml(self, config: Dict[str, Any], file_path: Path) -> None:
        """
        导出配置到 YAML 文件

        Args:
            config: 配置字典
            file_path: 导出文件路径
        """
        try:
            # 验证配置
            validated_config = self.validate_config(config)

            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    validated_config,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )

            logger.info(f"导出配置成功: {file_path}")

        except Exception as e:
            raise ConfigurationError(
                f"导出配置失败: {e}",
                details={"file": str(file_path), "error": str(e)}
            )

    def reset_public_config(self) -> None:
        """
        重置公共配置为默认配置

        用默认配置覆盖公共配置
        """
        try:
            shutil.copy(self.paths.default_config_path, self.paths.public_config_path)
            self._public_config = None  # 清除缓存
            logger.info("重置公共配置成功")
        except Exception as e:
            raise ConfigurationError(
                f"重置公共配置失败: {e}",
                details={"error": str(e)}
            )


# =============================================================================
# 全局配置加载器实例
# =============================================================================

_config_loader: Optional[AgentConfigLoader] = None


def get_config_loader() -> AgentConfigLoader:
    """获取全局配置加载器实例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = AgentConfigLoader()
    return _config_loader


# =============================================================================
# 辅助函数
# =============================================================================

def load_default_config() -> Dict[str, Any]:
    """加载默认配置"""
    return get_config_loader().load_default_config()


def load_public_config() -> Dict[str, Any]:
    """加载公共配置"""
    return get_config_loader().load_public_config()


def get_enabled_agents(
    config: Dict[str, Any],
    phase: str
) -> List[Dict[str, Any]]:
    """
    获取指定阶段已启用的智能体列表

    Args:
        config: 配置字典
        phase: 阶段名称 (phase1/phase2/phase3/phase4)

    Returns:
        已启用的智能体列表
    """
    phase_config = config.get(phase, {})
    if not phase_config.get("enabled", False):
        return []

    agents = phase_config.get("agents", [])
    return [agent for agent in agents if agent.get("enabled", True)]


def get_agent_by_slug(
    config: Dict[str, Any],
    phase: str,
    slug: str
) -> Optional[Dict[str, Any]]:
    """
    根据 slug 获取智能体配置

    Args:
        config: 配置字典
        phase: 阶段名称
        slug: 智能体 slug

    Returns:
        智能体配置，未找到返回 None
    """
    agents = config.get(phase, {}).get("agents", [])
    for agent in agents:
        if agent.get("slug") == slug:
            return agent
    return None
