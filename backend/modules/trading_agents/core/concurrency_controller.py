"""
并发控制器

基于模型配置实现智能并发控制：
- 模型最大并发数限制
- 单任务并发数限制
- 批量任务并发数限制
- 任务排队机制（FIFO）
"""
import asyncio
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


class ConcurrencyController:
    """
    并发控制器

    管理模型级别的并发控制和任务排队
    """

    def __init__(self):
        """初始化并发控制器"""
        self._lock = asyncio.Lock()

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
            # 理论最大同时运行任务数 = max_concurrency / task_concurrency
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

            # 尝试唤醒下一个等待任务
            await self._wake_next_task(model_id, redis_client)

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
            import json
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

        import json
        await redis_client.rpush(waiting_queue_key, json.dumps(task_data))

        # 返回队列位置
        queue_length = await redis_client.llen(waiting_queue_key)
        return queue_length

    async def _wake_next_task(
        self,
        model_id: str,
        redis_client: Any,
    ):
        """
        唤醒下一个等待任务

        通过设置一个标志，让任务管理器检查队列
        """
        waiting_queue_key = MODEL_WAITING_QUEUE_KEY.format(model_id=model_id)

        # 检查是否有等待任务
        queue_length = await redis_client.llen(waiting_queue_key)
        if queue_length > 0:
            # 标记有任务可以唤醒
            wakeup_key = f"concurrency:model:{model_id}:wakeup"
            await redis_client.set(wakeup_key, "1", ex=5)


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
