"""
Redis 滑动窗口限流器
基于 Redis Sorted Set 实现高效的滑动窗口限流算法
参考: https://upstash.com/blog/rate-limiting-with-python

降级策略说明：
- 当 Redis 不可用时，使用本地内存限流作为降级方案
- 本地限流使用简单的字典存储，仅作为应急措施
- 记录错误日志并告警，提醒运维人员处理
"""

import asyncio
import logging
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Optional

from fastapi import HTTPException, Request, status

from core.db.redis import get_redis

logger = logging.getLogger(__name__)

# 本地限流存储（Redis 不可用时的降级方案）
_local_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_local_rate_limit_lock = asyncio.Lock()


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

    降级策略：
    - 当 Redis 不可用时，自动切换到本地内存限流
    - 本地限流仅作为应急措施，不保证多实例一致性
    """

    def __init__(self) -> None:
        self._redis: Optional[Any] = None
        self._redis_available: bool = True
        self._last_redis_error_time: float = 0.0

    async def _get_redis(self) -> Any:
        """获取 Redis 客户端"""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def _check_local_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """本地限流检查（Redis 不可用时的降级方案）"""
        async with _local_rate_limit_lock:
            now = time.time()
            window_start = now - window_seconds

            # 获取该 key 的请求列表
            requests = _local_rate_limit_store[key]

            # 移除窗口外的请求
            requests[:] = [t for t in requests if t > window_start]

            # 检查是否超过限制
            if len(requests) >= max_requests:
                # 计算最早请求的剩余时间
                if requests:
                    retry_after = int(requests[0] + window_seconds - now) + 1
                    return False, max(1, retry_after)
                return False, window_seconds

            # 添加当前请求
            requests.append(now)
            return True, 0

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
            # 第一步：清理窗口外的旧记录并检查当前计数（不记录当前请求）
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = await pipe.execute()
            current_count = results[1]

            if current_count >= max_requests:
                # 被拒绝：不将当前请求加入计数，避免越拒绝越锁死
                earliest = await redis.zrange(key, 0, 0, withscores=True)
                if earliest:
                    retry_after = int(earliest[0][1] + window_seconds - now) + 1
                    return False, max(1, retry_after)
                return False, window_seconds

            # 第二步：仅在允许时才记录当前请求
            pipe2 = redis.pipeline()
            pipe2.zadd(key, {str(now): now})
            pipe2.expire(key, window_seconds + 1)
            await pipe2.execute()

            return True, 0

        except Exception as e:
            # Redis 故障时降级到本地限流
            now = time.time()

            # 每 60 秒记录一次告警日志
            if now - self._last_redis_error_time > 60:
                logger.error(
                    f"Rate limiter Redis error, falling back to local rate limiting: {e}. "
                    "This is a degraded mode and may not work correctly "
                    "in multi-instance deployments."
                )
                self._last_redis_error_time = now

            self._redis_available = False
            return await self._check_local_rate_limit(key, max_requests, window_seconds)

    async def reset(self, key: str) -> None:
        """重置限流计数"""
        redis = await self._get_redis()
        await redis.delete(key)

    async def get_count(self, key: str) -> int:
        """获取当前计数"""
        redis = await self._get_redis()
        return int(await redis.zcard(key))


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
    key_func: Callable[[Any], str],
    max_requests: int,
    window_seconds: int,
) -> Callable[..., Any]:
    """限流装饰器工厂

    Args:
        key_func: 生成限流键的函数，接收 Request 参数
        max_requests: 最大请求数
        window_seconds: 时间窗口（秒）

    Example:
        @rate_limit(lambda r: f"login:{r.client.host}", 5, 60)
        async def login(): ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 从 kwargs 中获取 Request
            request: Optional[Any] = kwargs.get("request")
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
            allowed, retry_after = await limiter.is_allowed(key, max_requests, window_seconds)

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

    仅在来自可信代理 IP 时才信任 X-Forwarded-For，防止客户端伪造。
    可信代理通过 TRUSTED_PROXIES 环境变量配置。
    """
    from core.config import TRUSTED_PROXIES

    # 获取直接连接方的真实 IP
    direct_ip = request.client.host if request.client else None

    # 仅信任来自可信代理的转发头
    if direct_ip in TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For: client, proxy1, proxy2 —— 取最左侧的客户端 IP
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        cf_connecting_ip = request.headers.get("CF-Connecting-IP")
        if cf_connecting_ip:
            return cf_connecting_ip

    # 非可信代理或无代理头，直接使用连接 IP
    return direct_ip or "unknown"


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取限流器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
