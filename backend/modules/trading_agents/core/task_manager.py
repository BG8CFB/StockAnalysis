"""
任务管理器

负责管理分析任务的创建、执行、取消和状态追踪。
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.core.task_manager_restore import (
    restore_running_tasks_with_checkpoint,
)
from modules.trading_agents.core.state import AgentState, create_initial_state
from modules.trading_agents.schemas import (
    TaskStatusEnum,
    AnalysisTaskCreate,
    BatchTaskCreate,
    RecommendationEnum,
)
from modules.trading_agents.core.exceptions import (
    TaskNotFoundException,
    TaskAlreadyRunningException,
    TaskCancelledException,
)
from modules.trading_agents.websocket import (
    websocket_manager,
    create_event,
    create_task_completed_event,
    create_task_failed_event,
)
# MCP 连接释放支持
from modules.trading_agents.tools.mcp_tool_filter import (
    complete_task_connections,
    fail_task_connections,
    release_task_connections,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 任务管理器
# =============================================================================

class TaskManager:
    """
    任务管理器

    负责：
    - 创建任务
    - 查询任务状态
    - 取消任务
    - 任务队列管理
    """

    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def create_task(
        self,
        user_id: str,
        request: AnalysisTaskCreate,
        config: Dict[str, Any],
    ) -> str:
        """
        创建分析任务

        Args:
            user_id: 用户 ID
            request: 分析任务请求
            config: 智能体配置快照

        Returns:
            任务 ID
        """
        # 使用 ObjectId 作为任务 ID
        task_id = ObjectId()

        # 创建任务文档
        task_doc = {
            "_id": task_id,
            "user_id": user_id,
            "stock_code": request.stock_code,
            "market": request.market,
            "trade_date": request.trade_date,
            "status": TaskStatusEnum.PENDING.value,
            "current_phase": 0,
            "current_agent": None,
            "progress": 0.0,
            "reports": {},
            "final_recommendation": None,
            "buy_price": None,
            "sell_price": None,
            "token_usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "error_message": None,
            "error_details": None,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "expired_at": None,
            "config_snapshot": config,
            "stages": request.stages.model_dump(),
            "batch_id": None,
            "interrupt_signal": False,
        }

        # 插入数据库
        await mongodb.database.analysis_tasks.insert_one(task_doc)

        logger.info(f"创建分析任务: task_id={task_id}, user_id={user_id}, stock={request.stock_code}, market={request.market}")

        # 发送任务创建事件
        await websocket_manager.broadcast_event(
            str(task_id),
            create_event(
                event_type="task_created",
                task_id=str(task_id),
                stock_code=request.stock_code,
                trade_date=request.trade_date,
            )
        )

        return str(task_id)

    async def create_batch_task(
        self,
        user_id: str,
        request: BatchTaskCreate,
        config: Dict[str, Any],
    ) -> str:
        """
        创建批量分析任务

        Args:
            user_id: 用户 ID
            request: 批量任务请求
            config: 智能体配置快照

        Returns:
            批量任务 ID
        """
        # 使用 ObjectId 作为批量任务 ID
        batch_id = ObjectId()

        # 为每个股票创建任务
        for stock_code in request.stock_codes:
            task_id = await self.create_task(
                user_id=user_id,
                request=AnalysisTaskCreate(
                    stock_code=stock_code,
                    market=request.market,
                    trade_date=request.trade_date,
                    stages=request.stages,
                ),
                config=config,
            )

            # 更新任务的 batch_id
            await mongodb.database.analysis_tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"batch_id": str(batch_id)}}
            )

        logger.info(f"创建批量任务: batch_id={batch_id}, count={len(request.stock_codes)}, market={request.market}")

        return str(batch_id)

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态字典

        Raises:
            TaskNotFoundException: 任务不存在
        """
        task_doc = await mongodb.database.analysis_tasks.find_one({"_id": ObjectId(task_id)})

        if not task_doc:
            raise TaskNotFoundException(task_id)

        # 转换为字典格式
        return {
            "id": str(task_doc["_id"]),
            "user_id": task_doc["user_id"],
            "stock_code": task_doc["stock_code"],
            "trade_date": task_doc["trade_date"],
            "status": task_doc["status"],
            "current_phase": task_doc.get("current_phase", 0),
            "current_agent": task_doc.get("current_agent"),
            "progress": task_doc.get("progress", 0.0),
            "reports": task_doc.get("reports", {}),
            "final_recommendation": task_doc.get("final_recommendation"),
            "buy_price": task_doc.get("buy_price"),
            "sell_price": task_doc.get("sell_price"),
            "token_usage": task_doc.get("token_usage", {}),
            "error_message": task_doc.get("error_message"),
            "error_details": task_doc.get("error_details"),
            "created_at": task_doc["created_at"],
            "started_at": task_doc.get("started_at"),
            "completed_at": task_doc.get("completed_at"),
            "expired_at": task_doc.get("expired_at"),
            "batch_id": task_doc.get("batch_id"),
        }

    async def list_tasks(
        self,
        user_id: str,
        status: Optional[TaskStatusEnum] = None,
        stock_code: Optional[str] = None,
        recommendation: Optional[str] = None,
        risk_level: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出用户的任务

        Args:
            user_id: 用户 ID
            status: 状态过滤
            stock_code: 股票代码过滤
            recommendation: 推荐结果过滤
            risk_level: 风险等级过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            任务列表
        """
        # 构建查询条件
        query = {"user_id": user_id}

        if status:
            query["status"] = status.value

        if stock_code:
            query["stock_code"] = stock_code

        if recommendation:
            query["final_recommendation"] = recommendation

        if risk_level:
            query["risk_level"] = risk_level

        # 查询数据库
        cursor = mongodb.database.analysis_tasks.find(query).sort("created_at", -1).skip(offset).limit(limit)

        tasks = []
        async for task_doc in cursor:
            tasks.append({
                "id": str(task_doc["_id"]),
                "stock_code": task_doc["stock_code"],
                "trade_date": task_doc["trade_date"],
                "status": task_doc["status"],
                "progress": task_doc.get("progress", 0.0),
                "final_recommendation": task_doc.get("final_recommendation"),
                "risk_level": task_doc.get("risk_level"),
                "buy_price": task_doc.get("buy_price"),
                "sell_price": task_doc.get("sell_price"),
                "created_at": task_doc["created_at"],
                "completed_at": task_doc.get("completed_at"),
            })

        return tasks

    async def count_tasks(
        self,
        user_id: str,
        status: Optional[TaskStatusEnum] = None,
        stock_code: Optional[str] = None,
        recommendation: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> int:
        """
        统计用户任务数量

        Args:
            user_id: 用户 ID
            status: 状态过滤
            stock_code: 股票代码过滤
            recommendation: 推荐结果过滤
            risk_level: 风险等级过滤

        Returns:
            任务数量
        """
        # 构建查询条件
        query = {"user_id": user_id}

        if status:
            query["status"] = status.value

        if stock_code:
            query["stock_code"] = stock_code

        if recommendation:
            query["final_recommendation"] = recommendation

        if risk_level:
            query["risk_level"] = risk_level

        # 统计数量
        count = await mongodb.database.analysis_tasks.count_documents(query)
        return count

    async def cancel_task(self, task_id: str) -> None:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Raises:
            TaskNotFoundException: 任务不存在
        """
        task_doc = await mongodb.database.analysis_tasks.find_one({"_id": ObjectId(task_id)})

        if not task_doc:
            raise TaskNotFoundException(task_id)

        status = task_doc["status"]

        if status == TaskStatusEnum.COMPLETED.value:
            raise TaskAlreadyRunningException(task_id, "任务已完成，无法取消")

        if status == TaskStatusEnum.CANCELLED.value:
            return  # 已取消，无需重复操作

        # 更新任务状态
        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "status": TaskStatusEnum.CANCELLED.value,
                    "interrupt_signal": True,
                    "completed_at": datetime.utcnow(),
                }
            }
        )

        # 取消正在运行的任务（如果有）
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            del self._running_tasks[task_id]

        # 发送任务取消事件
        await websocket_manager.broadcast_event(
            task_id,
            create_event(
                event_type="task_cancelled",
                task_id=task_id,
            )
        )

        # 立即释放 MCP 连接（任务取消不需要延迟）
        try:
            await release_task_connections(task_id)
        except Exception as e:
            logger.warning(f"MCP 连接释放失败: task_id={task_id}, error={e}")

        logger.info(f"任务已取消: task_id={task_id}")

    async def stop_task(self, task_id: str) -> None:
        """
        停止任务（中止执行）

        Args:
            task_id: 任务 ID

        Raises:
            TaskNotFoundException: 任务不存在
        """
        task_doc = await mongodb.database.analysis_tasks.find_one({"_id": ObjectId(task_id)})

        if not task_doc:
            raise TaskNotFoundException(task_id)

        status = task_doc["status"]

        # 只有运行中的任务可以停止
        if status != TaskStatusEnum.RUNNING.value:
            logger.warning(f"任务状态为 {status}，无法停止: task_id={task_id}")
            return

        # 设置中断信号
        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "status": TaskStatusEnum.STOPPED.value,
                    "interrupt_signal": True,
                    "completed_at": datetime.utcnow(),
                }
            }
        )

        # 取消正在运行的任务
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            del self._running_tasks[task_id]

        # 发送任务停止事件
        await websocket_manager.broadcast_event(
            task_id,
            create_event(
                event_type="task_stopped",
                task_id=task_id,
            )
        )

        # 立即释放 MCP 连接（任务停止不需要延迟）
        try:
            await release_task_connections(task_id)
        except Exception as e:
            logger.warning(f"MCP 连接释放失败: task_id={task_id}, error={e}")

        logger.info(f"任务已停止: task_id={task_id}")

    async def update_task_progress(
        self,
        task_id: str,
        progress: float,
        current_phase: Optional[int] = None,
        current_agent: Optional[str] = None,
    ) -> None:
        """
        更新任务进度

        Args:
            task_id: 任务 ID
            progress: 进度值 (0-100)
            current_phase: 当前阶段
            current_agent: 当前智能体
        """
        update_data = {"progress": progress}

        if current_phase is not None:
            update_data["current_phase"] = current_phase

        if current_agent is not None:
            update_data["current_agent"] = current_agent

        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": update_data}
        )

    async def add_task_report(
        self,
        task_id: str,
        agent_slug: str,
        report: str,
    ) -> None:
        """
        添加任务报告

        Args:
            task_id: 任务 ID
            agent_slug: 智能体标识
            report: 报告内容
        """
        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {f"reports.{agent_slug}": report}}
        )

    async def complete_task(
        self,
        task_id: str,
        final_recommendation: Optional[RecommendationEnum] = None,
        buy_price: Optional[float] = None,
        sell_price: Optional[float] = None,
        token_usage: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        完成任务

        Args:
            task_id: 任务 ID
            final_recommendation: 最终推荐结果
            buy_price: 买入价格
            sell_price: 卖出价格
            token_usage: Token 使用量
        """
        update_data = {
            "status": TaskStatusEnum.COMPLETED.value,
            "completed_at": datetime.utcnow(),
            "progress": 100.0,
        }

        if final_recommendation:
            update_data["final_recommendation"] = final_recommendation.value

        if buy_price is not None:
            update_data["buy_price"] = buy_price

        if sell_price is not None:
            update_data["sell_price"] = sell_price

        if token_usage:
            update_data["token_usage"] = token_usage

        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": update_data}
        )

        # 发送任务完成事件
        await websocket_manager.broadcast_event(
            task_id,
            create_task_completed_event(
                task_id=task_id,
                final_recommendation=final_recommendation.value if final_recommendation else None,
                buy_price=buy_price,
                sell_price=sell_price,
                total_token_usage=token_usage or {},
            )
        )

        # 移除运行中的任务
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

        # 标记 MCP 连接为完成状态（延迟 10 秒后销毁）
        try:
            await complete_task_connections(task_id)
        except Exception as e:
            logger.warning(f"MCP 连接完成标记失败: task_id={task_id}, error={e}")

        logger.info(f"任务已完成: task_id={task_id}, recommendation={final_recommendation}")

    async def fail_task(
        self,
        task_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        标记任务失败

        Args:
            task_id: 任务 ID
            error_message: 错误消息
            error_details: 错误详情
        """
        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "status": TaskStatusEnum.FAILED.value,
                    "error_message": error_message,
                    "error_details": error_details,
                    "completed_at": datetime.utcnow(),
                }
            }
        )

        # 发送任务失败事件
        await websocket_manager.broadcast_event(
            task_id,
            create_task_failed_event(
                task_id=task_id,
                error_message=error_message,
                error_details=error_details,
            )
        )

        # 移除运行中的任务
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

        # 标记 MCP 连接为失败状态（延迟 30 秒后销毁）
        try:
            await fail_task_connections(task_id)
        except Exception as e:
            logger.warning(f"MCP 连接失败标记失败: task_id={task_id}, error={e}")

        logger.error(f"任务失败: task_id={task_id}, error={error_message}")

    async def mark_task_running(self, task_id: str) -> None:
        """
        标记任务为运行中

        Args:
            task_id: 任务 ID
        """
        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "status": TaskStatusEnum.RUNNING.value,
                    "started_at": datetime.utcnow(),
                }
            }
        )

    async def check_interrupt(self, task_id: str) -> bool:
        """
        检查任务是否被中断

        Args:
            task_id: 任务 ID

        Returns:
            是否应该中断
        """
        task_doc = await mongodb.database.analysis_tasks.find_one({"_id": ObjectId(task_id)})

        if not task_doc:
            return True  # 任务不存在，应该中断

        return task_doc.get("interrupt_signal", False)

    async def reset_interrupt_signal(self, task_id: str) -> None:
        """
        重置中断信号

        Args:
            task_id: 任务 ID
        """
        await mongodb.database.analysis_tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"interrupt_signal": False}}
        )

    async def restore_running_tasks(self) -> int:
        """
        恢复运行中的任务（增强版）

        系统重启后，检查每个运行中的任务：
        1. 验证配置中的智能体是否存在
        2. 如果智能体被删除，标记任务为失败
        3. 否则，重置为 PENDING 状态，保留已完成报告

        Returns:
            恢复的任务数量（失败的任务不计入）
        """
        # 调用增强恢复函数
        restored_count, failed_count = await restore_running_tasks_with_checkpoint(
            mongodb
        )

        if failed_count > 0:
            logger.warning(f"有 {failed_count} 个任务恢复失败并已标记为失败状态")

        return restored_count

    async def get_running_tasks_count(self) -> int:
        """
        获取运行中的任务数量

        Returns:
            运行中的任务数量
        """
        count = await mongodb.database.analysis_tasks.count_documents({
            "status": TaskStatusEnum.RUNNING.value
        })
        return count


# =============================================================================
# 全局任务管理器实例
# =============================================================================

task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    return task_manager
