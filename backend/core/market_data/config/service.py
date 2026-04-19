"""
数据源配置管理服务

提供数据源配置的 CRUD 操作，供管理员使用。
"""

import logging
from datetime import datetime
from typing import Any

from core.config import SUPPORTED_MARKETS
from core.market_data.models.datasource import (
    SystemDataSourceConfig,
    UserDataSourceConfig,
)
from core.market_data.repositories.datasource import (
    SystemDataSourceRepository,
    UserDataSourceRepository,
)

logger = logging.getLogger(__name__)


class DataSourceConfigService:
    """数据源配置管理服务"""

    def __init__(self) -> None:
        """初始化服务"""
        self.system_repo = SystemDataSourceRepository()
        self.user_repo = UserDataSourceRepository()

    # ==================== 系统公共数据源配置 ====================

    async def create_system_source(
        self,
        source_id: str,
        market: str,
        enabled: bool = True,
        priority: int = 1,
        config: dict | None = None,
        rate_limit: dict | None = None,
        supported_data_types: list[str] | None = None,
    ) -> SystemDataSourceConfig:
        """创建系统公共数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型
            enabled: 是否启用
            priority: 优先级
            config: 配置信息
            rate_limit: 限流配置
            supported_data_types: 支持的数据类型

        Returns:
            创建的配置对象
        """
        logger.info(f"创建系统公共数据源配置: {source_id} ({market})")

        source_config = SystemDataSourceConfig(
            source_id=source_id,
            market=market,
            enabled=enabled,
            priority=priority,
            is_system_public=True,
            config=config or {},
            rate_limit=rate_limit,
            supported_data_types=supported_data_types or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await self.system_repo.upsert_config(source_config)
        logger.info(f"系统公共数据源配置创建成功: {source_id}")
        return source_config

    async def get_system_source(self, source_id: str, market: str) -> SystemDataSourceConfig | None:
        """获取系统公共数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            配置对象，不存在时返回 None
        """
        config_dict = await self.system_repo.get_config(source_id, market)
        if config_dict:
            return SystemDataSourceConfig(**config_dict)
        return None

    async def list_system_sources(
        self,
        market: str | None = None,
        enabled_only: bool = False,
    ) -> list[SystemDataSourceConfig]:
        """列出系统公共数据源配置

        Args:
            market: 市场类型过滤
            enabled_only: 是否只返回启用的配置

        Returns:
            配置列表
        """
        if market:
            config_dicts = await self.system_repo.get_enabled_configs(market, enabled_only)
        else:
            # 如果没有指定市场，需要查询所有市场
            config_dicts = []
            for m in SUPPORTED_MARKETS:
                configs = await self.system_repo.get_enabled_configs(m, enabled_only)
                config_dicts.extend(configs)

        return [SystemDataSourceConfig(**c) for c in config_dicts]

    async def update_system_source(
        self,
        source_id: str,
        market: str,
        **updates: Any,
    ) -> bool:
        """更新系统公共数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型
            **updates: 要更新的字段

        Returns:
            是否更新成功
        """
        logger.info(f"更新系统公共数据源配置: {source_id} ({market})")

        updates["updated_at"] = datetime.now()
        result = await self.system_repo.update_config(source_id, market, updates)

        if result:
            logger.info(f"系统公共数据源配置更新成功: {source_id}")
        else:
            logger.warning(f"系统公共数据源配置不存在: {source_id}")

        return result > 0

    async def delete_system_source(self, source_id: str, market: str) -> bool:
        """删除系统公共数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            是否删除成功
        """
        logger.info(f"删除系统公共数据源配置: {source_id} ({market})")

        result = await self.system_repo.delete_config(source_id, market)

        if result:
            logger.info(f"系统公共数据源配置删除成功: {source_id}")
        else:
            logger.warning(f"系统公共数据源配置不存在: {source_id}")

        return bool(result)  # type: ignore[no-any-return]

    # ==================== 用户个人数据源配置 ====================

    async def create_user_source(
        self,
        user_id: str,
        source_id: str,
        market: str,
        enabled: bool = True,
        priority: int = 1,
        config: dict | None = None,
    ) -> UserDataSourceConfig:
        """创建用户个人数据源配置

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型
            enabled: 是否启用
            priority: 优先级
            config: 配置信息

        Returns:
            创建的配置对象
        """
        logger.info(f"创建用户个人数据源配置: user_id={user_id}, source_id={source_id}")

        source_config = UserDataSourceConfig(
            user_id=user_id,
            source_id=source_id,
            market=market,
            enabled=enabled,
            priority=priority,
            config=config or {},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await self.user_repo.upsert_config(source_config)
        logger.info(f"用户个人数据源配置创建成功: {source_id}")
        return source_config

    async def get_user_source(
        self, user_id: str, source_id: str, market: str
    ) -> UserDataSourceConfig | None:
        """获取用户个人数据源配置

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型

        Returns:
            配置对象，不存在时返回 None
        """
        config_dict = await self.user_repo.get_config(user_id, source_id, market)
        if config_dict:
            return UserDataSourceConfig(**config_dict)
        return None

    async def list_user_sources(
        self,
        user_id: str,
        market: str | None = None,
        enabled_only: bool = False,
    ) -> list[UserDataSourceConfig]:
        """列出用户个人数据源配置

        Args:
            user_id: 用户ID
            market: 市场类型过滤
            enabled_only: 是否只返回启用的配置

        Returns:
            配置列表
        """
        config_dicts = await self.user_repo.get_user_configs(user_id, market, enabled_only)
        return [UserDataSourceConfig(**c) for c in config_dicts]

    async def update_user_source(
        self,
        user_id: str,
        source_id: str,
        market: str,
        **updates: Any,
    ) -> bool:
        """更新用户个人数据源配置

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型
            **updates: 要更新的字段

        Returns:
            是否更新成功
        """
        logger.info(f"更新用户个人数据源配置: user_id={user_id}, source_id={source_id}")

        # Repository 没有 update_config 方法，需要使用 upsert 或者直接操作 collection
        filter_query = {"user_id": user_id, "source_id": source_id, "market": market}
        updates["updated_at"] = datetime.now()
        result = await self.user_repo.collection.update_one(filter_query, {"$set": updates})

        if result.modified_count > 0:
            logger.info(f"用户个人数据源配置更新成功: {source_id}")
            return True
        else:
            logger.warning(f"用户个人数据源配置不存在: {source_id}")
            return False

    async def delete_user_source(self, user_id: str, source_id: str, market: str) -> bool:
        """删除用户个人数据源配置

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型

        Returns:
            是否删除成功
        """
        logger.info(f"删除用户个人数据源配置: user_id={user_id}, source_id={source_id}")

        result = await self.user_repo.delete_config(user_id, source_id, market)

        if result:
            logger.info(f"用户个人数据源配置删除成功: {source_id}")
        else:
            logger.warning(f"用户个人数据源配置不存在: {source_id}")

        return bool(result)  # type: ignore[no-any-return]

    # ==================== 配置测试 ====================

    async def test_system_source(self, source_id: str, market: str) -> dict:
        """测试系统公共数据源连接

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            测试结果，包含 success, message, response_time 等字段
        """
        import time

        logger.info(f"测试系统公共数据源连接: {source_id} ({market})")

        config = await self.get_system_source(source_id, market)
        if not config:
            return {
                "success": False,
                "message": f"数据源配置不存在: {source_id}",
                "response_time": None,
            }

        # 根据数据源类型创建适配器并测试连接
        try:
            adapter = self._create_adapter_for_source(
                source_id, config.config if hasattr(config, "config") else {}, market
            )
            if adapter is None:
                return {
                    "success": False,
                    "message": f"不支持的数据源类型: {source_id}",
                    "response_time": None,
                }

            # 执行连接测试
            start_time = time.time()
            is_connected = await adapter.test_connection()
            response_time = int((time.time() - start_time) * 1000)

            if is_connected:
                result = {
                    "success": True,
                    "message": "连接测试成功",
                    "response_time": response_time,
                }
                logger.info(
                    f"系统公共数据源连接测试完成: {source_id}, "
                    f"success=True, response_time={response_time}ms"
                )
            else:
                result = {
                    "success": False,
                    "message": "连接测试失败",
                    "response_time": response_time,
                }
                logger.warning(
                    f"系统公共数据源连接测试失败: {source_id}, response_time={response_time}ms"
                )

        except Exception as e:
            result = {
                "success": False,
                "message": f"连接测试异常: {str(e)}",
                "response_time": None,
            }
            logger.error(f"系统公共数据源连接测试异常: {source_id}, error={e}")

        return result

    async def test_user_source(self, user_id: str, source_id: str, market: str) -> dict:
        """测试用户个人数据源连接

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型

        Returns:
            测试结果
        """
        import time

        logger.info(f"测试用户个人数据源连接: user_id={user_id}, source_id={source_id}")

        config = await self.get_user_source(user_id, source_id, market)
        if not config:
            return {
                "success": False,
                "message": f"数据源配置不存在: {source_id}",
                "response_time": None,
            }

        # 根据数据源类型创建适配器并测试连接
        try:
            adapter = self._create_adapter_for_source(
                source_id, config.config if hasattr(config, "config") else {}, market
            )
            if adapter is None:
                return {
                    "success": False,
                    "message": f"不支持的数据源类型: {source_id}",
                    "response_time": None,
                }

            # 执行连接测试
            start_time = time.time()
            is_connected = await adapter.test_connection()
            response_time = int((time.time() - start_time) * 1000)

            if is_connected:
                result = {
                    "success": True,
                    "message": "连接测试成功",
                    "response_time": response_time,
                }
                logger.info(
                    f"用户个人数据源连接测试完成: {source_id}, "
                    f"success=True, response_time={response_time}ms"
                )
            else:
                result = {
                    "success": False,
                    "message": "连接测试失败",
                    "response_time": response_time,
                }
                logger.warning(
                    f"用户个人数据源连接测试失败: {source_id}, response_time={response_time}ms"
                )

        except Exception as e:
            result = {
                "success": False,
                "message": f"连接测试异常: {str(e)}",
                "response_time": None,
            }
            logger.error(f"用户个人数据源连接测试异常: {source_id}, error={e}")

        return result

    def _create_adapter_for_source(self, source_id: str, config: dict, market: str) -> Any:
        """
        根据数据源ID创建适配器实例

        Args:
            source_id: 数据源标识
            config: 配置信息
            market: 市场类型

        Returns:
            数据源适配器实例，不支持的数据源返回 None
        """
        from core.market_data.models import MarketType

        try:
            market_type = MarketType(market)

            # A股数据源
            if market_type == MarketType.A_STOCK:
                if source_id == "tushare":
                    from core.market_data.sources.a_stock.tushare_adapter import TuShareAdapter

                    return TuShareAdapter(config=config)
                elif source_id == "akshare":
                    from core.market_data.sources.a_stock.akshare_adapter import AkShareAdapter

                    return AkShareAdapter(config=config)

            # 美股数据源
            elif market_type == MarketType.US_STOCK:
                if source_id == "yahoo":
                    from core.market_data.sources.us_stock.yahoo_adapter import YahooFinanceAdapter

                    return YahooFinanceAdapter(config=config)
                elif source_id == "alpha_vantage":
                    from core.market_data.sources.us_stock.alphavantage_adapter import (
                        AlphaVantageAdapter,
                    )

                    return AlphaVantageAdapter(config=config)

            # 港股数据源
            elif market_type == MarketType.HK_STOCK:
                if source_id == "yahoo":
                    from core.market_data.sources.hk_stock.yahoo_adapter import YahooHKAdapter

                    return YahooHKAdapter(config=config)
                elif source_id == "akshare":
                    from core.market_data.sources.hk_stock.akshare_adapter import AkShareHKAdapter

                    return AkShareHKAdapter(config=config)

            logger.warning(f"Unsupported data source: {source_id} for market: {market}")
            return None

        except Exception as e:
            logger.error(f"Failed to create adapter for {source_id}: {e}")
            return None


# 便捷函数：获取服务实例
def get_config_service() -> DataSourceConfigService:
    """获取配置服务实例

    Returns:
        配置服务实例
    """
    return DataSourceConfigService()
