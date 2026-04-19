"""
双通道数据流服务

实现双通道数据流逻辑：
- 通道1：直接返回，不存储，不限流
- 通道2：存入数据库，限流控制
- 降级逻辑：用户未配置实时数据源时降级到项目信息源
"""

import logging
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional

from .rate_limiter import RateLimiter, get_rate_limiter

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """通道类型"""

    DIRECT = "direct"  # 通道1：直接返回
    STORAGE = "storage"  # 通道2：存储
    FALLBACK = "fallback"  # 降级通道：项目信息源


class FallbackReason(str, Enum):
    """降级原因"""

    NO_USER_CONFIG = "no_user_config"  # 用户未配置实时数据源
    SOURCE_UNAVAILABLE = "source_unavailable"  # 数据源不可用
    RATE_LIMITED = "rate_limited"  # 限流
    FETCH_FAILED = "fetch_failed"  # 获取失败
    TIMEOUT = "timeout"  # 超时


class DualChannelResult:
    """双通道数据流结果"""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        channel_used: Optional[ChannelType] = None,
        stored: bool = False,
        rate_limited: bool = False,
        error: Optional[str] = None,
        fallback_used: bool = False,
        fallback_reason: Optional[FallbackReason] = None,
    ):
        self.success = success
        self.data = data
        self.channel_used = channel_used
        self.stored = stored
        self.rate_limited = rate_limited
        self.error = error
        self.fallback_used = fallback_used
        self.fallback_reason = fallback_reason

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "channel_used": self.channel_used.value if self.channel_used else None,
            "stored": self.stored,
            "rate_limited": self.rate_limited,
            "error": self.error,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason.value if self.fallback_reason else None,
        }


