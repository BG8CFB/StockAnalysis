"""
任务过期处理模块

定期扫描运行中的任务，标记超过 24 小时未完成的任务为过期状态。
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.db.mongodb import mongodb
from core.mcp.pool.pool import get_mcp_connection_pool
from modules.trading_agents.schemas import TaskStatusEnum


def _get_batch_manager() -> Any:
    """延迟导入 BatchTaskManager，避免循环依赖"""
    from modules.trading_agents.manager.batch_manager import get_batch_manager

    return get_batch_manager()


logger = logging.getLogger(__name__)


# 任务超时时间（小时）
TASK_TIMEOUT_HOURS = 24


class TaskExpiryHandler:
    """
    任务过期处理器

    定期扫描运行中的任务，标记超时任务为过期状态。
    """

    def __init__(
        self,
        check_interval_seconds: int = 3600,  # 默认每小时扫描一次
        timeout_hours: int = TASK_TIMEOUT_HOURS,
    ):
        """
        初始化过期处理器

        Args:
            check_interval_seconds: 扫描间隔（秒）
            timeout_hours: 任务超时时间（小时）
        """
        self.check_interval_seconds = check_interval_seconds
        self.timeout_hours = timeout_hours
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动过期处理任务"""
        if self._running:
            logger.warning("任务过期处理器已在运行中")
            return

        self._running = True
        self._task = asyncio.create_task(self._expiry_loop())
        logger.info(
            f"任务过期处理器已启动: "
            f"扫描间隔={self.check_interval_seconds}秒, "
            f"超时时间={self.timeout_hours}小时"
        )

    async def stop(self) -> None:
        """停止过期处理任务"""
        if not self._running:
            return

        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("任务过期处理器已停止")

    async def _expiry_loop(self) -> None:
        """过期处理循环"""
        while self._running:
            try:
                await self._check_and_expire_tasks()
            except Exception as e:
                logger.error(f"任务过期处理失败: {e}", exc_info=True)

            # 等待下一次扫描
            await asyncio.sleep(self.check_interval_seconds)

    async def _check_and_expire_tasks(self) -> None:
        """检查并标记过期任务"""
        collection = mongodb.get_collection("analysis_tasks")

        # 计算超时阈值
        timeout_threshold = datetime.now(timezone.utc) - timedelta(hours=self.timeout_hours)

        # 查找运行中且超时的任务（使用 started_at 判断实际执行时长，而非创建时间）
        query = {
            "status": TaskStatusEnum.RUNNING.value,
            "started_at": {"$lt": timeout_threshold, "$ne": None},
        }

        expired_tasks = await collection.find(query).to_list(None)

        if not expired_tasks:
            logger.debug("没有过期任务")
            return

        logger.info(f"发现 {len(expired_tasks)} 个过期任务")

        # 处理每个过期任务
        for task_doc in expired_tasks:
            task_id = str(task_doc["_id"])
            user_id = task_doc["user_id"]
            stock_code = task_doc.get("stock_code", "未知")

            try:
                # 原子更新：仅在仍为 RUNNING 状态时才过期，避免 TOCTOU 竞态
                update_result = await collection.update_one(
                    {"_id": task_doc["_id"], "status": TaskStatusEnum.RUNNING.value},
                    {
                        "$set": {
                            "status": TaskStatusEnum.EXPIRED.value,
                            "expired_at": datetime.now(timezone.utc),
                            "error_message": f"任务执行超时（超过 {self.timeout_hours} 小时）",
                        }
                    },
                )

                if update_result.modified_count == 0:
                    # 任务在扫描期间已被其他操作更改状态，跳过
                    logger.debug(f"任务状态已变更，跳过过期处理: task_id={task_id}")
                    continue

                # 释放 MCP 连接（防止连接泄漏）
                try:
                    mcp_pool = get_mcp_connection_pool()
                    await mcp_pool.mark_task_failed(task_id)
                    logger.info(f"已释放过期任务的 MCP 连接: task_id={task_id}")
                except Exception as mcp_error:
                    logger.warning(
                        f"释放 MCP 连接失败（任务可能没有 MCP 连接）: "
                        f"task_id={task_id}, error={mcp_error}"
                    )

                # 通知 BatchTaskManager，确保批量任务队列继续推进
                batch_id = task_doc.get("batch_id")
                if batch_id:
                    try:
                        batch_manager = _get_batch_manager()
                        await batch_manager.on_task_completed(task_id, batch_id)
                        logger.info(
                            f"已通知 BatchTaskManager 过期任务: "
                            f"task_id={task_id}, batch_id={batch_id}"
                        )
                    except Exception as batch_error:
                        logger.error(
                            f"通知 BatchTaskManager 失败: "
                            f"task_id={task_id}, batch_id={batch_id}, error={batch_error}"
                        )

                logger.info(
                    f"任务已标记为过期: task_id={task_id}, "
                    f"user_id={user_id}, stock={stock_code}"
                )

            except Exception as e:
                logger.error(f"处理过期任务失败: task_id={task_id}, error={e}", exc_info=True)

    async def expire_task_now(self, task_id: str) -> bool:
        """
        立即标记指定任务为过期

        Args:
            task_id: 任务 ID

        Returns:
            是否标记成功
        """
        collection = mongodb.get_collection("analysis_tasks")

        try:
            from bson import ObjectId

            # 原子更新：条件写入，仅当状态为 RUNNING 时才修改，消除 TOCTOU 竞态
            result = await collection.update_one(
                {"_id": ObjectId(task_id), "status": TaskStatusEnum.RUNNING.value},
                {
                    "$set": {
                        "status": TaskStatusEnum.EXPIRED.value,
                        "expired_at": datetime.now(timezone.utc),
                        "error_message": f"任务执行超时（超过 {self.timeout_hours} 小时）",
                    }
                },
            )

            if result.modified_count == 0:
                # 任务不存在或不在 RUNNING 状态
                task_doc = await collection.find_one({"_id": ObjectId(task_id)}, {"status": 1})
                if not task_doc:
                    logger.warning(f"任务不存在: task_id={task_id}")
                else:
                    logger.warning(
                        f"任务不在运行状态，无法标记过期: "
                        f"task_id={task_id}, status={task_doc.get('status')}"
                    )
                return False

            # 释放 MCP 连接（防止连接泄漏）
            try:
                mcp_pool = get_mcp_connection_pool()
                await mcp_pool.mark_task_failed(task_id)
                logger.info(f"已释放过期任务的 MCP 连接: task_id={task_id}")
            except Exception as mcp_error:
                logger.debug(
                    f"释放 MCP 连接失败（任务可能没有 MCP 连接）: "
                    f"task_id={task_id}, error={mcp_error}"
                )

            logger.info(f"任务已手动标记为过期: task_id={task_id}")

            return True

        except Exception as e:
            logger.error(f"标记任务过期失败: task_id={task_id}, error={e}", exc_info=True)
            return False


# =============================================================================
# 全局过期处理器实例
# =============================================================================

_expiry_handler: Optional[TaskExpiryHandler] = None


def get_expiry_handler() -> TaskExpiryHandler:
    """获取全局过期处理器实例"""
    global _expiry_handler
    if _expiry_handler is None:
        _expiry_handler = TaskExpiryHandler()
    return _expiry_handler


async def start_expiry_handler() -> None:
    """启动全局过期处理器"""
    handler = get_expiry_handler()
    await handler.start()


async def stop_expiry_handler() -> None:
    """停止全局过期处理器"""
    global _expiry_handler
    if _expiry_handler is not None:
        await _expiry_handler.stop()
