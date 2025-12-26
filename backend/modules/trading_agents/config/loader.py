"""
配置加载器

负责加载、验证和合并智能体配置。
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from pydantic import ValidationError

from modules.trading_agents.schemas import (
    Phase1Config,
    Phase2Config,
    Phase3Config,
    Phase4Config,
    UserAgentConfigCreate,
)
from modules.trading_agents.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# =============================================================================
# 配置加载器
# =============================================================================

class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录，默认为 templates/ 目录
        """
        if config_dir is None:
            config_dir = Path(__file__).parent / "templates"

        self.config_dir = Path(config_dir)
        self._default_config: Optional[Dict[str, Any]] = None

    def load_default_config(self) -> Dict[str, Any]:
        """
        加载默认配置

        Returns:
            配置字典

        Raises:
            ConfigurationError: 配置加载失败
        """
        if self._default_config is not None:
            return self._default_config

        config_file = self.config_dir / "agents.yaml"

        if not config_file.exists():
            raise ConfigurationError(
                f"默认配置文件不存在: {config_file}",
                details={"file": str(config_file)}
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                self._default_config = yaml.safe_load(f)

            logger.info(f"加载默认配置成功: {config_file}")
            return self._default_config

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"配置文件解析失败: {e}",
                details={"file": str(config_file), "error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"加载配置文件失败: {e}",
                details={"file": str(config_file), "error": str(e)}
            )

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


def get_phase1_config(config: Optional[Dict[str, Any]] = None) -> Phase1Config:
    """
    获取第一阶段配置

    Args:
        config: 配置字典，None 表示使用默认配置

    Returns:
        第一阶段配置
    """
    if config is None:
        config = load_default_config()

    phase1_data = config.get("phase1", {})
    return Phase1Config(**phase1_data)


def get_phase2_config(config: Optional[Dict[str, Any]] = None) -> Optional[Phase2Config]:
    """
    获取第二阶段配置

    Args:
        config: 配置字典，None 表示使用默认配置

    Returns:
        第二阶段配置，如果阶段禁用则返回 None
    """
    if config is None:
        config = load_default_config()

    phase2_data = config.get("phase2")
    if not phase2_data or not phase2_data.get("enabled"):
        return None

    return Phase2Config(**phase2_data)


def get_phase3_config(config: Optional[Dict[str, Any]] = None) -> Optional[Phase3Config]:
    """
    获取第三阶段配置

    Args:
        config: 配置字典，None 表示使用默认配置

    Returns:
        第三阶段配置，如果阶段禁用则返回 None
    """
    if config is None:
        config = load_default_config()

    phase3_data = config.get("phase3")
    if not phase3_data or not phase3_data.get("enabled"):
        return None

    return Phase3Config(**phase3_data)


def get_phase4_config(config: Optional[Dict[str, Any]] = None) -> Optional[Phase4Config]:
    """
    获取第四阶段配置

    Args:
        config: 配置字典，None 表示使用默认配置

    Returns:
        第四阶段配置，如果阶段禁用则返回 None
    """
    if config is None:
        config = load_default_config()

    phase4_data = config.get("phase4")
    if not phase4_data or not phase4_data.get("enabled"):
        return None

    return Phase4Config(**phase4_data)


def validate_agent_config(config: Dict[str, Any]) -> UserAgentConfigCreate:
    """
    验证完整的智能体配置

    Args:
        config: 配置字典

    Returns:
        验证后的配置对象
    """
    return UserAgentConfigCreate(**config)
