"""
批量任务管理器

实现批量任务限制：
- 公共模型：最多 5 个任务同时执行
- 自定义模型：无限制
- 任务队列管理
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from core.db.mongodb import mongodb
from modules.trading_agents.core.exceptions import ConcurrencyLimitException

logger = logging.getLogger(__name__)


# =============================================================================
# 配置常量
# =============================================================================

PUBLIC_MODEL_MAX_BATCH_SIZE = 5  # 公共模型批量任务最大并发数


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class BatchTaskResult:
    """批量任务结果"""
    immediate_tasks: List[str]  # 立即执行的任务 ID
    waiting_tasks: List[str]    # 等待执行的任务 ID
    total_count: int
    immediate_count: int
    waiting_count: int


@dataclass
class BatchTaskInfo:
    """批量任务信息"""
    batch_id: str
    user_id: str
    stock_codes: List[str]
    model_id: str
    is_public_model: bool
    status: str  # pending, running, completed, partial, failed
    task_ids: List[str]  # 所有任务 ID
    immediate_task_ids: List[str]  # 立即执行的任务 ID
    waiting_task_ids: List[str]    # 等待执行的任务 ID
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


# =============================================================================
# 批量任务管理器
# =============================================================================

class BatchTaskManager:
    """
    批量任务管理器

    管理批量分析任务的提交、执行和监控。
    """

    def __init__(self):
        """初始化批量任务管理器"""
        # 追踪运行中的批量任务
        self._active_batches: Dict[str, BatchTaskInfo] = {}
        # 追踪等待中的任务
        self._waiting_tasks: Dict[str, List[str]] = {}

    async def submit_batch(
        self,
        user_id: str,
        stock_codes: List[str],
        model_id: str,
        is_public_model: bool,
        config: Dict[str, Any],
        task_ids: Optional[List[str]] = None
    ) -> BatchTaskResult:
        """
        提交批量任务

        Args:
            user_id: 用户 ID
            stock_codes: 股票代码列表
            model_id: 使用的模型 ID
            is_public_model: 是否为公共模型
            config: 分析配置
            task_ids: 任务 ID 列表（与 stock_codes 对应）

        Returns:
            批量任务结果
        """
        if not stock_codes:
            raise ValueError("股票代码列表不能为空")

        # 计算可立即执行的任务数
        if is_public_model:
            # 公共模型：最多 5 个任务同时执行
            max_concurrent = PUBLIC_MODEL_MAX_BATCH_SIZE
            logger.info(f"公共模型批量任务限制: user={user_id}, 最大并发={max_concurrent}")
        else:
            # 自定义模型：无限制
            max_concurrent = len(stock_codes)
            logger.info(f"自定义模型批量任务无限制: user={user_id}")

        immediate_count = min(max_concurrent, len(stock_codes))
        waiting_count = len(stock_codes) - immediate_count

        # 创建批量任务记录
        batch_id = await self._create_batch_record(
            user_id=user_id,
            stock_codes=stock_codes,
            model_id=model_id,
            is_public_model=is_public_model,
            immediate_count=immediate_count,
            waiting_count=waiting_count,
            config=config
        )

        logger.info(
            f"批量任务提交成功: batch_id={batch_id}, user={user_id}, "
            f"立即执行={immediate_count}, 等待={waiting_count}"
        )

        # 返回结果（任务 ID 或股票代码）
        if task_ids:
            return BatchTaskResult(
                immediate_tasks=task_ids[:immediate_count],
                waiting_tasks=task_ids[immediate_count:],
                total_count=len(stock_codes),
                immediate_count=immediate_count,
                waiting_count=waiting_count
            )
        else:
            # 向后兼容：返回股票代码
            return BatchTaskResult(
                immediate_tasks=stock_codes[:immediate_count],
                waiting_tasks=stock_codes[immediate_count:],
                total_count=len(stock_codes),
                immediate_count=immediate_count,
                waiting_count=waiting_count
            )

    async def notify_task_completed(
        self,
        batch_id: str,
        task_id: str
    ) -> Optional[str]:
        """
        通知任务完成，检查是否需要启动等待中的任务

        Args:
            batch_id: 批量任务 ID
            task_id: 已完成的任务 ID

        Returns:
            如果有等待中的任务需要启动，返回下一个股票代码；否则返回 None
        """
        # 获取批量任务信息
        batch_info = await self._get_batch_info(batch_id)
        if not batch_info:
            return None

        # 检查是否还有等待中的任务
        if not batch_info.waiting_task_ids:
            # 所有任务完成，更新批量任务状态
            if len(batch_info.immediate_task_ids) >= len(batch_info.stock_codes):
                batch_info.status = "completed"
                batch_info.completed_at = datetime.utcnow()
                await self._update_batch_info(batch_id, batch_info)
                logger.info(f"批量任务全部完成: batch_id={batch_id}")
            return None

        # 启动下一个等待中的任务
        next_stock_code = batch_info.waiting_task_ids[0]
        batch_info.waiting_task_ids.pop(0)
        batch_info.immediate_task_ids.append(task_id)

        # 更新批量任务记录
        await self._update_batch_info(batch_id, batch_info)

        logger.info(
            f"批量任务启动下一个: batch_id={batch_id}, stock_code={next_stock_code}, "
            f"剩余等待={len(batch_info.waiting_task_ids)}"
        )

        return next_stock_code

    async def get_public_model_running_count(self) -> int:
        """
        获取当前使用公共模型运行的任务数量

        Returns:
            运行中的任务数量
        """
        count = await mongodb.database.analysis_tasks.count_documents({
            "status": "running",
            "is_public_model": True
        })
        return count

    async def can_start_public_model_task(self) -> bool:
        """
        检查是否可以启动新的公共模型任务

        Returns:
            是否可以启动
        """
        running_count = await self.get_public_model_running_count()
        return running_count < PUBLIC_MODEL_MAX_BATCH_SIZE

    async def cancel_batch(self, batch_id: str) -> bool:
        """
        取消批量任务（取消所有未开始的任务）

        Args:
            batch_id: 批量任务 ID

        Returns:
            是否成功取消
        """
        batch_info = await self._get_batch_info(batch_id)
        if not batch_info:
            return False

        # 取消所有等待中的任务
        cancelled_count = 0
        for stock_code in batch_info.waiting_task_ids:
            # 注意：waiting_task_ids 中存储的是股票代码，还未创建任务
            # 在实际实现中，应该追踪等待中的任务 ID 并取消
            logger.info(f"跳过未创建的任务: stock_code={stock_code}")
            cancelled_count += 1

        # 更新批量任务状态
        batch_info.waiting_task_ids = []
        if cancelled_count > 0:
            batch_info.status = "partial"
        await self._update_batch_info(batch_id, batch_info)

        logger.info(
            f"批量任务取消成功: batch_id={batch_id}, "
            f"已取消={cancelled_count}, 已完成={len(batch_info.immediate_task_ids)}"
        )

        return True

    async def get_batch_status(self, batch_id: str) -> Optional[BatchTaskInfo]:
        """
        获取批量任务状态

        Args:
            batch_id: 批量任务 ID

        Returns:
            批量任务信息
        """
        return await self._get_batch_info(batch_id)

    # ========================================================================
    # 内部方法
    # ========================================================================

    async def _create_batch_record(
        self,
        user_id: str,
        stock_codes: List[str],
        model_id: str,
        is_public_model: bool,
        immediate_count: int,
        waiting_count: int,
        config: Dict[str, Any]
    ) -> str:
        """创建批量任务记录"""
        batch_id = f"batch_{datetime.utcnow().timestamp()}_{user_id}"

        batch_info = BatchTaskInfo(
            batch_id=batch_id,
            user_id=user_id,
            stock_codes=stock_codes,
            model_id=model_id,
            is_public_model=is_public_model,
            status="pending",
            task_ids=[],  # 任务 ID 在外部创建后填充
            immediate_task_ids=[],
            waiting_task_ids=stock_codes[immediate_count:],
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow() if immediate_count > 0 else None,
            completed_at=None,
            error_message=None
        )

        # 保存到数据库
        await mongodb.database.batch_tasks.insert_one({
            "batch_id": batch_id,
            "user_id": user_id,
            "stock_codes": stock_codes,
            "model_id": model_id,
            "is_public_model": is_public_model,
            "status": batch_info.status,
            "task_ids": batch_info.task_ids,
            "immediate_task_ids": batch_info.immediate_task_ids,
            "waiting_task_ids": batch_info.waiting_task_ids,
            "created_at": batch_info.created_at,
            "started_at": batch_info.started_at,
            "completed_at": batch_info.completed_at,
            "error_message": batch_info.error_message,
            "config": config
        })

        return batch_id

    async def _get_batch_info(self, batch_id: str) -> Optional[BatchTaskInfo]:
        """从数据库获取批量任务信息"""
        doc = await mongodb.database.batch_tasks.find_one({"batch_id": batch_id})
        if not doc:
            return None

        return BatchTaskInfo(
            batch_id=doc["batch_id"],
            user_id=doc["user_id"],
            stock_codes=doc["stock_codes"],
            model_id=doc["model_id"],
            is_public_model=doc["is_public_model"],
            status=doc["status"],
            task_ids=doc["task_ids"],
            immediate_task_ids=doc["immediate_task_ids"],
            waiting_task_ids=doc["waiting_task_ids"],
            created_at=doc["created_at"],
            started_at=doc.get("started_at"),
            completed_at=doc.get("completed_at"),
            error_message=doc.get("error_message")
        )

    async def _update_batch_info(self, batch_id: str, batch_info: BatchTaskInfo) -> None:
        """更新批量任务记录"""
        await mongodb.database.batch_tasks.update_one(
            {"batch_id": batch_id},
            {"$set": {
                "status": batch_info.status,
                "task_ids": batch_info.task_ids,
                "immediate_task_ids": batch_info.immediate_task_ids,
                "waiting_task_ids": batch_info.waiting_task_ids,
                "started_at": batch_info.started_at,
                "completed_at": batch_info.completed_at,
                "error_message": batch_info.error_message
            }}
        )

    async def _cancel_single_task(self, task_id: str) -> None:
        """取消单个任务"""
        # 标记任务为已取消
        from bson import ObjectId

        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"status": "cancelled", "completed_at": datetime.utcnow()}}
        )


# =============================================================================
# 全局批量任务管理器实例
# =============================================================================

batch_manager = BatchTaskManager()


def get_batch_manager() -> BatchTaskManager:
    """获取全局批量任务管理器实例"""
    return batch_manager