class DualChannelService:
    """
    双通道数据流服务

    负责管理双通道数据流的逻辑：
    - 通道1（direct）：直接返回，不存储，不限流
    - 通道2（storage）：存入数据库，限流控制
    - 降级通道（fallback）：当实时数据源不可用时，降级到项目信息源
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        storage_callback: Optional[Callable] = None,
        fallback_callback: Optional[Callable[[], Awaitable[Any]]] = None,
    ):
        """
        初始化双通道服务

        Args:
            rate_limiter: 限流器实例
            storage_callback: 存储回调函数（用于存储数据到数据库）
            fallback_callback: 降级回调函数（用于从项目信息源获取数据）
        """
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.storage_callback = storage_callback
        self.fallback_callback = fallback_callback

    async def fetch_with_dual_channel(
        self,
        symbol: str,
        data_type: str,
        fetch_func: Callable[[], Awaitable[Any]],
        use_channel1: bool = True,
        use_channel2: bool = True,
        fallback_func: Optional[Callable[[], Awaitable[Any]]] = None,
        has_user_config: bool = True,
    ) -> DualChannelResult:
        """
        使用双通道获取数据

        Args:
            symbol: 股票代码
            data_type: 数据类型（quote、financial、company 等）
            fetch_func: 数据获取函数
            use_channel1: 是否使用通道1（直接返回）
            use_channel2: 是否使用通道2（存储）
            fallback_func: 降级回调函数（从项目信息源获取数据）
            has_user_config: 用户是否配置了实时数据源

        Returns:
            双通道结果
        """
        # 如果用户未配置实时数据源，直接降级到项目信息源
        if not has_user_config:
            logger.info(f"User has no realtime config, fallback for {symbol}/{data_type}")
            return await self._try_fallback(
                symbol, data_type, fallback_func, FallbackReason.NO_USER_CONFIG
            )

        # 通道1：直接返回，不限流
        if use_channel1:
            try:
                logger.debug(f"Channel1 (direct): fetching data for {symbol}/{data_type}")
                data = await fetch_func()

                if data is not None:
                    logger.info(
                        f"Channel1 (direct): successfully fetched data for {symbol}/{data_type}"
                    )

                    # 通道1成功后，仍然尝试通道2（存储）
                    if use_channel2:
                        await self._try_channel2(symbol, data_type, data)

                    return DualChannelResult(
                        success=True,
                        data=data,
                        channel_used=ChannelType.DIRECT,
                        stored=False,
                    )
            except Exception as e:
                logger.warning(f"Channel1 (direct) failed for {symbol}/{data_type}: {e}")
                # 通道1失败，继续尝试通道2

        # 通道2：存入数据库，限流控制
        if use_channel2:
            result = await self._try_channel2(symbol, data_type, None, fetch_func)
            if result.success:
                return result

            # 通道2失败，尝试降级
            if result.rate_limited:
                return await self._try_fallback(
                    symbol, data_type, fallback_func, FallbackReason.RATE_LIMITED
                )

        # 所有通道都失败，尝试降级
        return await self._try_fallback(
            symbol, data_type, fallback_func, FallbackReason.FETCH_FAILED
        )

    async def _try_channel2(
        self,
        symbol: str,
        data_type: str,
        data: Any = None,
        fetch_func: Optional[Callable[[], Awaitable[Any]]] = None,
    ) -> DualChannelResult:
        """
        尝试通道2（存储）

        Args:
            symbol: 股票代码
            data_type: 数据类型
            data: 已获取的数据（如果有的话）
            fetch_func: 数据获取函数（如果没有数据）

        Returns:
            双通道结果
        """
        # 检查限流
        is_allowed, current_count = await self.rate_limiter.check_and_increment(symbol, data_type)

        if not is_allowed:
            remaining_time = await self.rate_limiter.get_remaining_time(symbol, data_type)
            logger.info(
                f"Channel2 (storage): rate limited for {symbol}/{data_type}, "
                f"remaining_time={remaining_time}s"
            )
            return DualChannelResult(
                success=False,
                rate_limited=True,
                error=f"Rate limited, remaining time: {remaining_time}s",
            )

        # 获取数据
        if data is None and fetch_func:
            try:
                logger.debug(f"Channel2 (storage): fetching data for {symbol}/{data_type}")
                data = await fetch_func()
            except Exception as e:
                logger.error(f"Channel2 (storage) fetch failed for {symbol}/{data_type}: {e}")
                return DualChannelResult(
                    success=False,
                    channel_used=ChannelType.STORAGE,
                    error=str(e),
                )

        if data is None:
            logger.warning(f"Channel2 (storage): no data for {symbol}/{data_type}")
            return DualChannelResult(
                success=False,
                channel_used=ChannelType.STORAGE,
                error="No data returned",
            )

        # 存储数据
        stored = False
        if self.storage_callback:
            try:
                logger.debug(f"Channel2 (storage): storing data for {symbol}/{data_type}")
                await self.storage_callback(symbol, data_type, data)
                stored = True
                logger.info(
                    f"Channel2 (storage): successfully stored data for {symbol}/{data_type}"
                )
            except Exception as e:
                logger.error(f"Channel2 (storage) store failed for {symbol}/{data_type}: {e}")

        return DualChannelResult(
            success=True,
            data=data,
            channel_used=ChannelType.STORAGE,
            stored=stored,
        )

    async def fetch_from_database(
        self, symbol: str, data_type: str, db_query_func: Callable[[], Awaitable[Any]]
    ) -> DualChannelResult:
        """
        从数据库获取数据（用于项目信息源）

        Args:
            symbol: 股票代码
            data_type: 数据类型
            db_query_func: 数据库查询函数

        Returns:
            双通道结果
        """
        try:
            logger.debug(f"Fetching from database: {symbol}/{data_type}")
            data = await db_query_func()

            if data is None or (isinstance(data, list) and len(data) == 0):
                logger.warning(f"No data found in database for {symbol}/{data_type}")
                return DualChannelResult(
                    success=False,
                    error="No data found in database",
                )

            logger.info(f"Successfully fetched from database: {symbol}/{data_type}")
            return DualChannelResult(
                success=True,
                data=data,
                channel_used=ChannelType.STORAGE,
                stored=True,
            )

        except Exception as e:
            logger.error(f"Failed to fetch from database for {symbol}/{data_type}: {e}")
            return DualChannelResult(
                success=False,
                error=str(e),
            )

    async def reset_rate_limit(self, symbol: str, data_type: str) -> bool:
        """
        重置限流计数

        Args:
            symbol: 股票代码
            data_type: 数据类型

        Returns:
            是否成功重置
        """
        return await self.rate_limiter.reset(symbol, data_type)

    async def _try_fallback(
        self,
        symbol: str,
        data_type: str,
        fallback_func: Optional[Callable[[], Awaitable[Any]]],
        reason: FallbackReason,
    ) -> DualChannelResult:
        """
        尝试降级到项目信息源

        Args:
            symbol: 股票代码
            data_type: 数据类型
            fallback_func: 降级回调函数
            reason: 降级原因

        Returns:
            双通道结果
        """
        # 使用传入的降级函数或全局降级回调
        callback = fallback_func or self.fallback_callback

        if not callback:
            logger.warning(
                f"No fallback available for {symbol}/{data_type}, reason: {reason.value}"
            )
            return DualChannelResult(
                success=False,
                error=f"No fallback available, reason: {reason.value}",
                fallback_used=False,
                fallback_reason=reason,
            )

        try:
            logger.info(
                f"Fallback: fetching from project source for "
                f"{symbol}/{data_type}, reason: {reason.value}"
            )
            data = await callback()

            if data is not None:
                logger.info(f"Fallback: successfully fetched data for {symbol}/{data_type}")
                return DualChannelResult(
                    success=True,
                    data=data,
                    channel_used=ChannelType.FALLBACK,
                    stored=True,  # 项目信息源数据已存储
                    fallback_used=True,
                    fallback_reason=reason,
                )

            logger.warning(f"Fallback: no data for {symbol}/{data_type}")
            return DualChannelResult(
                success=False,
                error="Fallback returned no data",
                fallback_used=True,
                fallback_reason=reason,
            )

        except Exception as e:
            logger.error(f"Fallback failed for {symbol}/{data_type}: {e}")
            return DualChannelResult(
                success=False,
                error=f"Fallback failed: {str(e)}",
                fallback_used=True,
                fallback_reason=reason,
            )

    def set_storage_callback(self, callback: Callable) -> None:
        """
        设置存储回调函数

        Args:
            callback: 存储回调函数
        """
        self.storage_callback = callback
        logger.info("Storage callback updated")

    def set_fallback_callback(self, callback: Callable[[], Awaitable[Any]]) -> None:
        """
        设置降级回调函数

        Args:
            callback: 降级回调函数
        """
        self.fallback_callback = callback
        logger.info("Fallback callback updated")


# 全局双通道服务实例
_global_dual_channel_service: Optional[DualChannelService] = None


def get_dual_channel_service(
    rate_limiter: Optional[RateLimiter] = None,
    storage_callback: Optional[Callable] = None,
    fallback_callback: Optional[Callable[[], Awaitable[Any]]] = None,
) -> DualChannelService:
    """
    获取全局双通道服务实例

    Args:
        rate_limiter: 限流器实例
        storage_callback: 存储回调函数
        fallback_callback: 降级回调函数

    Returns:
        双通道服务实例
    """
    global _global_dual_channel_service
    if _global_dual_channel_service is None:
        _global_dual_channel_service = DualChannelService(
            rate_limiter=rate_limiter,
            storage_callback=storage_callback,
            fallback_callback=fallback_callback,
        )
        logger.info("Created global dual channel service")
    return _global_dual_channel_service
