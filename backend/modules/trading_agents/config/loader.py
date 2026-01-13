"""
配置加载器

负责加载、验证和合并智能体配置。

新架构支持：
- 从 phases/*/agents/*.yaml 目录结构加载配置
- 保持向后兼容，支持从 templates/agents.yaml 加载
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

from modules.trading_agents.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# =============================================================================
# 配置加载器
# =============================================================================

class ConfigLoader:
    """
    配置加载器

    新架构：从 phases/*/agents/*.yaml 目录结构加载配置
    - Phase 1: phases/phase1/agents/*.yaml (动态数量)
    - Phase 2: phases/phase2/agents/*.yaml (固定 4 个)
    - Phase 3: phases/phase3/agents/*.yaml (固定 4 个)
    - Phase 4: phases/phase4/agents/*.yaml (固定 1 个)
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化配置加载器

        Args:
            base_dir: phases/ 目录的路径
        """
        if base_dir is None:
            # 默认指向 modules/trading_agents/phases/
            base_dir = Path(__file__).parent.parent / "phases"

        self.base_dir = Path(base_dir)
        self._default_config: Optional[Dict[str, Any]] = None

    def load_default_config(self) -> Dict[str, Any]:
        """
        加载默认配置（新架构）

        从 phases/*/agents/*.yaml 目录结构加载所有智能体配置。

        Returns:
            配置字典，格式：
            {
                "phase1": {"agents": [...]},
                "phase2": {"agents": [...]},
                "phase3": {"agents": [...]},
                "phase4": {"agents": [...]}
            }

        Raises:
            ConfigurationError: 配置加载失败
        """
        if self._default_config is not None:
            return self._default_config

        config = {
            "phase1": {"agents": self._load_phase_agents("phase1")},
            "phase2": {"agents": self._load_phase_agents("phase2")},
            "phase3": {"agents": self._load_phase_agents("phase3")},
            "phase4": {"agents": self._load_phase_agents("phase4")},
        }

        self._default_config = config
        logger.info(f"加载默认配置成功: phase1={len(config['phase1']['agents'])} 个智能体")
        return config

    def _load_phase_agents(self, phase_name: str) -> List[Dict[str, Any]]:
        """
        加载指定阶段的智能体配置

        Args:
            phase_name: 阶段名称（如 "phase1", "phase2"）

        Returns:
            智能体配置列表
        """
        agents_dir = self.base_dir / phase_name / "agents"

        if not agents_dir.exists():
            logger.warning(f"智能体目录不存在: {agents_dir}")
            return []

        agents = []
        for yaml_file in sorted(agents_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    agent_config = yaml.safe_load(f)

                # 验证必需字段
                if not agent_config.get("slug"):
                    logger.warning(f"智能体配置缺少 slug: {yaml_file}")
                    continue

                agents.append(agent_config)
                logger.debug(f"加载智能体配置: {agent_config.get('slug')} from {yaml_file.name}")

            except Exception as e:
                logger.warning(f"加载智能体配置失败: {yaml_file}, error={e}")

        logger.info(f"[{phase_name}] 加载 {len(agents)} 个智能体配置")
        return agents

    def load_config_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        从文件加载配置

        Args:
            file_path: 配置文件路径

        Returns:
            配置字典
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            logger.info(f"从文件加载配置成功: {file_path}")
            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"配置文件解析失败: {e}",
                details={"file": str(file_path), "error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"加载配置文件失败: {e}",
                details={"file": str(file_path), "error": str(e)}
            )

    def load_config_from_dict(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        从字典加载配置

        Args:
            config_dict: 配置字典

        Returns:
            配置字典（验证后）
        """
        return self._validate_config(config_dict)

    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证配置

        Args:
            config: 配置字典

        Returns:
            验证后的配置字典

        Raises:
            ConfigurationError: 配置验证失败
        """
        try:
            # 验证第一阶段配置
            if "phase1" in config:
                Phase1Config(**config["phase1"])

            # 验证第二阶段配置
            if "phase2" in config:
                Phase2Config(**config["phase2"])

            # 验证第三阶段配置
            if "phase3" in config:
                Phase3Config(**config["phase3"])

            # 验证第四阶段配置
            if "phase4" in config:
                Phase4Config(**config["phase4"])

            return config

        except ValidationError as e:
            raise ConfigurationError(
                f"配置验证失败: {e}",
                details={"validation_error": str(e)}
            )

    def merge_config(
        self,
        base_config: Dict[str, Any],
        override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并配置

        Args:
            base_config: 基础配置
            override_config: 覆盖配置

        Returns:
            合并后的配置
        """
        import copy

        merged = copy.deepcopy(base_config)

        for phase_key, phase_value in override_config.items():
            if phase_key not in merged:
                merged[phase_key] = phase_value
                continue

            # 合并阶段配置
            if isinstance(phase_value, dict):
                for key, value in phase_value.items():
                    if key == "agents":
                        # 智能体列表需要特殊处理
                        merged_agents = merged.get(phase_key, {}).get("agents", [])
                        override_agents = value

                        # 按 slug 合并智能体配置
                        merged_agents_dict = {a["slug"]: a for a in merged_agents}
                        for agent in override_agents:
                            slug = agent["slug"]
                            if slug in merged_agents_dict:
                                # 更新已存在的智能体
                                merged_agents_dict[slug].update(agent)
                            else:
                                # 添加新智能体
                                merged_agents_dict[slug] = agent

                        merged[phase_key]["agents"] = list(merged_agents_dict.values())
                    else:
                        merged[phase_key][key] = value
            else:
                merged[phase_key] = phase_value

        return merged

    def export_config_to_yaml(self, config: Dict[str, Any], file_path: Path) -> None:
        """
        导出配置到 YAML 文件

        Args:
            config: 配置字典
            file_path: 导出文件路径
        """
        try:
            # 验证配置
            validated_config = self._validate_config(config)

            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(validated_config, f, allow_unicode=True, default_flow_style=False)

            logger.info(f"导出配置成功: {file_path}")

        except Exception as e:
            raise ConfigurationError(
                f"导出配置失败: {e}",
                details={"file": str(file_path), "error": str(e)}
            )


# =============================================================================
# 全局配置加载器实例
# =============================================================================

config_loader = ConfigLoader()


def get_config_loader() -> ConfigLoader:
    """获取全局配置加载器实例"""
    return config_loader


# =============================================================================
# 辅助函数
# =============================================================================

def load_default_config() -> Dict[str, Any]:
    """
    加载默认配置

    Returns:
        配置字典
    """
    return config_loader.load_default_config()


def get_phase1_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    获取第一阶段配置

    Args:
        config: 配置字典，None 表示使用默认配置

    Returns:
        第一阶段配置
    """
    if config is None:
        config = load_default_config()

    return config.get("phase1", {})


def get_phase2_config(config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    获取第二阶段配置

    Args:
        config: 配置字典，None 表示使用默认配置

    Returns:
        第二阶段配置，如果阶段禁用则返回 None
    """
    if config is None:
        config = load_default_config()

    return config.get("phase2")


def get_phase3_config(config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    获取第三阶段配置

    Args:
        config: 配置字典，None 表示使用默认配置

    Returns:
        第三阶段配置，如果阶段禁用则返回 None
    """
    if config is None:
        config = load_default_config()

    return config.get("phase3")


def get_phase4_config(config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    获取第四阶段配置

    Args:
        config: 配置字典，None 表示使用默认配置

    Returns:
        第四阶段配置，如果阶段禁用则返回 None
    """
    if config is None:
        config = load_default_config()

    return config.get("phase4")
