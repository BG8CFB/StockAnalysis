"""
MongoDB 数据库连接管理
使用 Motor 进行异步操作
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None


class MongoDB:
    """MongoDB 连接管理器"""

    def __init__(self) -> None:
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None

    def connect(self) -> None:
        """建立数据库连接"""
        if self._client is None:
            self._client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
                connectTimeoutMS=60000,  # 使用 60 秒连接超时
                socketTimeoutMS=settings.MONGODB_SOCKET_TIMEOUT_MS,  # 使用配置的 Socket 超时
                retryWrites=True,
                w="majority",
            )
            self._database = self._client[settings.MONGODB_DATABASE]

    def close(self) -> None:
        """关闭数据库连接"""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None

    @property
    def client(self) -> AsyncIOMotorClient:
        """获取 MongoDB 客户端"""
        if self._client is None:
            raise RuntimeError("MongoDB client not initialized. Call connect() first.")
        return self._client

    @property
    def database(self) -> AsyncIOMotorDatabase:
        """获取数据库实例"""
        if self._database is None:
            raise RuntimeError("MongoDB database not initialized. Call connect() first.")
        return self._database

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """获取集合"""
        return self.database[name]

    @asynccontextmanager
    async def transaction(self) -> Any:
        """
        事务上下文管理器

        使用示例:
            async with mongodb.transaction() as session:
                await collection.insert_one(doc, session=session)
                await collection.update_one(filter, update, session=session)

        Yields:
            AsyncIOMotorClientSession: MongoDB 会话对象
        """
        if self._client is None:
            raise RuntimeError("MongoDB client not initialized. Call connect() first.")

        async with await self._client.start_session() as session:
            try:
                async with session.start_transaction():
                    yield session
            except Exception as e:
                logger.error(f"Transaction failed: {e}")
                raise


# 全局 MongoDB 实例
mongodb = MongoDB()


async def get_mongodb() -> AsyncGenerator[MongoDB, None]:
    """依赖注入：获取 MongoDB 实例"""
    yield mongodb


async def init_indexes() -> None:
    """初始化数据库索引"""
    db = mongodb.database

    # 用户集合索引
    await db.users.create_index("email", unique=True)
    await db.users.create_index("created_at")

    # 用户配置集合索引 - 必须有 user_id
    await db.user_preferences.create_index([("user_id", 1)], unique=False)
    await db.user_preferences.create_index([("user_id", 1), ("key", 1)], unique=True)

    # 会话存储使用 Redis，无需 MongoDB sessions 集合

    logger.debug("MongoDB indexes initialized successfully")


async def connect_to_mongodb() -> None:
    """启动时连接数据库"""
    mongodb.connect()
    await init_indexes()
    logger.info(f"Connected to MongoDB: {settings.MONGODB_URL}")


async def close_mongodb() -> None:
    """关闭时断开数据库连接"""
    mongodb.close()
    logger.info("Closed MongoDB connection")
