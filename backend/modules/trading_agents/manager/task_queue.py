"""
任务队列管理器

使用 Redis 实现任务队列调度，确保批量任务按 FIFO 顺序执行。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.db.redis import redis_manager

logger = logging.getLogger(__name__)


# Redis Key 常量
TASK_QUEUE_KEY = "queue:analysis_tasks"  # 任务队列（列表）
TASK_PRIORITY_QUEUE_KEY = "queue:analysis_tasks:priority"  # 优先级队列（有序集合）


class TaskQueueManager:
    """
    任务队列管理器

    使用 Redis 实现任务队列，支持：
    - FIFO 任务调度
    - 优先级任务
    - 任务状态追踪
    """

    def __init__(self) -> None:
        """初始化任务队列管理器"""
        self._processing = False
        self._worker_task: Optional[asyncio.Task[None]] = None

    async def enqueue_task(
        self,
        task_id: str,
        user_id: str,
        stock_code: str,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        将任务加入队列

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            stock_code: 股票代码
            priority: 优先级（越高越优先）
            metadata: 额外的元数据

        Returns:
            是否入队成功
        """
        try:
            redis_client = redis_manager.get_client()

            # 构建任务数据
            task_data = {
                "task_id": task_id,
                "user_id": user_id,
                "stock_code": stock_code,
                "priority": priority,
                "metadata": metadata or {},
                "enqueued_at": datetime.now(timezone.utc).isoformat(),
            }

            # 如果有优先级，使用优先级队列
            if priority > 0:
                # 使用有序集合，分数为优先级（负数表示越高越优先）
                await redis_client.zadd(  # type: ignore[misc]
                    TASK_PRIORITY_QUEUE_KEY, {json.dumps(task_data): -priority}
                )
                logger.info(f"任务加入优先级队列: task_id={task_id}, priority={priority}")
            else:
                # 普通队列
                await redis_client.rpush(TASK_QUEUE_KEY, json.dumps(task_data))  # type: ignore[misc]
                logger.info(f"任务加入队列: task_id={task_id}")

            return True

        except Exception as e:
            logger.error(f"任务入队失败: task_id={task_id}, error={e}")
            return False

    async def dequeue_task(self) -> Optional[Dict[str, Any]]:
        """
        从队列中取出一个任务

        优先从优先级队列取，如果没有则从普通队列取。

        Returns:
            任务数据或 None
        """
        try:
            redis_client = redis_manager.get_client()

            # 先检查优先级队列
            priority_task = await redis_client.zpopmax(TASK_PRIORITY_QUEUE_KEY)  # type: ignore[misc]
            if priority_task:
                task_json = priority_task[0]  # zpopmax 返回 [(member, score)]
                task_data: Dict[str, Any] = json.loads(task_json)
                logger.info(f"从优先级队列取出任务: task_id={task_data['task_id']}")
                return task_data

            # 再检查普通队列
            task_json = await redis_client.lpop(TASK_QUEUE_KEY)  # type: ignore[misc]
            if task_json:
                task_data2: Dict[str, Any] = json.loads(task_json)
                logger.info(f"从队列取出任务: task_id={task_data2['task_id']}")
                return task_data2

            return None

        except Exception as e:
            logger.error(f"任务出队失败: error={e}")
            return None

    async def get_queue_length(self) -> Dict[str, int]:
        """
        获取队列长度

        Returns:
            {"normal": 普通队列长度, "priority": 优先级队列长度}
        """
        try:
            redis_client = redis_manager.get_client()

            normal_length = await redis_client.llen(TASK_QUEUE_KEY)  # type: ignore[misc]
            priority_length = await redis_client.zcard(TASK_PRIORITY_QUEUE_KEY)  # type: ignore[misc]

            return {
                "normal": normal_length,
                "priority": priority_length,
                "total": normal_length + priority_length,
            }

        except Exception as e:
            logger.error(f"获取队列长度失败: error={e}")
            return {"normal": 0, "priority": 0, "total": 0}

    async def clear_queue(self) -> bool:
        """
        清空队列

        Returns:
            是否清空成功
        """
        try:
            redis_client = redis_manager.get_client()

            await redis_client.delete(TASK_QUEUE_KEY)
            await redis_client.delete(TASK_PRIORITY_QUEUE_KEY)

            logger.info("任务队列已清空")
            return True

        except Exception as e:
            logger.error(f"清空队列失败: error={e}")
            return False

    async def remove_task(self, task_id: str) -> bool:
        """
        从队列中移除指定任务

        Args:
            task_id: 任务 ID

        Returns:
            是否移除成功
        """
        try:
            redis_client = redis_manager.get_client()

            # 从普通队列移除
            normal_queue = await redis_client.lrange(TASK_QUEUE_KEY, 0, -1)  # type: ignore[misc]
            for task_json in normal_queue:
                task_data = json.loads(task_json)
                if task_data.get("task_id") == task_id:
                    await redis_client.lrem(TASK_QUEUE_KEY, 1, task_json)  # type: ignore[misc]
                    logger.info(f"从普通队列移除任务: task_id={task_id}")
                    return True

            # 从优先级队列移除
            priority_queue = await redis_client.zrange(TASK_PRIORITY_QUEUE_KEY, 0, -1)  # type: ignore[misc]
            for task_json in priority_queue:
                task_data = json.loads(task_json)
                if task_data.get("task_id") == task_id:
                    await redis_client.zrem(TASK_PRIORITY_QUEUE_KEY, task_json)
                    logger.info(f"从优先级队列移除任务: task_id={task_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"移除任务失败: task_id={task_id}, error={e}")
            return False

    async def start_worker(self, handler: Any) -> None:
        """
        启动队列工作线程

        Args:
            handler: 任务处理函数，接收 task_data 参数
        """
        if self._processing:
            logger.warning("队列工作线程已在运行")
            return

        self._processing = True
        self._worker_task = asyncio.create_task(self._worker_loop(handler))
        logger.info("任务队列工作线程已启动")

    async def stop_worker(self) -> None:
        """停止队列工作线程"""
        if not self._processing:
            return

        self._processing = False

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("任务队列工作线程已停止")

    async def _worker_loop(self, handler: Any) -> None:
        """工作线程循环"""
        while self._processing:
            try:
                # 从队列获取任务
                task_data = await self.dequeue_task()

                if task_data:
                    # 执行任务处理
                    try:
                        await handler(task_data)
                    except Exception as e:
                        logger.error(
                            f"任务处理失败: task_id={task_data.get('task_id')}, error={e}",
                            exc_info=True,
                        )
                else:
                    # 队列为空，等待一段时间
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"队列工作线程错误: {e}", exc_info=True)
                await asyncio.sleep(5)


# =============================================================================
# 全局任务队列管理器实例
# =============================================================================

_task_queue_manager: Optional[TaskQueueManager] = None


def get_task_queue_manager() -> TaskQueueManager:
    """获取全局任务队列管理器实例"""
    global _task_queue_manager
    if _task_queue_manager is None:
        _task_queue_manager = TaskQueueManager()
    return _task_queue_manager


async def start_task_queue() -> None:
    """启动任务队列"""

    queue_manager = get_task_queue_manager()

    # 定义任务处理函数
    async def task_handler(task_data: Dict[str, Any]) -> None:
        """处理队列中的任务"""
        # 这里任务已经在 execute_analysis_workflow 中被处理
        # 队列主要用于批量任务的调度控制
        logger.info(f"处理队列任务: task_id={task_data['task_id']}")

        # 任务实际执行在 background_tasks 中完成
        # 这里主要用于标记任务从队列中取出

    await queue_manager.start_worker(task_handler)
    logger.info("任务队列已启动")


async def stop_task_queue() -> None:
    """停止任务队列"""
    queue_manager = get_task_queue_manager()
    await queue_manager.stop_worker()
    logger.info("任务队列已停止")
