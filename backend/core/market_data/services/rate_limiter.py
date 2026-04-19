"""
限流服务

基于 Redis 的限流实现，按 symbol + data_type 粒度限流，1分钟时间窗口。
用于双通道数据流的通道2限流控制。
"""

import logging
from datetime import datetime
from typing import Any, Optional

from core.config import (
    DATA_SOURCE_RATE_LIMIT_MAX_REQUESTS,
    DATA_SOURCE_RATE_LIMIT_WINDOW,
)

logger = logging.getLogger(__name__)


# Lua 脚本：原子性地执行 incr 和 expire 操作
# 返回值：当前计数
INCR_AND_EXPIRE_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


class RateLimiter:
    """
    限流服务

    按 symbol + data_type 粒度进行限流，1分钟时间窗口。
    支持内存和 Redis 两种实现方式。

    Redis 实现使用 Lua 脚本确保 incr 和 expire 操作的原子性。
    """

    def __init__(
        self,
        redis_client: Any = None,
        window_seconds: int | None = None,
        max_requests: int | None = None,
    ):
        """
        初始化限流服务

        Args:
            redis_client: Redis 客户端（可选，不传则使用内存存储）
            window_seconds: 时间窗口（秒），默认从配置读取
            max_requests: 时间窗口内最大请求数，默认从配置读取
        """
        self.redis = redis_client
        # 使用配置文件中的默认值
        self.window_seconds = (
            window_seconds if window_seconds is not None else DATA_SOURCE_RATE_LIMIT_WINDOW
        )
        self.max_requests = (
            max_requests if max_requests is not None else DATA_SOURCE_RATE_LIMIT_MAX_REQUESTS
        )
        self._memory_store: dict[str, dict[str, Any]] = {}  # 内存存储（用于无 Redis 的情况）
        self._lua_script = None  # Lua 脚本缓存

    async def _get_lua_script(self) -> Any:
        """获取或注册 Lua 脚本"""
        if self._lua_script is None:
            self._lua_script = await self.redis.register_script(INCR_AND_EXPIRE_SCRIPT)
        return self._lua_script

    def _make_key(self, symbol: str, data_type: str) -> str:
        """
        生成限流键

        Args:
            symbol: 股票代码
            data_type: 数据类型

        Returns:
            限流键
        """
        return f"rate_limiter:{symbol}:{data_type}"

    async def is_allowed(self, symbol: str, data_type: str) -> bool:
        """
        检查是否允许访问

        Args:
            symbol: 股票代码
            data_type: 数据类型（如 quote、financial、company 等）

        Returns:
            True 表示允许访问，False 表示被限流
        """
        key = self._make_key(symbol, data_type)

        if self.redis:
            return await self._check_redis(key)
        else:
            return await self._check_memory(key)

    async def _check_redis(self, key: str) -> bool:
        """
        使用 Redis 检查限流（使用 Lua 脚本确保原子性）

        Args:
            key: 限流键

        Returns:
            是否允许访问
        """
        try:
            # 使用 Lua 脚本原子性地执行 incr 和 expire
            script = await self._get_lua_script()
            current = await script(keys=[key], args=[self.window_seconds])

            if current <= self.max_requests:
                logger.debug(
                    f"Rate limiter: allowed key={key}, count={current}/{self.max_requests}"
                )
                return True
            else:
                # 获取剩余时间
                ttl = await self.redis.ttl(key)
                logger.debug(
                    f"Rate limiter: blocked key={key}, "
                    f"count={current}/{self.max_requests}, ttl={ttl}s"
                )
                return False

        except Exception as e:
            logger.error(f"Redis rate limiter error: {e}")
            # Redis 出错时降级为允许访问
            return True

    async def _check_memory(self, key: str) -> bool:
        """
        使用内存检查限流

        Args:
            key: 限流键

        Returns:
            是否允许访问
        """
        now = datetime.now()

        # 清理过期记录
        self._cleanup_memory()

        if key not in self._memory_store:
            self._memory_store[key] = {
                "count": 1,
                "first_request": now,
            }
            logger.debug(f"Rate limiter (memory): allowed key={key}, count=1/{self.max_requests}")
            return True

        record = self._memory_store[key]

        # 检查是否在时间窗口内
        time_diff = (now - record["first_request"]).total_seconds()

        if time_diff > self.window_seconds:
            # 超过时间窗口，重置计数
            record["count"] = 1
            record["first_request"] = now
            logger.debug(f"Rate limiter (memory): window expired, reset key={key}")
            return True

        # 在时间窗口内
        if record["count"] < self.max_requests:
            record["count"] += 1
            logger.debug(
                f"Rate limiter (memory): allowed key={key}, "
                f"count={record['count']}/{self.max_requests}"
            )
            return True
        else:
            logger.debug(
                f"Rate limiter (memory): blocked key={key}, "
                f"count={record['count']}/{self.max_requests}, "
                f"remaining_time={self.window_seconds - time_diff:.1f}s"
            )
            return False

    def _cleanup_memory(self) -> None:
        """清理内存中过期的限流记录"""
        now = datetime.now()
        expired_keys = []

        for key, record in self._memory_store.items():
            time_diff = (now - record["first_request"]).total_seconds()
            if time_diff > self.window_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del self._memory_store[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit records")

    async def reset(self, symbol: str, data_type: str) -> bool:
        """
        重置限流计数

        Args:
            symbol: 股票代码
            data_type: 数据类型

        Returns:
            是否成功重置
        """
        key = self._make_key(symbol, data_type)

        if self.redis:
            try:
                await self.redis.delete(key)
                logger.debug(f"Rate limiter: reset key={key}")
                return True
            except Exception as e:
                logger.error(f"Redis reset error: {e}")
                return False
        else:
            if key in self._memory_store:
                del self._memory_store[key]
                logger.debug(f"Rate limiter (memory): reset key={key}")
                return True
            return False

    async def get_remaining_time(self, symbol: str, data_type: str) -> int:
        """
        获取限流剩余时间（秒）

        Args:
            symbol: 股票代码
            data_type: 数据类型

        Returns:
            剩余时间（秒），0 表示无限制
        """
        key = self._make_key(symbol, data_type)

        if self.redis:
            try:
                ttl = await self.redis.ttl(key)
                return max(0, int(ttl))
            except Exception as e:
                logger.error(f"Redis get remaining time error: {e}")
                return 0
        else:
            if key in self._memory_store:
                record = self._memory_store[key]
                now = datetime.now()
                time_diff = (now - record["first_request"]).total_seconds()
                remaining = self.window_seconds - time_diff
                return max(0, int(remaining))
            return 0

    async def check_and_increment(self, symbol: str, data_type: str) -> tuple[bool, int]:
        """
        检查并增加计数（使用 Lua 脚本确保原子操作）

        Args:
            symbol: 股票代码
            data_type: 数据类型

        Returns:
            (是否允许, 当前计数)
        """
        key = self._make_key(symbol, data_type)

        if self.redis:
            try:
                # 使用 Lua 脚本原子性地执行 incr 和 expire
                script = await self._get_lua_script()
                current = await script(keys=[key], args=[self.window_seconds])

                allowed = current <= self.max_requests
                if not allowed:
                    ttl = await self.redis.ttl(key)
                    logger.debug(
                        f"Rate limiter: blocked key={key}, "
                        f"count={current}/{self.max_requests}, ttl={ttl}s"
                    )
                return allowed, current
            except Exception as e:
                logger.error(f"Redis rate limiter error: {e}")
                return True, 0
        else:
            now = datetime.now()
            self._cleanup_memory()

            if key not in self._memory_store:
                self._memory_store[key] = {
                    "count": 1,
                    "first_request": now,
                }
                return True, 1

            record = self._memory_store[key]
            time_diff = (now - record["first_request"]).total_seconds()

            if time_diff > self.window_seconds:
                record["count"] = 1
                record["first_request"] = now
                return True, 1

            if record["count"] < self.max_requests:
                record["count"] += 1
                return True, record["count"]
            else:
                return False, record["count"]


# 全局限流器实例
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(redis_client: Any = None) -> RateLimiter:
    """
    获取全局限流器实例

    Args:
        redis_client: Redis 客户端（可选）

    Returns:
        限流器实例
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(redis_client=redis_client)
        logger.info("Created global rate limiter")
    return _global_rate_limiter
