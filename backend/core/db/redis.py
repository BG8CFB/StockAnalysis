"""
Redis 连接管理
用于缓存、会话管理和限流
"""
import logging
from typing import Optional

from redis.asyncio import Redis as AsyncRedis

from core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis 连接管理器"""

    def __init__(self) -> None:
        self._client: Optional[AsyncRedis] = None

    def connect(self) -> None:
        """建立 Redis 连接"""
        if self._client is None:
            self._client = AsyncRedis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            )

    def close(self) -> None:
        """关闭 Redis 连接"""
        if self._client:
            # 简单地断开连接
            self._client = None

    async def ping(self) -> bool:
        """检查 Redis 连接状态"""
        try:
            if self._client:
                await self._client.ping()
                return True
            return False
        except Exception as e:
            logger.error(f"Redis ping 失败: {e}")
            return False

    def get_client(self) -> AsyncRedis:
        """获取 Redis 客户端"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._client


# 全局 Redis 管理器实例
redis_manager = RedisManager()


async def get_redis() -> AsyncRedis:
    """依赖注入：获取 Redis 客户端"""
    return redis_manager.get_client()


class UserRedisKey:
    """用户相关的 Redis Key 生成器"""

    @staticmethod
    def session(user_id: str, session_id: str) -> str:
        """会话 Key"""
        return f"user:{user_id}:session:{session_id}"

    @staticmethod
    def preferences(user_id: str) -> str:
        """用户配置 Key"""
        return f"user:{user_id}:preferences"

    @staticmethod
    def cache(user_id: str, key: str) -> str:
        """用户缓存 Key"""
        return f"user:{user_id}:cache:{key}"

    @staticmethod
    def rate_limit(ip: str) -> str:
        """限流 Key"""
        return f"rate_limit:ip:{ip}"

    @staticmethod
    def email_verification(email: str) -> str:
        """邮箱验证码 Key"""
        return f"email:verify:{email}"

    # ==================== 安全相关 Key ====================

    @staticmethod
    def login_failures_ip(ip: str) -> str:
        """IP 登录失败计数"""
        return f"auth:login:failures:ip:{ip}"

    @staticmethod
    def login_failures_email(email: str) -> str:
        """邮箱登录失败计数"""
        return f"auth:login:failures:email:{email}"

    @staticmethod
    def login_blocked_ip(ip: str) -> str:
        """IP 登录封禁标记"""
        return f"auth:login:blocked:ip:{ip}"

    @staticmethod
    def register_attempts_ip(ip: str) -> str:
        """IP 注册尝试计数"""
        return f"auth:register:attempts:ip:{ip}"

    @staticmethod
    def trusted_ips(user_id: str) -> str:
        """用户信任 IP 集合"""
        return f"ip_trust:user:{user_id}:trusted_ips"

    @staticmethod
    def ip_login_count(user_id: str, ip: str) -> str:
        """IP 登录该用户的次数"""
        return f"ip_trust:user:{user_id}:ip:{ip}:logins"


async def connect_to_redis() -> None:
    """启动时连接 Redis"""
    redis_manager.connect()
    is_connected = await redis_manager.ping()
    if is_connected:
        logger.info(f"Connected to Redis: {settings.REDIS_URL}")
    else:
        logger.error("Redis connection failed")


async def close_redis() -> None:
    """关闭时断开 Redis 连接"""
    redis_manager.close()
    logger.info("Closed Redis connection")
