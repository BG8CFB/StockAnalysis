"""
MCP 配置加载器

从数据库、YAML 文件、环境变量加载 MCP 模块的配置，并提供配置访问接口。

配置加载优先级：
1. 数据库配置（用户通过前端修改）
2. YAML 默认配置
3. 环境变量覆盖
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# 数据库配置加载（同步版本）
# =============================================================================

def load_db_config_sync() -> Dict[str, Any]:
    """
    从数据库加载配置（同步版本）

    尝试从 MongoDB 读取系统配置，如果失败则返回空字典。

    Returns:
        数据库配置字典
    """
    try:
        # 动态导入避免循环依赖
        from core.db.mongodb import mongodb

        collection = mongodb.get_collection("mcp_settings")
        doc = collection.find_one({"_id": "system"})

        if doc:
            doc.pop("_id", None)
            logger.info("从数据库加载 MCP 系统配置")
            return _convert_db_config_to_yaml_format(doc)
    except Exception as e:
        logger.warning(f"从数据库加载配置失败: {e}")

    return {}


def _convert_db_config_to_yaml_format(db_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    将数据库配置转换为 YAML 格式

    Args:
        db_config: 数据库配置字典（下划线命名）

    Returns:
        YAML 格式的配置字典（嵌套结构）
    """
    yaml_config = {}

    # 连接池配置
    if "pool_personal_max_concurrency" in db_config:
        yaml_config.setdefault("pool", {})["personal"] = yaml_config.get("pool", {}).get("personal", {})
        yaml_config["pool"]["personal"]["max_concurrency"] = db_config["pool_personal_max_concurrency"]

    if "pool_public_per_user_max" in db_config:
        yaml_config.setdefault("pool", {})["public"] = yaml_config.get("pool", {}).get("public", {})
        yaml_config["pool"]["public"]["per_user_max"] = db_config["pool_public_per_user_max"]

    if "pool_personal_queue_size" in db_config:
        yaml_config.setdefault("pool", {})["personal"] = yaml_config.get("pool", {}).get("personal", {})
        yaml_config["pool"]["personal"]["queue_size"] = db_config["pool_personal_queue_size"]

    if "pool_public_queue_size" in db_config:
        yaml_config.setdefault("pool", {})["public"] = yaml_config.get("pool", {}).get("public", {})
        yaml_config["pool"]["public"]["queue_size"] = db_config["pool_public_queue_size"]

    # 连接生命周期
    if "connection_complete_timeout" in db_config:
        yaml_config.setdefault("connection", {})["complete_timeout"] = db_config["connection_complete_timeout"]

    if "connection_failed_timeout" in db_config:
        yaml_config.setdefault("connection", {})["failed_timeout"] = db_config["connection_failed_timeout"]

    # 健康检查
    if "health_check_enabled" in db_config:
        yaml_config.setdefault("health_check", {})["enabled"] = db_config["health_check_enabled"]

    if "health_check_interval" in db_config:
        yaml_config.setdefault("health_check", {})["interval"] = db_config["health_check_interval"]

    if "health_check_timeout" in db_config:
        yaml_config.setdefault("health_check", {})["timeout"] = db_config["health_check_timeout"]

    return yaml_config


# =============================================================================
# 配置缓存
# =============================================================================

_mcp_config_cache: Optional[Dict[str, Any]] = None


# =============================================================================
# 配置加载函数
# =============================================================================

def get_default_config_path() -> Path:
    """
    获取默认配置文件路径

    Returns:
        配置文件的 Path 对象
    """
    # 当前文件所在目录
    current_dir = Path(__file__).parent
    return current_dir / "default_config.yaml"


