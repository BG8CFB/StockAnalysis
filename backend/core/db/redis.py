import redis.asyncio as redis
from typing import Optional, Any, Union
import json
import logging

logger = logging.getLogger(__name__)


class RedisConnection:
    client: Optional[redis.Redis] = None

    @classmethod
    async def connect_to_redis(cls, connection_string: str):
        """连接到Redis"""
        try:
            cls.client = redis.from_url(connection_string, decode_responses=True)

            # 测试连接
            await cls.client.ping()
            logger.info("Successfully connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    @classmethod
    async def close_redis_connection(cls):
        """关闭Redis连接"""
        if cls.client:
            await cls.client.close()
            logger.info("Redis connection closed")

    @classmethod
    def get_client(cls):
        """获取Redis客户端"""
        if not cls.client:
            raise RuntimeError("Redis not initialized. Call connect_to_redis first.")
        return cls.client

    @classmethod
    async def set(cls, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置键值对"""
        try:
            client = cls.get_client()
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            return await client.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """获取值"""
        try:
            client = cls.get_client()
            value = await client.get(key)

            if value is None:
                return None

            # 尝试解析JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    @classmethod
    async def delete(cls, key: str) -> bool:
        """删除键"""
        try:
            client = cls.get_client()
            return bool(await client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    @classmethod
    async def exists(cls, key: str) -> bool:
        """检查键是否存在"""
        try:
            client = cls.get_client()
            return bool(await client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False


# 全局Redis实例
redis_connection = RedisConnection()