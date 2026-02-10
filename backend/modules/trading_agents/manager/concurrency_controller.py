"""
并发控制器

基于模型配置实现智能并发控制：
- 模型最大并发数限制
- 单任务并发数限制
- 批量任务并发数限制
- 任务排队机制（FIFO）
- Redis Pub/Sub 事件驱动的自动唤醒
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque

from core.db.redis import redis_manager

logger = logging.getLogger(__name__)

# Redis Key 常量
MODEL_ACTIVE_TASKS_KEY = "concurrency:model:{model_id}:active"  # Hash: {task_id: user_id}
MODEL_WAITING_QUEUE_KEY = "concurrency:model:{model_id}:waiting"  # List: JSON
USER_ACTIVE_BATCH_TASKS_KEY = "concurrency:user:{user_id}:batch_active"  # List: [batch_id]
MODEL_WAKEUP_CHANNEL = "concurrency:wakeup:{model_id}"  # Pub/Sub 唤醒通道


class ConcurrencyController:
    """
    并发控制器

    管理模型级别的并发控制和任务排队。
    使用 Redis Pub/Sub 实现事件驱动的槽位释放通知。
    """

    def __init__(self):
        """初始化并发控制器"""
        self._lock = asyncio.Lock()
        # Pub/Sub 订阅器缓存: {model_id: pubsub}
        self._pubsub_cache: Dict[str, Any] = {}
        # 事件缓存: {model_id: asyncio.Event}
        self._event_cache: Dict[str, asyncio.Event] = {}

    async def cleanup_on_startup(self) -> None:
        """
        启动时清理并发控制状态

        清除所有 Redis 并发控制相关的 Key，防止服务重启后残留状态导致死锁。
        """
        try:
            redis_client = redis_manager.get_client()
            
            # 1. 清理模型活跃任务
            active_keys = await redis_client.keys("concurrency:model:*:active")
            if active_keys:
                await redis_client.delete(*active_keys)
                logger.info(f"[并发控制] 已清理 {len(active_keys)} 个模型活跃任务 Key")

            # 2. 清理等待队列
            waiting_keys = await redis_client.keys("concurrency:model:*:waiting")
            if waiting_keys:
                await redis_client.delete(*waiting_keys)
                logger.info(f"[并发控制] 已清理 {len(waiting_keys)} 个等待队列 Key")

            # 3. 清理用户批量任务
            batch_keys = await redis_client.keys("concurrency:user:*:batch_active")
            if batch_keys:
                await redis_client.delete(*batch_keys)
                logger.info(f"[并发控制] 已清理 {len(batch_keys)} 个用户批量任务 Key")

            logger.info("[并发控制] 启动清理完成")
        except Exception as e:
            logger.error(f"[并发控制] 启动清理失败: {e}")

    # Lua 脚本：原子性检查和获取槽位
    _ACQUIRE_SLOT_LUA = """
    local active_tasks_key = KEYS[1]
    local task_id = ARGV[1]
    local user_id = ARGV[2]
    local max_running_tasks = tonumber(ARGV[3])

    -- 获取当前活跃任务数
    local active_count = redis.call('HLEN', active_tasks_key)

    -- 检查是否超过限制
    if active_count >= max_running_tasks then
        return {0, active_count}  -- 槽位已满
    end

    -- 获取槽位
    redis.call('HSET', active_tasks_key, task_id, user_id)
    return {1, active_count + 1}  -- 成功获取
    """

    async def request_execution(
        self,
        model_id: str,
        task_id: str,
        user_id: str,
        model_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        请求执行任务（使用 Lua 脚本确保原子性）

        支持三级并发控制：
        1. 每用户模型槽位上限（user_max_concurrent）：防止单用户垄断
        2. 每用户批量任务数（batch_concurrency）：限制批量任务并行数
        3. 全局模型槽位（max_running_tasks）：系统整体限制

        Args:
            model_id: 模型 ID
            task_id: 任务 ID
            user_id: 用户 ID
            model_config: 模型配置

        Returns:
            {
                "can_execute": bool,  # 是否可以立即执行
                "queue_position": int,  # 在队列中的位置（0 表示可以执行）
                "waiting_count": int,  # 总等待任务数
                "reason": str,  # 不能执行的原因（可为 None）
            }
        """
        redis_client = redis_manager.get_client()

        max_concurrency = model_config.get("max_concurrency", 40)
        task_concurrency = model_config.get("task_concurrency", 2)
        batch_concurrency = model_config.get("batch_concurrency", 1)
        # 每用户模型槽位上限，防止单用户垄断并发资源
        user_max_concurrent = model_config.get("user_max_concurrent", 10)

        # 计算可同时运行的任务数
        max_running_tasks = max_concurrency // task_concurrency

        # ============================================================
        # 检查 1：每用户模型槽位上限（最高优先级，最先检查）
        # ============================================================
        user_slot_count = await self._get_user_active_slot_count(
            redis_client, model_id, user_id
        )

        if user_slot_count >= user_max_concurrent:
            # 用户槽位已达上限，加入队列等待
            async with self._lock:
                queue_position = await self._enqueue_task(
                    model_id, task_id, user_id, redis_client
                )

            waiting_count = await redis_client.llen(
                MODEL_WAITING_QUEUE_KEY.format(model_id=model_id)
            )

            logger.debug(
                f"用户 {user_id} 在模型 {model_id} 的槽位已达上限: "
                f"已用={user_slot_count}, 上限={user_max_concurrent}"
            )

            return {
                "can_execute": False,
                "queue_position": queue_position,
                "waiting_count": waiting_count,
                "reason": "user_quota_exceeded",
            }

        # ============================================================
        # 检查 2：每用户批量任务数限制
        # ============================================================
        user_batch_key = USER_ACTIVE_BATCH_TASKS_KEY.format(user_id=user_id)
        user_batch_count = await redis_client.llen(user_batch_key)

        if user_batch_count >= batch_concurrency:
            # 用户批量任务数已达上限，任务需要等待
            async with self._lock:
                queue_position = await self._enqueue_task(
                    model_id, task_id, user_id, redis_client
                )

            waiting_count = await redis_client.llen(
                MODEL_WAITING_QUEUE_KEY.format(model_id=model_id)
            )

            return {
                "can_execute": False,
                "queue_position": queue_position,
                "waiting_count": waiting_count,
                "reason": "user_batch_limit",
            }

        # ============================================================
        # 检查 3：全局模型槽位限制（Lua 脚本确保原子性）
        # ============================================================
        active_tasks_key = MODEL_ACTIVE_TASKS_KEY.format(model_id=model_id)

        try:
            result = await redis_client.eval(
                self._ACQUIRE_SLOT_LUA,
                1,  # 1个 key
                active_tasks_key,
                task_id,
                user_id,
                max_running_tasks
            )

            if result[0] == 1:
                # 成功获取槽位
                return {
                    "can_execute": True,
                    "queue_position": 0,
                    "waiting_count": 0,
                    "reason": None,
                }
            else:
                # 槽位已满，加入队列
                async with self._lock:
                    queue_position = await self._enqueue_task(
                        model_id, task_id, user_id, redis_client
                    )

                waiting_count = await redis_client.llen(
                    MODEL_WAITING_QUEUE_KEY.format(model_id=model_id)
                )

                return {
                    "can_execute": False,
                    "queue_position": queue_position,
                    "waiting_count": waiting_count,
                    "reason": "model_concurrency_limit",
                }

        except Exception as e:
            logger.error(f"请求执行时发生错误: model={model_id}, task={task_id}, error={e}")
            raise

    async def _get_user_active_slot_count(
        self,
        redis_client: Any,
        model_id: str,
        user_id: str,
    ) -> int:
        """
        统计用户在指定模型上已占用的活跃槽位数

        用于每用户并发限制检查。遍历 active_tasks Hash，统计 value 等于 user_id 的条目数。

        Args:
            redis_client: Redis 客户端
            model_id: 模型 ID
            user_id: 用户 ID

        Returns:
            该用户已占用的槽位数
        """
        active_tasks_key = MODEL_ACTIVE_TASKS_KEY.format(model_id=model_id)

        try:
            # 使用 HSCAN 遍历 Hash，统计匹配用户 ID 的条目
            # 更高效的方式是维护一个单独的计数器，但先使用 HSCAN 方案
            all_entries = await redis_client.hgetall(active_tasks_key)

            if not all_entries:
                return 0

            # 统计 value 等于 user_id 的条目数
            count = 0
            for _, entry_user_id in all_entries.items():
                if entry_user_id == user_id:
                    count += 1

            return count

        except Exception as e:
            logger.warning(
                f"统计用户槽位数失败: model={model_id}, user={user_id}, error={e}"
            )
            # 出错时返回 0，允许任务继续，避免阻塞
            return 0

    async def release_execution(
        self,
        model_id: str,
        task_id: str,
        user_id: str,
        batch_id: Optional[str] = None,
    ):
        """
        释放任务执行资源

        使用 Redis Pub/Sub 通知等待中的任务。

        Args:
            model_id: 模型 ID
            task_id: 任务 ID
            user_id: 用户 ID
            batch_id: 批量任务 ID（可选）
        """
        async with self._lock:
            redis_client = redis_manager.get_client()

            # 从活跃任务中移除
            active_tasks_key = MODEL_ACTIVE_TASKS_KEY.format(model_id=model_id)
            await redis_client.hdel(active_tasks_key, task_id)

            # 如果是批量任务，从用户批量任务列表中移除
            if batch_id:
                user_batch_key = USER_ACTIVE_BATCH_TASKS_KEY.format(user_id=user_id)
                await redis_client.lrem(user_batch_key, 1, batch_id)

            # 使用 Pub/Sub 通知等待任务（事件驱动）
            await self._notify_waiting_tasks(model_id, redis_client)

    async def get_queue_position(
        self,
        model_id: str,
        task_id: str,
    ) -> Dict[str, int]:
        """
        获取任务在队列中的位置

        Args:
            model_id: 模型 ID
            task_id: 任务 ID

        Returns:
            {
                "position": int,  # 队列位置（0 表示可以执行，>0 表示前面有任务）
                "waiting_count": int,  # 总等待任务数
            }
        """
        redis_client = redis_manager.get_client()

        waiting_queue_key = MODEL_WAITING_QUEUE_KEY.format(model_id=model_id)
        waiting_queue = await redis_client.lrange(waiting_queue_key, 0, -1)

        for i, task_json in enumerate(waiting_queue):
            task_data = json.loads(task_json)
            if task_data.get("task_id") == task_id:
                return {
                    "position": i + 1,  # 从 1 开始计数
                    "waiting_count": len(waiting_queue),
                }

        # 不在队列中，说明可以执行
        return {
            "position": 0,
            "waiting_count": len(waiting_queue),
        }

    async def _enqueue_task(
        self,
        model_id: str,
        task_id: str,
        user_id: str,
        redis_client: Any,
    ) -> int:
        """
        将任务加入等待队列

        Returns:
            队列位置（从 1 开始）
        """
        waiting_queue_key = MODEL_WAITING_QUEUE_KEY.format(model_id=model_id)

        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "enqueued_at": datetime.utcnow().isoformat(),
        }

        await redis_client.rpush(waiting_queue_key, json.dumps(task_data))

        # 返回队列位置
        queue_length = await redis_client.llen(waiting_queue_key)
        return queue_length

    async def register_batch_task(
        self,
        user_id: str,
        batch_id: str,
    ) -> None:
        """
        登记批量任务占用槽位（用于每用户批量并发限制）

        在任务成功获取执行权后调用，向 USER_ACTIVE_BATCH_TASKS_KEY 中追加 batch_id，
        以便 release_execution 时能够正确移除，维持计数器一致。

        Args:
            user_id: 用户 ID
            batch_id: 批量任务 ID（单任务不会调用此方法）
        """
        if not batch_id:
            return

        redis_client = redis_manager.get_client()
        user_batch_key = USER_ACTIVE_BATCH_TASKS_KEY.format(user_id=user_id)

        try:
            await redis_client.rpush(user_batch_key, batch_id)
            logger.debug(
                f"[并发控制] 登记批量任务占用: user={user_id}, batch={batch_id}"
            )
        except Exception as e:
            logger.warning(
                f"[并发控制] 登记批量任务占用失败: user={user_id}, batch={batch_id}, error={e}"
            )

    async def wait_for_execution(
        self,
        model_id: str,
        task_id: str,
        user_id: str,
        model_config: Dict[str, Any],
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """
        等待任务可以执行（使用 Redis Pub/Sub 事件驱动 + 兜底轮询）

        实现逻辑：
        1. 首先尝试请求执行
        2. 如果不能执行，订阅对应模型的唤醒通道
        3. 使用 asyncio.wait_for 等待消息或超时
        4. 收到消息或超时时重新检查槽位
        5. 兜底：即使没有收到 Pub/Sub 消息，也会定期重新检查

        Args:
            model_id: 模型 ID
            task_id: 任务 ID
            user_id: 用户 ID
            model_config: 模型配置
            timeout: 超时时间（秒），默认 5 分钟

        Returns:
            {
                "success": bool,  # 是否成功获取执行权限
                "reason": str,    # 失败原因（如果超时）
            }

        Raises:
            asyncio.TimeoutError: 等待超时时抛出
        """
        start_time = datetime.utcnow()
        redis_client = redis_manager.get_client()
        pubsub = None

        try:
            while True:
                # 检查是否超时
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout:
                    raise asyncio.TimeoutError(
                        f"任务 {task_id} 等待执行超时（{timeout}秒），"
                        f"模型 {model_id} 的并发槽位一直不可用"
                    )

                # 尝试请求执行
                result = await self.request_execution(
                    model_id=model_id,
                    task_id=task_id,
                    user_id=user_id,
                    model_config=model_config,
                )

                if result["can_execute"]:
                    logger.info(
                        f"任务 {task_id} 获取到执行权限，等待时间: {elapsed:.2f}秒"
                    )
                    return {"success": True, "reason": None}

                # 不能执行，记录日志
                logger.debug(
                    f"任务 {task_id} 等待执行: 原因={result['reason']}, "
                    f"队列位置={result['queue_position']}, "
                    f"等待数={result['waiting_count']}, "
                    f"已等待={elapsed:.1f}秒"
                )

                # ========================================================
                # 事件驱动等待：订阅唤醒通道
                # ========================================================
                if pubsub is None:
                    channel = MODEL_WAKEUP_CHANNEL.format(model_id=model_id)
                    pubsub = redis_client.pubsub()
                    await pubsub.subscribe(channel)
                    logger.debug(f"已订阅唤醒通道: channel={channel}")

                # 计算剩余超时时间
                remaining_timeout = min(timeout - elapsed, 5.0)  # 最多等 5 秒

                try:
                    # 等待唤醒消息或超时
                    message = await asyncio.wait_for(
                        pubsub.get_message(timeout=remaining_timeout),
                        timeout=remaining_timeout
                    )

                    if message and message.get("type") == "message":
                        # 收到唤醒消息，重新检查槽位
                        logger.debug(
                            f"任务 {task_id} 收到唤醒消息，重新检查槽位"
                        )
                        continue

                except asyncio.TimeoutError:
                    # 超时，重新检查槽位（兜底机制）
                    pass
                except Exception as e:
                    logger.warning(
                        f"等待唤醒消息时出错: task={task_id}, error={e}"
                    )
                    # 出错时继续循环重试

        except asyncio.CancelledError:
            # 任务被取消，从队列中移除
            waiting_queue_key = MODEL_WAITING_QUEUE_KEY.format(model_id=model_id)
            await self._remove_from_queue(waiting_queue_key, task_id, redis_client)
            raise
        finally:
            # 清理 Pub/Sub 连接
            if pubsub:
                try:
                    channel = MODEL_WAKEUP_CHANNEL.format(model_id=model_id)
                    await pubsub.unsubscribe(channel)
                    await pubsub.close()
                    logger.debug(f"已关闭 Pub/Sub 连接: task={task_id}")
                except Exception as e:
                    logger.warning(f"关闭 Pub/Sub 连接失败: task={task_id}, error={e}")

    async def _listen_for_wakeup(
        self,
        model_id: str,
        pubsub: Any,
        event: asyncio.Event,
    ) -> None:
        """
        监听唤醒消息

        使用轮询方式（get_message）替代 async for listen()，
        避免 redis-py 在某些环境下的事件循环问题。

        Args:
            model_id: 模型 ID
            pubsub: Redis Pub/Sub 订阅器
            event: asyncio 事件对象
        """
        try:
            while True:
                try:
                    # 使用 get_message 替代 listen()，避免异步迭代器问题
                    message = await pubsub.get_message(timeout=None)
                    if message and message.get("type") == "message":
                        # 收到唤醒消息，设置事件
                        event.set()
                        logger.debug(f"收到唤醒信号: model_id={model_id}")
                except asyncio.CancelledError:
                    # 任务被取消，正常退出
                    logger.debug(f"监听任务被取消: model_id={model_id}")
                    break
                except Exception as e:
                    # 捕获单个消息处理的异常，继续监听
                    logger.warning(f"处理 Pub/Sub 消息时发生异常: model_id={model_id}, error={e}")
                    # 短暂休眠后继续
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            # 任务被取消，正常退出
            logger.debug(f"监听任务被取消: model_id={model_id}")
            pass
        except Exception as e:
            # 捕获所有异常，防止任务崩溃
            logger.error(f"监听唤醒消息时发生异常: model_id={model_id}, error={e}", exc_info=True)

    async def _notify_waiting_tasks(
        self,
        model_id: str,
        redis_client: Any,
    ) -> None:
        """
        通知等待中的任务（使用 Redis Pub/Sub）

        当槽位释放时，向对应模型的唤醒通道发布消息，
        唤醒正在等待该模型槽位的任务。

        Args:
            model_id: 模型 ID
            redis_client: Redis 客户端
        """
        try:
            channel = MODEL_WAKEUP_CHANNEL.format(model_id=model_id)
            await redis_client.publish(channel, "wakeup")
            logger.debug(f"已发布唤醒消息: channel={channel}")
        except Exception as e:
            logger.warning(f"发布唤醒消息失败: model={model_id}, error={e}")
            # 发布失败不影响主流程，轮询机制会作为兜底

    async def _remove_from_queue(
        self,
        queue_key: str,
        task_id: str,
        redis_client: Any,
    ) -> bool:
        """
        从队列中移除任务

        Args:
            queue_key: 队列键
            task_id: 任务 ID
            redis_client: Redis 客户端

        Returns:
            是否成功移除
        """
        # 获取队列中所有任务
        queue = await redis_client.lrange(queue_key, 0, -1)

        # 找到并移除目标任务
        for task_json in queue:
            task_data = json.loads(task_json)
            if task_data.get("task_id") == task_id:
                await redis_client.lrem(queue_key, 1, task_json)
                logger.info(f"从队列中移除任务: task_id={task_id}")
                return True

        return False

    async def close(self):
        """关闭所有 Pub/Sub 连接"""
        for model_id, pubsub in self._pubsub_cache.items():
            try:
                await pubsub.close()
                logger.debug(f"关闭 Pub/Sub 订阅: model_id={model_id}")
            except Exception as e:
                logger.warning(f"关闭 Pub/Sub 订阅失败: model_id={model_id}, error={e}")

        self._pubsub_cache.clear()
        self._event_cache.clear()


# =============================================================================
# 全局并发控制器实例
# =============================================================================

_concurrency_controller: Optional[ConcurrencyController] = None


def get_concurrency_controller() -> ConcurrencyController:
    """获取全局并发控制器实例"""
    global _concurrency_controller
    if _concurrency_controller is None:
        _concurrency_controller = ConcurrencyController()
    return _concurrency_controller