def load_yaml_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    从 YAML 文件加载配置

    Args:
        config_path: 配置文件路径，默认使用 default_config.yaml

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: YAML 格式错误或 pyyaml 未安装
    """
    if not YAML_AVAILABLE:
        raise ValueError(
            "pyyaml 包未安装，无法加载 YAML 配置文件。"
            "请运行: pip install pyyaml"
        )

    if config_path is None:
        config_path = get_default_config_path()

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        logger.info(f"MCP 配置文件加载成功: {config_path}")
        return config

    except yaml.YAMLError as e:
        raise ValueError(f"YAML 配置文件格式错误: {e}")
    except Exception as e:
        raise RuntimeError(f"加载配置文件失败: {e}")


def get_env_overrides() -> Dict[str, Any]:
    """
    从环境变量获取配置覆盖

    支持的环境变量格式：
    - MCP_POOL_PERSONAL_MAX_CONCURRENCY
    - MCP_POOL_PUBLIC_PER_USER_MAX
    - MCP_CONNECTION_COMPLETE_TIMEOUT
    - MCP_HEALTH_CHECK_INTERVAL
    等等

    Returns:
        环境变量覆盖的配置字典
    """
    overrides: Dict[str, Any] = {}

    # MCP_POOL_*
    if "MCP_POOL_PERSONAL_MAX_CONCURRENCY" in os.environ:
        overrides.setdefault("pool", {})["personal"] = overrides.get("pool", {}).get("personal", {})
        overrides["pool"]["personal"]["max_concurrency"] = int(os.environ["MCP_POOL_PERSONAL_MAX_CONCURRENCY"])

    if "MCP_POOL_PUBLIC_PER_USER_MAX" in os.environ:
        overrides.setdefault("pool", {})["public"] = overrides.get("pool", {}).get("public", {})
        overrides["pool"]["public"]["per_user_max"] = int(os.environ["MCP_POOL_PUBLIC_PER_USER_MAX"])

    # MCP_CONNECTION_*
    if "MCP_CONNECTION_COMPLETE_TIMEOUT" in os.environ:
        overrides.setdefault("connection", {})["complete_timeout"] = int(os.environ["MCP_CONNECTION_COMPLETE_TIMEOUT"])

    if "MCP_CONNECTION_FAILED_TIMEOUT" in os.environ:
        overrides.setdefault("connection", {})["failed_timeout"] = int(os.environ["MCP_CONNECTION_FAILED_TIMEOUT"])

    # MCP_HEALTH_CHECK_*
    if "MCP_HEALTH_CHECK_ENABLED" in os.environ:
        overrides.setdefault("health_check", {})["enabled"] = os.environ["MCP_HEALTH_CHECK_ENABLED"].lower() in ("true", "1", "yes")

    if "MCP_HEALTH_CHECK_INTERVAL" in os.environ:
        overrides.setdefault("health_check", {})["interval"] = int(os.environ["MCP_HEALTH_CHECK_INTERVAL"])

    if overrides:
        logger.info(f"从环境变量获取配置覆盖: {list(overrides.keys())}")

    return overrides


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个配置字典

    Args:
        base: 基础配置
        override: 覆盖配置

    Returns:
        合并后的配置字典
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def load_mcp_config(config_path: Optional[Path] = None, use_cache: bool = True) -> Dict[str, Any]:
    """
    加载 MCP 配置（完整流程）

    加载优先级：
    1. 数据库配置（用户通过前端修改）
    2. YAML 文件默认配置
    3. 环境变量覆盖

    Args:
        config_path: 配置文件路径，默认使用 default_config.yaml
        use_cache: 是否使用缓存的配置

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: YAML 格式错误或 pyyaml 未安装
    """
    global _mcp_config_cache

    # 使用缓存
    if use_cache and _mcp_config_cache is not None:
        return _mcp_config_cache

    # 1. 加载 YAML 默认配置
    yaml_config = load_yaml_config(config_path)

    # 2. 加载数据库配置（优先级高于 YAML）
    db_overrides = load_db_config_sync()

    # 3. 合并数据库配置和 YAML 配置
    base_config = merge_configs(yaml_config, db_overrides)

    # 4. 加载环境变量覆盖（最高优先级）
    env_overrides = get_env_overrides()

    # 5. 最终合并
    final_config = merge_configs(base_config, env_overrides)

    # 缓存配置
    _mcp_config_cache = final_config

    return final_config


def get_mcp_config(*keys: str, default: Any = None) -> Any:
    """
    获取配置值（支持嵌套键访问）

    Args:
        *keys: 配置键路径，如 "pool", "personal", "max_concurrency"
        default: 默认值

    Returns:
        配置值

    Examples:
        >>> get_mcp_config("pool", "personal", "max_concurrency")
        100
        >>> get_mcp_config("health_check", "interval")
        300
        >>> get_mcp_config("nonexistent", "key", default=42)
        42
    """
    config = load_mcp_config()

    # 遍历键路径
    value = config
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default

    return value if value is not None else default


def reload_mcp_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    重新加载配置（清除缓存）

    Args:
        config_path: 配置文件路径，默认使用 default_config.yaml

    Returns:
        配置字典
    """
    global _mcp_config_cache
    _mcp_config_cache = None
    return load_mcp_config(config_path, use_cache=False)


