from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    database = None

    @classmethod
    async def connect_to_mongodb(cls, connection_string: str, database_name: str):
        """连接到MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(connection_string)
            cls.database = cls.client[database_name]

            # 测试连接
            await cls.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            return True
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False

    @classmethod
    async def close_mongodb_connection(cls):
        """关闭MongoDB连接"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")

    @classmethod
    def get_database(cls):
        """获取数据库实例"""
        if not cls.database:
            raise RuntimeError("Database not initialized. Call connect_to_mongodb first.")
        return cls.database

    @classmethod
    async def create_indexes(cls):
        """创建必要的索引"""
        db = cls.get_database()

        # 用户集合索引
        await db.users.create_index("email", unique=True)
        await db.users.create_index("username", unique=True)

        logger.info("MongoDB indexes created successfully")


# 全局MongoDB实例
mongodb = MongoDB()