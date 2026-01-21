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

    async def request_execution(
        self,
        model_id: str,
        task_id: str,
        user_id: str,
        model_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        请求执行任务

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
            }
        """
        async with self._lock:
            redis_client = redis_manager.get_client()

            max_concurrency = model_config.get("max_concurrency", 40)
            task_concurrency = model_config.get("task_concurrency", 2)
            batch_concurrency = model_config.get("batch_concurrency", 1)

            # 检查模型当前活跃任务数
            active_tasks_key = MODEL_ACTIVE_TASKS_KEY.format(model_id=model_id)
            active_count = await redis_client.hlen(active_tasks_key)

            # 计算可同时运行的任务数
            max_running_tasks = max_concurrency // task_concurrency

            # 检查批量任务并发限制
            user_batch_key = USER_ACTIVE_BATCH_TASKS_KEY.format(user_id=user_id)
            user_batch_count = await redis_client.llen(user_batch_key)

            if user_batch_count >= batch_concurrency:
                # 用户批量任务数已达上限，任务需要等待
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

            if active_count >= max_running_tasks:
                # 模型并发数已达上限，任务需要等待
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

            # 可以执行，标记为活跃任务
            await redis_client.hset(active_tasks_key, task_id, user_id)

            return {
                "can_execute": True,
                "queue_position": 0,
                "waiting_count": 0,
                "reason": None,
            }

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

    async def wait_for_execution(
        self,
        model_id: str,
        task_id: str,
        user_id: str,
        model_config: Dict[str, Any],
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """
        等待任务可以执行（使用轮询机制）

        定期检查并发槽位是否可用，简单可靠。

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
        check_interval = 2.0  # 每 2 秒检查一次

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

                # 不能执行，记录日志并等待后重试
                logger.debug(
                    f"任务 {task_id} 等待执行: 原因={result['reason']}, "
                    f"队列位置={result['queue_position']}, "
                    f"等待数={result['waiting_count']}, "
                    f"已等待={elapsed:.1f}秒"
                )

                # 等待一段时间后重新检查
                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            # 任务被取消，从队列中移除
            waiting_queue_key = MODEL_WAITING_QUEUE_KEY.format(model_id=model_id)
            await self._remove_from_queue(waiting_queue_key, task_id, redis_client)
            raise

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
        通知等待中的任务（使用轮询机制时此方法为空操作）

        由于现在使用轮询机制，等待任务会自动检测槽位释放，
        不需要主动通知。保留此方法以保持接口兼容性。

        Args:
            model_id: 模型 ID
            redis_client: Redis 客户端
        """
        # 使用轮询机制，无需主动通知
        pass

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
