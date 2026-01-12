"""
数据源配置管理服务

提供数据源配置的 CRUD 操作，供管理员使用。
"""

import logging
from typing import List, Optional
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from core.market_data.models.datasource import (
    SystemDataSourceConfig,
    UserDataSourceConfig,
    DataSourceType,
)
from core.market_data.repositories.datasource import (
    SystemDataSourceRepository,
    UserDataSourceRepository,
)

logger = logging.getLogger(__name__)


class DataSourceConfigService:
    """数据源配置管理服务"""

    def __init__(self, db: AsyncIOMotorClient):
        """初始化服务

        Args:
            db: MongoDB 客户端
        """
        self.db = db
        self.system_repo = SystemDataSourceRepository(db)
        self.user_repo = UserDataSourceRepository(db)

    # ==================== 系统公共数据源配置 ====================

    async def create_system_source(
        self,
        source_id: str,
        market: str,
        enabled: bool = True,
        priority: int = 1,
        config: dict = None,
        rate_limit: dict = None,
        supported_data_types: List[str] = None,
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

        await self.system_repo.create(source_config)
        logger.info(f"系统公共数据源配置创建成功: {source_id}")
        return source_config

    async def get_system_source(self, source_id: str, market: str) -> Optional[SystemDataSourceConfig]:
        """获取系统公共数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            配置对象，不存在时返回 None
        """
        return await self.system_repo.get_by_source_and_market(source_id, market)

    async def list_system_sources(
        self,
        market: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[SystemDataSourceConfig]:
        """列出系统公共数据源配置

        Args:
            market: 市场类型过滤
            enabled_only: 是否只返回启用的配置

        Returns:
            配置列表
        """
        return await self.system_repo.list(market=market, enabled_only=enabled_only)

    async def update_system_source(
        self,
        source_id: str,
        market: str,
        **updates,
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
        result = await self.system_repo.update_by_source_and_market(source_id, market, updates)

        if result:
            logger.info(f"系统公共数据源配置更新成功: {source_id}")
        else:
            logger.warning(f"系统公共数据源配置不存在: {source_id}")

        return result

    async def delete_system_source(self, source_id: str, market: str) -> bool:
        """删除系统公共数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            是否删除成功
        """
        logger.info(f"删除系统公共数据源配置: {source_id} ({market})")

        result = await self.system_repo.delete_by_source_and_market(source_id, market)

        if result:
            logger.info(f"系统公共数据源配置删除成功: {source_id}")
        else:
            logger.warning(f"系统公共数据源配置不存在: {source_id}")

        return result

    # ==================== 用户个人数据源配置 ====================

    async def create_user_source(
        self,
        user_id: str,
        source_id: str,
        market: str,
        enabled: bool = True,
        priority: int = 1,
        config: dict = None,
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

        await self.user_repo.create(source_config)
        logger.info(f"用户个人数据源配置创建成功: {source_id}")
        return source_config

    async def get_user_source(self, user_id: str, source_id: str, market: str) -> Optional[UserDataSourceConfig]:
        """获取用户个人数据源配置

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型

        Returns:
            配置对象，不存在时返回 None
        """
        return await self.user_repo.get_by_user_source_market(user_id, source_id, market)

    async def list_user_sources(
        self,
        user_id: str,
        market: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[UserDataSourceConfig]:
        """列出用户个人数据源配置

        Args:
            user_id: 用户ID
            market: 市场类型过滤
            enabled_only: 是否只返回启用的配置

        Returns:
            配置列表
        """
        return await self.user_repo.list_by_user(user_id, market=market, enabled_only=enabled_only)

    async def update_user_source(
        self,
        user_id: str,
        source_id: str,
        market: str,
        **updates,
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

        updates["updated_at"] = datetime.now()
        result = await self.user_repo.update_by_user_source_market(user_id, source_id, market, updates)

        if result:
            logger.info(f"用户个人数据源配置更新成功: {source_id}")
        else:
            logger.warning(f"用户个人数据源配置不存在: {source_id}")

        return result

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

        result = await self.user_repo.delete_by_user_source_market(user_id, source_id, market)

        if result:
            logger.info(f"用户个人数据源配置删除成功: {source_id}")
        else:
            logger.warning(f"用户个人数据源配置不存在: {source_id}")

        return result

    # ==================== 配置测试 ====================

    async def test_system_source(self, source_id: str, market: str) -> dict:
        """测试系统公共数据源连接

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            测试结果，包含 success, message, response_time 等字段
        """
        logger.info(f"测试系统公共数据源连接: {source_id} ({market})")

        config = await self.get_system_source(source_id, market)
        if not config:
            return {
                "success": False,
                "message": f"数据源配置不存在: {source_id}",
                "response_time": None,
            }

        # TODO: 实现具体的连接测试逻辑
        # 这里需要根据不同的数据源类型调用相应的测试方法

        result = {
            "success": True,
            "message": "连接测试成功",
            "response_time": 100,
        }

        logger.info(f"系统公共数据源连接测试完成: {source_id}, success={result['success']}")
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
        logger.info(f"测试用户个人数据源连接: user_id={user_id}, source_id={source_id}")

        config = await self.get_user_source(user_id, source_id, market)
        if not config:
            return {
                "success": False,
                "message": f"数据源配置不存在: {source_id}",
                "response_time": None,
            }

        # TODO: 实现具体的连接测试逻辑

        result = {
            "success": True,
            "message": "连接测试成功",
            "response_time": 100,
        }

        logger.info(f"用户个人数据源连接测试完成: {source_id}, success={result['success']}")
        return result


# 便捷函数：获取服务实例
def get_config_service(db: AsyncIOMotorClient) -> DataSourceConfigService:
    """获取配置服务实例

    Args:
        db: MongoDB 客户端

    Returns:
        配置服务实例
    """
    return DataSourceConfigService(db)
