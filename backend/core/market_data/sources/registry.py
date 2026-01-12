"""
数据源注册表

提供数据源适配器的中央注册机制，用于管理和获取所有数据源适配器。
"""

import logging
from typing import Dict, Type, List, Optional

from core.market_data.models import MarketType
from core.market_data.sources.base import DataSourceAdapter

logger = logging.getLogger(__name__)


class DataSourceRegistry:
    """数据源注册表

    管理所有数据源适配器的注册和获取。
    """

    def __init__(self):
        """初始化注册表"""
        self._adapters: Dict[str, Type[DataSourceAdapter]] = {}
        self._instances: Dict[str, DataSourceAdapter] = {}

    def register(
        self,
        source_id: str,
        adapter_class: Type[DataSourceAdapter],
        market: MarketType = MarketType.A_STOCK,
    ) -> None:
        """注册数据源适配器

        Args:
            source_id: 数据源标识（如 "tushare", "akshare"）
            adapter_class: 适配器类
            market: 市场类型
        """
        key = f"{market.value}:{source_id}"

        if key in self._adapters:
            logger.warning(f"数据源适配器已存在，将覆盖: {key}")

        self._adapters[key] = adapter_class
        logger.info(f"注册数据源适配器: {key} -> {adapter_class.__name__}")

    def get(
        self,
        source_id: str,
        market: MarketType = MarketType.A_STOCK,
        config: dict = None,
    ) -> Optional[DataSourceAdapter]:
        """获取数据源适配器实例

        Args:
            source_id: 数据源标识
            market: 市场类型
            config: 配置参数

        Returns:
            适配器实例，不存在时返回 None
        """
        key = f"{market.value}:{source_id}"

        if key not in self._adapters:
            logger.warning(f"数据源适配器未注册: {key}")
            return None

        # 复用已创建的实例（如果配置相同）
        instance_key = f"{key}:{hash(str(config))}"
        if instance_key in self._instances:
            return self._instances[instance_key]

        # 创建新实例
        adapter_class = self._adapters[key]
        instance = adapter_class(config or {})
        self._instances[instance_key] = instance

        logger.debug(f"创建数据源适配器实例: {key}")
        return instance

    def list_by_market(self, market: MarketType) -> List[str]:
        """列出指定市场的所有数据源

        Args:
            market: 市场类型

        Returns:
            数据源标识列表
        """
        prefix = f"{market.value}:"
        return [
            key[len(prefix):]
            for key in self._adapters.keys()
            if key.startswith(prefix)
        ]

    def list_all(self) -> List[str]:
        """列出所有已注册的数据源

        Returns:
            数据源标识列表（格式：market:source_id）
        """
        return list(self._adapters.keys())

    def is_registered(self, source_id: str, market: MarketType = MarketType.A_STOCK) -> bool:
        """检查数据源是否已注册

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            是否已注册
        """
        key = f"{market.value}:{source_id}"
        return key in self._adapters

    def unregister(self, source_id: str, market: MarketType = MarketType.A_STOCK) -> bool:
        """注销数据源适配器

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            是否注销成功
        """
        key = f"{market.value}:{source_id}"

        if key not in self._adapters:
            logger.warning(f"数据源适配器未注册，无法注销: {key}")
            return False

        del self._adapters[key]

        # 清理相关实例
        to_remove = [
            instance_key
            for instance_key in self._instances.keys()
            if instance_key.startswith(f"{key}:")
        ]
        for instance_key in to_remove:
            del self._instances[instance_key]

        logger.info(f"注销数据源适配器: {key}")
        return True

    def clear(self) -> None:
        """清空所有注册的数据源"""
        self._adapters.clear()
        self._instances.clear()
        logger.info("清空所有数据源注册")


# 全局注册表实例
_global_registry: Optional[DataSourceRegistry] = None


def get_registry() -> DataSourceRegistry:
    """获取全局注册表实例

    Returns:
        全局注册表实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = DataSourceRegistry()
        logger.info("创建全局数据源注册表")
    return _global_registry


def register_adapter(
    source_id: str,
    adapter_class: Type[DataSourceAdapter],
    market: MarketType = MarketType.A_STOCK,
) -> None:
    """注册数据源适配器的便捷函数

    Args:
        source_id: 数据源标识
        adapter_class: 适配器类
        market: 市场类型
    """
    registry = get_registry()
    registry.register(source_id, adapter_class, market)


def get_adapter(
    source_id: str,
    market: MarketType = MarketType.A_STOCK,
    config: dict = None,
) -> Optional[DataSourceAdapter]:
    """获取数据源适配器实例的便捷函数

    Args:
        source_id: 数据源标识
        market: 市场类型
        config: 配置参数

    Returns:
        适配器实例
    """
    registry = get_registry()
    return registry.get(source_id, market, config)
