"""
批量任务管理器

实现真正的批量任务控制：
- 只创建可立即执行的任务（基于模型配置的并发限制）
- 任务完成后自动触发下一批任务创建
- 使用生产者-消费者模式
- 多用户隔离，每个用户独立的批量任务队列
- 批量并发数从模型配置读取
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.schemas import AnalysisTaskCreate

logger = logging.getLogger(__name__)


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

        logger.info("[BatchTaskManager] 批量任务管理器初始化完成")

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
        async with self._lock:
            context = self._batch_contexts.get(batch_id)
            if not context:
                logger.warning(f"[BatchTaskManager] 批量任务上下文不存在: batch_id={batch_id}")
                return None

            # 减少运行中计数
            context.running_count -= 1

            # 如果没有待处理的股票，删除上下文
            if not context.pending_stocks:
                del self._batch_contexts[batch_id]
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

            # 如果没有待处理的股票，删除上下文
            if not context.pending_stocks:
                del self._batch_contexts[batch_id]

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
        async with self._lock:
            context = self._batch_contexts.get(batch_id)
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
        async with self._lock:
            context = self._batch_contexts.get(batch_id)
            if not context:
                return {
                    "success": False,
                    "message": "批量任务不存在或已完成",
                }

            pending_count = len(context.pending_stocks)
            created_count = len(context.created_tasks)

            # 清空待处理列表
            context.pending_stocks.clear()

            # 删除上下文
            del self._batch_contexts[batch_id]

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
