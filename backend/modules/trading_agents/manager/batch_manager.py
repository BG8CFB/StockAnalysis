"""
批量任务管理器

实现真正的批量任务控制：
- 只创建可立即执行的任务（基于模型配置的并发限制）
- 任务完成后自动触发下一批任务创建
- 使用生产者-消费者模式
- 多用户隔离，每个用户独立的批量任务队列
- 批量并发数从模型配置读取
- 批量上下文持久化到 Mongo，支持重启后恢复未完成批量

**并发安全说明**：
- 所有对 _batch_contexts 的操作都在 _lock 保护下进行
- on_task_completed 中的任务创建在同一锁内完成，避免竞争条件
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.schemas import AnalysisTaskCreate
from modules.trading_agents.schemas import TaskStatusEnum

logger = logging.getLogger(__name__)

# 批量任务上下文持久化集合
BATCH_CONTEXTS_COLLECTION = "batch_task_contexts"


# =============================================================================
# 数据模型
# =============================================================================


@dataclass
class BatchTaskContext:
    """批量任务上下文"""

    batch_id: str
    user_id: str
    stock_codes: List[str]  # 所有待处理的股票代码
    request: AnalysisTaskCreate  # 原始请求（市场、日期、阶段等）
    config: Dict[str, Any]  # 智能体配置
    max_concurrent: int  # 最大并发数（从模型配置读取）
    batch_name: Optional[str] = None  # 批量任务名称
    created_tasks: List[str] = field(default_factory=list)  # 已创建的任务 ID
    pending_stocks: List[str] = field(default_factory=list)  # 待处理的股票代码
    running_count: int = 0  # 当前运行中的任务数
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # 创建时间


def _context_to_doc(ctx: BatchTaskContext) -> Dict[str, Any]:
    """将 BatchTaskContext 转为 Mongo 文档（用于持久化）"""
    return {
        "_id": ctx.batch_id,
        "user_id": ctx.user_id,
        "stock_codes": ctx.stock_codes,
        "request": ctx.request.model_dump(),
        "config": ctx.config,
        "max_concurrent": ctx.max_concurrent,
        "batch_name": ctx.batch_name,
        "created_tasks": ctx.created_tasks,
        "pending_stocks": ctx.pending_stocks,
        "running_count": ctx.running_count,
        "created_at": ctx.created_at,
    }


def _doc_to_context(doc: Dict[str, Any]) -> BatchTaskContext:
    """从 Mongo 文档还原 BatchTaskContext"""
    return BatchTaskContext(
        batch_id=doc["_id"],
        user_id=doc["user_id"],
        stock_codes=doc["stock_codes"],
        request=AnalysisTaskCreate.model_validate(doc["request"]),
        config=doc["config"],
        max_concurrent=doc["max_concurrent"],
        batch_name=doc.get("batch_name"),
        created_tasks=doc.get("created_tasks", []),
        pending_stocks=doc.get("pending_stocks", []),
        running_count=doc.get("running_count", 0),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
    )


# =============================================================================
# 批量任务管理器
# =============================================================================


class BatchTaskManager:
    """
    批量任务管理器

    实现真正的批量任务控制：
    1. 只创建可立即执行的任务（基于并发限制）
    2. 任务完成后自动触发下一批任务创建
    3. 多用户隔离，每个用户独立的批量任务队列
    """

    def __init__(self):
        """初始化批量任务管理器"""
        # 批量任务上下文: {batch_id: BatchTaskContext}
        self._batch_contexts: Dict[str, BatchTaskContext] = {}
        # 锁
        self._lock = asyncio.Lock()
        # 是否已执行过启动恢复（延迟到首次使用时执行）
        self._restored = False

        logger.info("[BatchTaskManager] 批量任务管理器初始化完成")

    async def _ensure_restored(self) -> None:
        """确保已从 Mongo 恢复未完成的批量上下文（仅执行一次）"""
        if self._restored:
            return
        async with self._lock:
            if self._restored:
                return
            await self._load_all_unfinished_contexts()
            self._restored = True

    async def _persist_context(self, ctx: BatchTaskContext) -> None:
        """将批量上下文持久化到 Mongo"""
        coll = mongodb.database[BATCH_CONTEXTS_COLLECTION]
        doc = _context_to_doc(ctx)
        await coll.replace_one({"_id": ctx.batch_id}, doc, upsert=True)
        logger.debug(f"[BatchTaskManager] 已持久化批量上下文: batch_id={ctx.batch_id}")

    async def _delete_context_from_db(self, batch_id: str) -> None:
        """从 Mongo 删除批量上下文"""
        coll = mongodb.database[BATCH_CONTEXTS_COLLECTION]
        result = await coll.delete_one({"_id": batch_id})
        if result.deleted_count:
            logger.debug(f"[BatchTaskManager] 已删除持久化批量上下文: batch_id={batch_id}")

    async def _load_context_from_db(self, batch_id: str) -> Optional[BatchTaskContext]:
        """从 Mongo 加载单个批量上下文到内存（不自动放入 _batch_contexts，由调用方加锁后放入）"""
        coll = mongodb.database[BATCH_CONTEXTS_COLLECTION]
        doc = await coll.find_one({"_id": batch_id})
        if not doc:
            return None
        return _doc_to_context(doc)

    async def _load_all_unfinished_contexts(self) -> None:
        """启动时从 Mongo 加载所有未完成的批量上下文到内存"""
        coll = mongodb.database[BATCH_CONTEXTS_COLLECTION]
        # 未完成：有待处理股票（数组非空）或仍有运行中任务
        cursor = coll.find({
            "$or": [
                {"pending_stocks.0": {"$exists": True}},
                {"running_count": {"$gt": 0}},
            ]
        })
        count = 0
        async for doc in cursor:
            ctx = _doc_to_context(doc)
            self._batch_contexts[ctx.batch_id] = ctx
            count += 1
        if count:
            logger.info(f"[BatchTaskManager] 启动恢复: 已加载 {count} 个未完成批量上下文")

    async def create_batch(
        self,
        user_id: str,
        stock_codes: List[str],
        request: AnalysisTaskCreate,
        config: Dict[str, Any],
        max_concurrent: int,
        batch_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建批量任务（只创建第一批可执行的任务）

        Args:
            user_id: 用户 ID
            stock_codes: 股票代码列表
            request: 分析任务请求
            config: 智能体配置
            max_concurrent: 最大并发数（从模型配置读取）
            batch_name: 批量任务名称

        Returns:
            {
                "batch_id": str,
                "initial_task_ids": List[str],  # 第一批创建的任务 ID
                "pending_count": int,  # 剩余待创建的任务数
                "total_count": int,  # 总任务数
            }
        """
        await self._ensure_restored()

        if not stock_codes:
            raise ValueError("股票代码列表不能为空")

        # 生成批量任务 ID
        batch_id = str(ObjectId())

        # 计算第一批可创建的任务数（使用模型配置的批量并发数）
        initial_count = min(max_concurrent, len(stock_codes))
        pending_stocks = stock_codes[initial_count:]

        # 创建批量任务上下文
        context = BatchTaskContext(
            batch_id=batch_id,
            user_id=user_id,
            stock_codes=stock_codes,
            request=request,
            config=config,
            max_concurrent=max_concurrent,
            batch_name=batch_name,
            pending_stocks=pending_stocks,
        )

        async with self._lock:
            self._batch_contexts[batch_id] = context

        # 创建第一批任务
        initial_task_ids = []
        for i in range(initial_count):
            task_id = await self._create_single_task(
                user_id=user_id,
                stock_code=stock_codes[i],
                request=request,
                config=config,
                batch_id=batch_id,
                batch_name=batch_name,
            )
            initial_task_ids.append(task_id)
            context.created_tasks.append(task_id)
            context.running_count += 1

        logger.info(
            f"[BatchTaskManager] 创建批量任务: batch_id={batch_id}, "
            f"batch_name={batch_name}, "
            f"初始任务={len(initial_task_ids)}, 待处理={len(pending_stocks)}, "
            f"总计={len(stock_codes)}, 并发限制={max_concurrent}"
        )

        await self._persist_context(context)

        return {
            "batch_id": batch_id,
            "initial_task_ids": initial_task_ids,
            "pending_count": len(pending_stocks),
            "total_count": len(stock_codes),
        }

    async def on_task_completed(
        self,
        task_id: str,
        batch_id: str,
    ) -> Optional[List[str]]:
        """
        任务完成回调，触发下一批任务创建

        Args:
            task_id: 已完成的任务 ID
            batch_id: 批量任务 ID

        Returns:
            新创建的任务 ID 列表（如果有）
        """
        await self._ensure_restored()

        async with self._lock:
            context = self._batch_contexts.get(batch_id)
            if not context:
                logger.warning(f"[BatchTaskManager] 批量任务上下文不存在: batch_id={batch_id}")
                return None

            # 减少运行中计数
            context.running_count -= 1

            # 如果没有待处理的股票，删除上下文并持久化删除
            if not context.pending_stocks:
                del self._batch_contexts[batch_id]
                await self._delete_context_from_db(batch_id)
                logger.info(
                    f"[BatchTaskManager] 批量任务全部完成: batch_id={batch_id}, "
                    f"总任务数={len(context.created_tasks)}"
                )
                return None

            # 创建下一批任务
            new_task_ids = []
            slots_available = context.max_concurrent - context.running_count

            # 创建的任务数 = min(可用槽位, 待处理股票数)
            create_count = min(slots_available, len(context.pending_stocks))

            for _ in range(create_count):
                if not context.pending_stocks:
                    break

                stock_code = context.pending_stocks.pop(0)
                task_id = await self._create_single_task(
                    user_id=context.user_id,
                    stock_code=stock_code,
                    request=context.request,
                    config=context.config,
                    batch_id=batch_id,
                    batch_name=context.batch_name,
                )
                new_task_ids.append(task_id)
                context.created_tasks.append(task_id)
                context.running_count += 1

            if new_task_ids:
                logger.info(
                    f"[BatchTaskManager] 创建下一批任务: batch_id={batch_id}, "
                    f"新任务={len(new_task_ids)}, 剩余={len(context.pending_stocks)}"
                )

            # 如果没有待处理的股票，删除上下文并持久化删除
            if not context.pending_stocks:
                del self._batch_contexts[batch_id]
                await self._delete_context_from_db(batch_id)
            else:
                await self._persist_context(context)

            return new_task_ids if new_task_ids else None

    async def get_batch_status(
        self,
        batch_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取批量任务状态

        Args:
            batch_id: 批量任务 ID

        Returns:
            批量任务状态信息
        """
        await self._ensure_restored()

        async with self._lock:
            context = self._batch_contexts.get(batch_id)
            if not context:
                context = await self._load_context_from_db(batch_id)
                if context:
                    self._batch_contexts[batch_id] = context
            if not context:
                return None

            return {
                "batch_id": context.batch_id,
                "user_id": context.user_id,
                "total_count": len(context.stock_codes),
                "created_count": len(context.created_tasks),
                "pending_count": len(context.pending_stocks),
                "running_count": context.running_count,
                "max_concurrent": context.max_concurrent,
            }

    async def remove_task_from_batch(
        self,
        task_id: str,
        batch_id: str,
        stock_code: str,
        task_status: str,
    ) -> Dict[str, Any]:
        """
        从批量上下文中移除指定任务

        用于在删除任务时同步更新 BatchTaskContext，保持数据一致性。

        业务逻辑：
        - 从 created_tasks 中移除任务 ID
        - 如果任务是 PENDING/CANCELLED/FAILED（未开始运行），需要把股票代码加回 pending_stocks
        - 如果任务已经运行过，需要减少 running_count
        - 如果 pending_stocks 和 created_tasks 都为空且 running_count 为 0，清理 context

        Args:
            task_id: 要移除的任务 ID
            batch_id: 批量任务 ID
            stock_code: 任务对应的股票代码
            task_status: 任务状态

        Returns:
            {
                "success": bool,
                "message": str,
                "stock_restored": bool,  # 股票是否已恢复到待处理队列
                "running_decremented": bool,  # running_count 是否已减少
            }
        """
        await self._ensure_restored()

        async with self._lock:
            context = self._batch_contexts.get(batch_id)
            if not context:
                context = await self._load_context_from_db(batch_id)
                if context:
                    self._batch_contexts[batch_id] = context
            if not context:
                logger.warning(
                    f"[BatchTaskManager] 移除任务时批量上下文不存在: "
                    f"batch_id={batch_id}, task_id={task_id}"
                )
                return {
                    "success": False,
                    "message": "批量任务上下文不存在",
                    "stock_restored": False,
                    "running_decremented": False,
                }

            # 验证任务是否属于该 batch
            if task_id not in context.created_tasks:
                logger.warning(
                    f"[BatchTaskManager] 要移除的任务不属于该批量: "
                    f"batch_id={batch_id}, task_id={task_id}"
                )
                return {
                    "success": False,
                    "message": "任务不属于该批量",
                    "stock_restored": False,
                    "running_decremented": False,
                }

            # 从 created_tasks 中移除
            context.created_tasks.remove(task_id)

            stock_restored = False
            running_decremented = False

            # 判断任务是否已经开始运行
            # 只有 PENDING/CANCELLED/FAILED 状态表示任务未开始运行
            pending_statuses = {
                TaskStatusEnum.PENDING.value,
                TaskStatusEnum.CANCELLED.value,
                TaskStatusEnum.FAILED.value,
            }

            if task_status in pending_statuses:
                # 任务未开始运行，将股票加回待处理队列
                if stock_code and stock_code not in context.pending_stocks:
                    context.pending_stocks.append(stock_code)
                    stock_restored = True
                    logger.info(
                        f"[BatchTaskManager] 任务未运行，恢复股票到待处理队列: "
                        f"batch_id={batch_id}, task_id={task_id}, stock_code={stock_code}"
                    )
            else:
                # 任务已经开始运行过，减少 running_count
                if context.running_count > 0:
                    context.running_count -= 1
                    running_decremented = True
                    logger.info(
                        f"[BatchTaskManager] 任务已运行，减少 running_count: "
                        f"batch_id={batch_id}, task_id={task_id}, new_running={context.running_count}"
                    )

            # 如果批量任务已完成（没有待处理股票且没有已创建任务），清理 context 并持久化删除
            if not context.pending_stocks and not context.created_tasks:
                del self._batch_contexts[batch_id]
                await self._delete_context_from_db(batch_id)
                logger.info(
                    f"[BatchTaskManager] 批量任务上下文已清理: batch_id={batch_id}"
                )
            else:
                await self._persist_context(context)

            return {
                "success": True,
                "message": "成功从批量中移除任务",
                "stock_restored": stock_restored,
                "running_decremented": running_decremented,
            }

    async def cancel_batch(
        self,
        batch_id: str,
    ) -> Dict[str, Any]:
        """
        取消批量任务（取消所有未创建的任务）

        Args:
            batch_id: 批量任务 ID

        Returns:
            取消结果
        """
        await self._ensure_restored()

        async with self._lock:
            context = self._batch_contexts.get(batch_id)
            if not context:
                context = await self._load_context_from_db(batch_id)
                if context:
                    self._batch_contexts[batch_id] = context
            if not context:
                return {
                    "success": False,
                    "message": "批量任务不存在或已完成",
                }

            pending_count = len(context.pending_stocks)
            created_count = len(context.created_tasks)

            # 清空待处理列表
            context.pending_stocks.clear()

            # 删除上下文并持久化删除
            del self._batch_contexts[batch_id]
            await self._delete_context_from_db(batch_id)

            logger.info(
                f"[BatchTaskManager] 取消批量任务: batch_id={batch_id}, "
                f"已创建={created_count}, 已取消={pending_count}"
            )

            return {
                "success": True,
                "message": f"已取消 {pending_count} 个未创建的任务",
                "created_count": created_count,
                "cancelled_count": pending_count,
            }

    async def _create_single_task(
        self,
        user_id: str,
        stock_code: str,
        request: AnalysisTaskCreate,
        config: Dict[str, Any],
        batch_id: str,
        batch_name: Optional[str] = None,
    ) -> str:
        """
        创建单个任务

        Args:
            user_id: 用户 ID
            stock_code: 股票代码
            request: 原始请求
            config: 智能体配置
            batch_id: 批量任务 ID
            batch_name: 批量任务名称

        Returns:
            任务 ID
        """
        # 导入避免循环依赖
        from modules.trading_agents.manager.task_manager import get_task_manager

        task_manager = get_task_manager()

        # 创建单个任务请求
        single_request = AnalysisTaskCreate(
            stock_code=stock_code,
            market=request.market,
            trade_date=request.trade_date,
            stages=request.stages,
            data_collection_model=request.data_collection_model,
            debate_model=request.debate_model,
        )

        # 创建任务
        task_id = await task_manager.create_task(
            user_id=user_id,
            request=single_request,
            config=config,
        )

        # 更新任务的 batch_id 和 batch_name
        update_data = {"batch_id": batch_id}
        if batch_name:
            update_data["batch_name"] = batch_name

        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)}, {"$set": update_data}
        )

        return task_id


# =============================================================================
# 全局批量任务管理器实例
# =============================================================================

_batch_manager: Optional[BatchTaskManager] = None


def get_batch_manager() -> BatchTaskManager:
    """获取全局批量任务管理器实例"""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchTaskManager()
    return _batch_manager
