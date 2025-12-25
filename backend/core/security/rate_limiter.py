"""
Redis 滑动窗口限流器
基于 Redis Sorted Set 实现高效的滑动窗口限流算法
参考: https://upstash.com/blog/rate-limiting-with-python
"""
import logging
import time
from functools import wraps
from typing import Optional

from fastapi import HTTPException, Request, status

from core.config import settings
from core.db.redis import get_redis

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """限流异常"""

    def __init__(
        self,
        detail: str = "请求过于频繁，请稍后再试",
        retry_after: Optional[int] = None,
    ):
        headers = {}
        if retry_after is not None:
            headers["Retry-After"] = str(retry_after)
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
        )


class RateLimiter:
    """滑动窗口限流器

    使用 Redis Sorted Set 实现滑动窗口限流：
    - 将每个请求的时间戳作为 score 存入 Sorted Set
    - 移除窗口外的旧记录
    - 统计当前窗口内的请求数
    """

    def __init__(self):
        self._redis = None

    async def _get_redis(self):
        """获取 Redis 客户端"""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """检查是否允许请求

        Args:
            key: 限流键（如 IP、用户ID 等）
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）

        Returns:
            (是否允许, 剩余重试秒数)
        """
        redis = await self._get_redis()
        now = time.time()
        window_start = now - window_seconds

        try:
            # 使用 pipeline 减少网络往返
            pipe = redis.pipeline()

            # 移除窗口外的记录
            pipe.zremrangebyscore(key, 0, window_start)

            # 统计当前窗口内的请求数
            pipe.zcard(key)

            # 添加当前请求
            pipe.zadd(key, {str(now): now})

            # 设置过期时间（窗口时间 + 1秒，避免永久存储）
            pipe.expire(key, window_seconds + 1)

            results = await pipe.execute()
            current_count = results[1]

            if current_count >= max_requests:
                # 计算最早请求的剩余时间
                earliest = await redis.zrange(key, 0, 0, withscores=True)
                if earliest:
                    retry_after = int(earliest[0][1] + window_seconds - now) + 1
                    return False, retry_after
                return False, window_seconds

            return True, 0

        except Exception as e:
            # Redis 故障时降级：允许请求通过
            logger.warning(f"Rate limiter error, allowing request: {e}")
            return True, 0

    async def reset(self, key: str) -> None:
        """重置限流计数"""
        redis = await self._get_redis()
        await redis.delete(key)

    async def get_count(self, key: str) -> int:
        """获取当前计数"""
        redis = await self._get_redis()
        return await redis.zcard(key)


# 预定义的限流配置
class RateLimitConfig:
    """限流配置常量"""

    # 登录相关
    LOGIN_ATTEMPTS = 5
    LOGIN_WINDOW = 60  # 5次/分钟

    # 注册相关
    REGISTER_ATTEMPTS = 3
    REGISTER_WINDOW = 3600  # 3次/小时

    # 图形验证码
    CAPTCHA_GENERATE = 10
    CAPTCHA_WINDOW = 60  # 10次/分钟

    # 邮箱验证码
    EMAIL_CODE_ATTEMPTS = 1
    EMAIL_CODE_WINDOW = 60  # 1次/分钟

    # 通用 API
    API_REQUESTS = 100
    API_WINDOW = 60  # 100次/分钟


def rate_limit(
    key_func: callable,
    max_requests: int,
    window_seconds: int,
):
    """限流装饰器工厂

    Args:
        key_func: 生成限流键的函数，接收 Request 参数
        max_requests: 最大请求数
        window_seconds: 时间窗口（秒）

    Example:
        @rate_limit(lambda r: f"login:{r.client.host}", 5, 60)
        async def login(): ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中获取 Request
            request: Optional[Request] = kwargs.get("request")
            if not request:
                # 尝试从位置参数获取
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                # 没有 Request 对象，直接执行
                return await func(*args, **kwargs)

            key = key_func(request)
            limiter = get_rate_limiter()
            allowed, retry_after = await limiter.is_allowed(
                key, max_requests, window_seconds
            )

            if not allowed:
                raise RateLimitExceeded(
                    detail=f"请求过于频繁，请 {retry_after} 秒后再试",
                    retry_after=retry_after,
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP

    优先从代理头获取，考虑各种代理场景
    """
    # 检查代理头
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For 可能包含多个 IP，取第一个
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    cf_connecting_ip = request.headers.get("CF-Connecting-IP")
    if cf_connecting_ip:
        return cf_connecting_ip

    # 回退到直接连接的 IP
    if request.client:
        return request.client.host

    return "unknown"


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取限流器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
