"""
并发控制器（公共模型资源池）

实现基于 Redis 的分布式并发控制，支持：
- 槽位管理（总并发上限、每用户限制）
- FIFO 队列排队
- TTL 自动过期锁（防止死锁）
- Watchdog 自动续期机制
- Force Release 机制（管理员可手动解锁）
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from core.db.redis import redis_manager
from modules.trading_agents.exceptions import ConcurrencyLimitException, ModelQuotaExhaustedError

logger = logging.getLogger(__name__)


# =============================================================================
# 配置常量
# =============================================================================

# 默认配置
DEFAULT_LOCK_TTL = 300  # 锁默认过期时间（秒）5 分钟
DEFAULT_WATCHDOG_INTERVAL = 60  # 看门狗续期间隔（秒）1 分钟
DEFAULT_MAX_QUEUE_SIZE = 100  # 最大队列长度


@dataclass
class QuotaInfo:
    """配额信息"""
    model_id: str
    max_slots: int              # 总槽位数
    occupied_slots: int         # 已占用槽位数
    available_slots: int        # 可用槽位数
    queue_length: int           # 队列长度
    user_occupied: int          # 当前用户已占用槽位数
    user_position: Optional[int]  # 当前用户在队列中的位置


@dataclass
class LockInfo:
    """锁信息"""
    user_id: str
    model_id: str
    acquired_at: float = field(default_factory=time.time)
    last_renewed: float = field(default_factory=time.time)
    watchdog_task: Optional[asyncio.Task] = None


# =============================================================================
# 并发控制器
# =============================================================================

class ConcurrencyManager:
    """
    并发控制器

    管理公共模型的并发访问，使用 Redis 实现分布式锁和队列。
    """

    def __init__(
        self,
        redis_client=None,
        default_lock_ttl: int = DEFAULT_LOCK_TTL,
        watchdog_interval: int = DEFAULT_WATCHDOG_INTERVAL,
    ):
        """
        初始化并发控制器

        Args:
            redis_client: Redis 客户端（可选，默认使用全局实例）
            default_lock_ttl: 默认锁过期时间（秒）
            watchdog_interval: 看门狗续期间隔（秒）
        """
        self._redis = redis_client
        self._default_lock_ttl = default_lock_ttl
        self._watchdog_interval = watchdog_interval

        # 追踪活动锁（用于看门狗续期）
        self._active_locks: Dict[str, LockInfo] = {}

    def _get_redis(self):
        """获取 Redis 客户端"""
        if self._redis is None:
            return redis_manager.get_client()
        return self._redis

    # ========================================================================
    # 公共模型配额管理
    # ========================================================================

    async def get_quota_info(
        self,
        model_id: str,
        user_id: str,
        max_slots: int
    ) -> QuotaInfo:
        """
        获取配额信息

        Args:
            model_id: 模型 ID
            user_id: 用户 ID
            max_slots: 总槽位数

        Returns:
            配额信息
        """
        redis = self._get_redis()

        # 获取已占用槽位数
        occupied_key = f"model:{model_id}:occupied"
        occupied = await redis.get(occupied_key)
        occupied_slots = int(occupied) if occupied else 0

        # 获取队列长度
        queue_key = f"model:{model_id}:queue"
        queue_length = await redis.llen(queue_key)

        # 获取用户已占用槽位数
        user_key = f"model:{model_id}:user:{user_id}"
        user_occupied = await redis.exists(user_key)

        # 获取用户在队列中的位置
        user_position = await self._get_queue_position(model_id, user_id)

        return QuotaInfo(
            model_id=model_id,
            max_slots=max_slots,
            occupied_slots=occupied_slots,
            available_slots=max_slots - occupied_slots,
            queue_length=queue_length,
            user_occupied=user_occupied,
            user_position=user_position,
        )

    async def acquire_public_quota(
        self,
        model_id: str,
        user_id: str,
        max_slots: int,
        timeout: Optional[float] = None
    ) -> bool:
        """
        获取公共模型配额

        Args:
            model_id: 模型 ID
            user_id: 用户 ID
            max_slots: 总槽位数
            timeout: 等待超时时间（秒），None 表示不等待

        Returns:
            是否成功获取配额

        Raises:
            ModelQuotaExhaustedError: 配额已满且不等待时
        """
        redis = self._get_redis()

        # 检查用户是否已占用槽位
        if await self._has_user_slot(model_id, user_id):
            logger.info(f"用户已有槽位: model={model_id}, user={user_id}")
            return True

        # 尝试获取槽位
        occupied_key = f"model:{model_id}:occupied"
        user_key = f"model:{model_id}:user:{user_id}"

        # 使用 Redis 事务
        async with redis.pipeline(transaction=True) as pipe:
            while True:
                try:
                    # 监视 occupied_key
                    await pipe.watch(occupied_key)

                    # 获取当前占用数
                    occupied = await pipe.get(occupied_key)
                    current = int(occupied) if occupied else 0

                    if current >= max_slots:
                        # 槽位已满
                        if timeout is not None and timeout > 0:
                            # 加入队列
                            await pipe.unwatch()
                            return await self._wait_in_queue(model_id, user_id, timeout)
                        else:
                            await pipe.unwatch()
                            raise ModelQuotaExhaustedError(
                                model_id=model_id,
                                queue_position=await self._get_queue_position(model_id, user_id)
                            )

                    # 槽位可用，尝试获取
                    pipe.multi()
                    await pipe.incr(occupied_key)
                    await pipe.setex(user_key, self._default_lock_ttl, "1")
                    results = await pipe.execute()

                    if results is not None:
                        # 成功获取槽位
                        logger.info(f"获取公共模型配额成功: model={model_id}, user={user_id}")
                        # 启动看门狗，自动续期锁
                        await self.start_watchdog(model_id, user_id)
                        return True
                    else:
                        # CAS 失败，重试
                        continue

                except Exception as e:
                    logger.error(f"获取配额失败: {e}")
                    raise

    async def release_public_quota(
        self,
        model_id: str,
        user_id: str
    ) -> None:
        """
        释放公共模型配额

        Args:
            model_id: 模型 ID
            user_id: 用户 ID
        """
        redis = self._get_redis()

        occupied_key = f"model:{model_id}:occupied"
        user_key = f"model:{model_id}:user:{user_id}"
        queue_key = f"model:{model_id}:queue"

        # 停止看门狗
        lock_key = f"{model_id}:{user_id}"
        if lock_key in self._active_locks:
            lock_info = self._active_locks[lock_key]
            if lock_info.watchdog_task:
                lock_info.watchdog_task.cancel()
            del self._active_locks[lock_key]

        # 使用 Redis 事务
        async with redis.pipeline(transaction=True) as pipe:
            while True:
                try:
                    await pipe.watch(user_key)

                    # 检查用户槽位是否存在
                    if not await pipe.exists(user_key):
                        await pipe.unwatch()
                        return

                    # 释放槽位
                    pipe.multi()
                    await pipe.delete(user_key)
                    await pipe.decr(occupied_key)
                    results = await pipe.execute()

                    if results is not None:
                        break

                except Exception:
                    continue

        # 唤醒队列中的下一个任务（使用RPOP保持FIFO顺序）
        # 注意：在_wait_in_queue中，我们使用BLPOP获取队列头部元素
        # 所以这里不需要手动唤醒，队列会自动按FIFO顺序处理
        # 但为了向后兼容，保留唤醒逻辑，但改为更安全的方式
        queue_length = await redis.llen(queue_key)
        if queue_length > 0:
            logger.info(f"队列中还有 {queue_length} 个用户在等待: model={model_id}")

        logger.info(f"释放公共模型配额: model={model_id}, user={user_id}")

    # ========================================================================
    # 队列管理
    # ========================================================================

    async def _wait_in_queue(
        self,
        model_id: str,
        user_id: str,
        timeout: float
    ) -> bool:
        """
        在队列中等待（使用BLPOP阻塞获取，避免轮询）

        Args:
            model_id: 模型 ID
            user_id: 用户 ID
            timeout: 等待超时时间（秒）

        Returns:
            是否成功获取配额
        """
        redis = self._get_redis()

        queue_key = f"model:{model_id}:queue"
        user_key = f"model:{model_id}:user:{user_id}"

        # 加入队列（FIFO：先到先服务）
        await redis.rpush(queue_key, user_id)
        logger.info(f"加入排队队列: model={model_id}, user={user_id}")

        try:
            # 使用BLPOP阻塞等待，避免轮询（更高效的FIFO实现）
            # BLPOP会按队列顺序返回元素，确保公平性
            result = await redis.blpop(queue_key, timeout=timeout)

            if result is None:
                # 超时
                raise ModelQuotaExhaustedError(
                    model_id=model_id,
                    queue_position=await self._get_queue_position(model_id, user_id)
                )

            # 检查返回的用户ID是否匹配
            popped_user = result[1].decode() if isinstance(result[1], bytes) else result[1]
            if popped_user != user_id:
                # 不应该发生，因为BLPOP是顺序的
                logger.error(f"队列顺序错误: expected={user_id}, got={popped_user}")
                # 重新加入队列
                await redis.rpush(queue_key, user_id)
                return False

            # 成功获取槽位
            logger.info(f"排队成功获取槽位: model={model_id}, user={user_id}")

            # 设置用户槽位
            occupied_key = f"model:{model_id}:occupied"
            await redis.setex(user_key, self._default_lock_ttl, "1")
            await redis.incr(occupied_key)

            return True

        except asyncio.CancelledError:
            # 被取消，从队列中移除
            await redis.lrem(queue_key, 0, user_id)
            raise
        except Exception as e:
            # 其他错误，清理队列
            await redis.lrem(queue_key, 0, user_id)
            logger.error(f"队列等待失败: {e}")
            raise

    async def _get_queue_position(
        self,
        model_id: str,
        user_id: str
    ) -> Optional[int]:
        """
        获取用户在队列中的位置

        Args:
            model_id: 模型 ID
            user_id: 用户 ID

        Returns:
            队列位置（从1开始），不在队列中返回 None
        """
        redis = self._get_redis()
        queue_key = f"model:{model_id}:queue"

        queue = await redis.lrange(queue_key, 0, -1)
        user_id_bytes = user_id.encode() if isinstance(user_id, str) else user_id

        try:
            return queue.index(user_id_bytes) + 1
        except ValueError:
            return None

    # ========================================================================
    # 辅助方法
    # ========================================================================

    async def _has_user_slot(self, model_id: str, user_id: str) -> bool:
        """检查用户是否已占用槽位"""
        redis = self._get_redis()
        user_key = f"model:{model_id}:user:{user_id}"
        return await redis.exists(user_key) > 0

    # ========================================================================
    # 看门狗机制
    # ========================================================================

    async def start_watchdog(
        self,
        model_id: str,
        user_id: str
    ) -> None:
        """
        启动看门狗，自动续期锁

        Args:
            model_id: 模型 ID
            user_id: 用户 ID
        """
        lock_key = f"{model_id}:{user_id}"

        if lock_key in self._active_locks:
            # 看门狗已在运行
            return

        lock_info = LockInfo(user_id=user_id, model_id=model_id)
        self._active_locks[lock_key] = lock_info

        # 创建看门狗任务
        lock_info.watchdog_task = asyncio.create_task(
            self._watchdog_loop(model_id, user_id)
        )

        logger.info(f"启动看门狗: model={model_id}, user={user_id}")

    async def _watchdog_loop(self, model_id: str, user_id: str) -> None:
        """
        看门狗续期循环（增强版）
        
        增加健康检查：
        1. 检查Redis中槽位是否存在
        2. 检查任务是否仍在运行（通过任务管理器）
        3. 检查续期是否过于频繁（防止Redis异常）
        """
        redis = self._get_redis()
        user_key = f"model:{model_id}:user:{user_id}"
        lock_key = f"{model_id}:{user_id}"
        
        # 最大续期间隔（防止过于频繁）
        min_renew_interval = self._watchdog_interval * 0.5
        
        while True:
            try:
                await asyncio.sleep(self._watchdog_interval)
                
                # 检查锁信息是否存在
                if lock_key not in self._active_locks:
                    logger.warning(f"锁信息丢失，停止看门狗: model={model_id}, user={user_id}")
                    break
                
                lock_info = self._active_locks[lock_key]
                
                # 检查是否过于频繁（防止Redis异常导致快速循环）
                now = time.time()
                time_since_last_renew = now - lock_info.last_renewed
                if time_since_last_renew < min_renew_interval:
                    logger.warning(f"续期过于频繁({time_since_last_renew:.2f}s)，可能Redis异常: model={model_id}, user={user_id}")
                    # 即使检测到频繁续期，也应该正常续期，避免锁过期
                    # 只记录警告日志，不跳过续期

                # 检查Redis中槽位是否存在
                exists = await redis.exists(user_key)
                if not exists:
                    logger.info(f"槽位已释放，停止看门狗: model={model_id}, user={user_id}")
                    break
                
                # 检查任务是否仍在运行（通过检查任务状态）
                if not await self._is_task_running(model_id, user_id):
                    logger.info(f"任务已停止，释放槽位并停止看门狗: model={model_id}, user={user_id}")
                    await self.release_public_quota(model_id, user_id)
                    break

                # 续期锁
                await redis.expire(user_key, self._default_lock_ttl)
                lock_info.last_renewed = now
                logger.debug(f"看门狗续期: model={model_id}, user={user_id}")

            except asyncio.CancelledError:
                logger.info(f"看门狗被取消: model={model_id}, user={user_id}")
                break
            except Exception as e:
                logger.error(f"看门狗续期失败: {e}")
                break
    
    async def _is_task_running(self, model_id: str, user_id: str) -> bool:
        """
        检查任务是否仍在运行
        
        Args:
            model_id: 模型 ID
            user_id: 用户 ID
            
        Returns:
            任务是否正在运行
        """
        # 这里可以通过查询任务管理器或Redis中的任务状态来判断
        # 简化实现：检查Redis中是否有活跃的任务标记
        redis = self._get_redis()
        task_key = f"task:running:{user_id}:{model_id}"
        return await redis.exists(task_key) > 0

    # ========================================================================
    # 管理员功能
    # ========================================================================

    async def force_release(
        self,
        model_id: str,
        user_id: str,
        admin_user_id: str
    ) -> bool:
        """
        强制释放用户槽位（管理员功能）

        Args:
            model_id: 模型 ID
            user_id: 要释放的用户 ID
            admin_user_id: 管理员用户 ID

        Returns:
            是否成功释放
        """
        redis = self._get_redis()

        user_key = f"model:{model_id}:user:{user_id}"

        if not await redis.exists(user_key):
            return False

        # 停止看门狗
        lock_key = f"{model_id}:{user_id}"
        if lock_key in self._active_locks:
            lock_info = self._active_locks[lock_key]
            if lock_info.watchdog_task:
                lock_info.watchdog_task.cancel()
            del self._active_locks[lock_key]

        # 释放槽位
        occupied_key = f"model:{model_id}:occupied"
        await redis.delete(user_key)
        await redis.decr(occupied_key)

        logger.info(
            f"管理员强制释放槽位: model={model_id}, "
            f"user={user_id}, admin={admin_user_id}"
        )
        return True


# =============================================================================
# 全局并发控制器实例
# =============================================================================

concurrency_manager = ConcurrencyManager()


def get_concurrency_manager() -> ConcurrencyManager:
    """获取全局并发控制器实例"""
    return concurrency_manager