# =============================================================================
# 配置访问便捷函数
# =============================================================================

def get_pool_personal_max_concurrency() -> int:
    """获取个人 MCP 最大并发数"""
    return get_mcp_config("pool", "personal", "max_concurrency", default=100)


def get_pool_public_per_user_max() -> int:
    """获取公共 MCP 每用户最大并发数"""
    return get_mcp_config("pool", "public", "per_user_max", default=10)


def get_pool_personal_queue_size() -> int:
    """获取个人 MCP 队列大小"""
    return get_mcp_config("pool", "personal", "queue_size", default=200)


def get_pool_public_queue_size() -> int:
    """获取公共 MCP 队列大小"""
    return get_mcp_config("pool", "public", "queue_size", default=50)


def get_connection_complete_timeout() -> int:
    """
    获取连接完成后超时时间（秒）

    优化说明：从10秒降低到2秒
    - 2秒缓冲期足够覆盖边界情况（比如任务完成后的后续清理工作）
    - 减少资源占用，避免连接长时间保持
    - 如果用户快速重试，2秒足够复用连接
    """
    return get_mcp_config("connection", "complete_timeout", default=2)


def get_connection_failed_timeout() -> int:
    """
    获取连接失败后超时时间（秒）

    优化说明：从30秒降低到10秒
    - 保留更长时间便于调试和查看错误信息
    - 但不需要30秒那么长
    - 减少失败连接的资源占用
    """
    return get_mcp_config("connection", "failed_timeout", default=10)


def get_connection_connect_timeout() -> int:
    """获取连接建立超时时间（秒）"""
    return get_mcp_config("connection", "connect_timeout", default=30)


def get_connection_read_timeout() -> int:
    """获取读取数据超时时间（秒）"""
    return get_mcp_config("connection", "read_timeout", default=120)


def get_health_check_enabled() -> bool:
    """是否启用健康检查"""
    return get_mcp_config("health_check", "enabled", default=True)


def get_health_check_interval() -> int:
    """获取健康检查间隔时间（秒）"""
    return get_mcp_config("health_check", "interval", default=300)


def get_health_check_timeout() -> int:
    """获取健康检查超时时间（秒）"""
    return get_mcp_config("health_check", "timeout", default=30)


def get_health_check_max_concurrent_checks() -> int:
    """获取健康检查最大并发数"""
    return get_mcp_config("health_check", "max_concurrent_checks", default=5)


def get_cleanup_enabled() -> bool:
    """是否启用清理任务"""
    return get_mcp_config("cleanup", "enabled", default=True)


def get_cleanup_interval() -> int:
    """获取清理任务间隔时间（秒）"""
    return get_mcp_config("cleanup", "interval", default=60)


def get_cleanup_batch_size() -> int:
    """获取清理任务批次大小"""
    return get_mcp_config("cleanup", "batch_size", default=10)


def get_session_timeout() -> int:
    """获取会话超时时间（秒）"""
    return get_mcp_config("session", "session_timeout", default=600)


def get_session_idle_timeout() -> int:
    """获取会话空闲超时时间（秒）"""
    return get_mcp_config("session", "idle_timeout", default=300)
