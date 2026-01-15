"""
任务管理器

负责管理分析任务的创建、执行、取消和状态追踪。
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.manager.task_manager_restore import (
    restore_running_tasks_with_checkpoint,
)
from modules.trading_agents.schemas import (
    TaskStatusEnum,
    AnalysisTaskCreate,
    BatchTaskCreate,
    RecommendationEnum,
    AnalysisStagesConfig,
)
from modules.trading_agents.exceptions import (
    TaskNotFoundException,
    TaskAlreadyRunningException,
)
from modules.trading_agents.api.websocket_manager import (
    get_ws_manager,
)
from modules.trading_agents.workflow.events import (
    EventType,
    create_event,
    create_task_completed_event,
    create_task_failed_event,
)
# MCP 连接释放支持
from modules.mcp.pool.pool import get_mcp_connection_pool

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
            # 保存模型选择，便于追踪和调试
            "data_collection_model": request.data_collection_model,
            "debate_model": request.debate_model,
        }

        # 插入数据库
        await mongodb.database.analysis_tasks.insert_one(task_doc)

        logger.info(
            f"创建分析任务: task_id={task_id}, user_id={user_id}, "
            f"stock={request.stock_code}, market={request.market}"
        )

        # 发送任务创建事件
        ws_manager = await get_ws_manager()
        await ws_manager.broadcast_event(
            str(task_id),
            create_event(
                event_type=EventType.TASK_CREATED,
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

        使用新的批量任务管理器：
        - 只创建可立即执行的任务（基于模型配置的批量并发数）
        - 任务完成后自动触发下一批任务创建

        Args:
            user_id: 用户 ID
            request: 批量任务请求
            config: 智能体配置快照

        Returns:
            批量任务 ID
        """
        from modules.trading_agents.manager.batch_manager import get_batch_manager

        # 获取模型配置中的批量并发数
        batch_concurrency = await self._get_model_batch_concurrency(user_id, request)

        # 使用批量任务管理器
        batch_manager = get_batch_manager()

        result = await batch_manager.create_batch(
            user_id=user_id,
            stock_codes=request.stock_codes,
            request=AnalysisTaskCreate(
                market=request.market,
                trade_date=request.trade_date,
                stages=request.stages,
                data_collection_model=request.data_collection_model,
                debate_model=request.debate_model,
            ),
            config=config,
            max_concurrent=batch_concurrency,
        )

        # 启动第一批任务
        for task_id in result["initial_task_ids"]:
            # 从数据库读取正确的任务信息
            task_doc = await mongodb.database.analysis_tasks.find_one(
                {"_id": ObjectId(task_id)}
            )

            if not task_doc:
                logger.error(f"找不到新创建的任务: task_id={task_id}")
                continue

            # 使用数据库中的正确信息
            asyncio.create_task(
                self.execute_analysis_workflow(
                    task_id=task_id,
                    user_id=user_id,
                    request=AnalysisTaskCreate(
                        stock_code=task_doc.get("stock_code", ""),  # 从数据库读取
                        market=task_doc.get("market", request.market),
                        trade_date=task_doc.get("trade_date", request.trade_date),
                        stages=AnalysisStagesConfig(**task_doc.get("stages", {})),
                        data_collection_model=task_doc.get("data_collection_model"),
                        debate_model=task_doc.get("debate_model"),
                    ),
                    _skip_model_loading=True,  # 跳过模型加载（已在后台任务中完成）
                )
            )

        logger.info(
            f"创建批量任务: batch_id={result['batch_id']}, "
            f"初始任务={len(result['initial_task_ids'])}, "
            f"待处理={result['pending_count']}, "
            f"总计={result['total_count']}, "
            f"批量并发={batch_concurrency}"
        )

        return result["batch_id"]

    async def _get_model_batch_concurrency(
        self,
        user_id: str,
        request: BatchTaskCreate,
    ) -> int:
        """
        获取模型配置中的批量并发数

        Args:
            user_id: 用户 ID
            request: 批量任务请求

        Returns:
            批量并发数
        """
        from core.ai.model.service import get_model_service

        model_service = get_model_service()

        # 优先使用任务参数指定的模型
        model_id = request.data_collection_model or request.debate_model

        if model_id:
            model = await model_service.get_model(model_id, user_id, is_admin=False)
            if model:
                return model.batch_concurrency

        # 使用用户默认模型
        default_model = await model_service.get_default_model(user_id=user_id)
        return default_model.batch_concurrency if default_model else 1

    async def get_task_status(self, task_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID
            user_id: 用户 ID（可选，用于数据隔离验证）

        Returns:
            任务状态字典

        Raises:
            TaskNotFoundException: 任务不存在
            PermissionError: 用户无权访问该任务
        """
        query = {"_id": ObjectId(task_id)}

        # 如果提供了 user_id，添加用户隔离验证
        if user_id is not None:
            query["user_id"] = user_id

        task_doc = await mongodb.database.analysis_tasks.find_one(query)

        if not task_doc:
            raise TaskNotFoundException(task_id)

        # 验证任务属于请求的用户（如果提供了 user_id）
        if user_id is not None and task_doc.get("user_id") != user_id:
            raise PermissionError("无权访问该任务")

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
        cursor = (
            mongodb.database.analysis_tasks.find(query)
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )

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
        ws_manager = await get_ws_manager()
        await ws_manager.broadcast_event(
            task_id,
            create_event(
                event_type=EventType.TASK_CANCELLED,
                task_id=task_id,
            )
        )

        # 使用延迟释放 MCP 连接（而非立即释放）
        # 原因：取消时智能体可能正在执行 LLM 调用或工具调用，
        # 立即释放连接可能导致其他任务复用连接时出现混乱
        # 使用失败级别的延迟（30秒），确保当前操作完成
        try:
            pool = get_mcp_connection_pool()
            await pool.mark_task_cancelled(task_id)
        except Exception as e:
            logger.warning(f"MCP 连接延迟释放设置失败: task_id={task_id}, error={e}")

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
        ws_manager = await get_ws_manager()
        await ws_manager.broadcast_event(
            task_id,
            create_event(
                event_type=EventType.TASK_STOPPED,
                task_id=task_id,
            )
        )

        # 使用延迟释放 MCP 连接（而非立即释放）
        # 原因同 cancel_task
        try:
            pool = get_mcp_connection_pool()
            await pool.mark_task_cancelled(task_id)
        except Exception as e:
            logger.warning(f"MCP 连接延迟释放设置失败: task_id={task_id}, error={e}")

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

        如果是批量任务的一部分，触发下一批任务创建。

        Args:
            task_id: 任务 ID
            final_recommendation: 最终推荐结果
            buy_price: 买入价格
            sell_price: 卖出价格
            token_usage: Token 使用量
        """
        # 获取任务信息（检查是否属于批量任务）
        task_doc = await mongodb.database.analysis_tasks.find_one(
            {"_id": ObjectId(task_id)}
        )
        batch_id = task_doc.get("batch_id") if task_doc else None
        user_id = task_doc.get("user_id") if task_doc else None

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
        ws_manager = await get_ws_manager()
        await ws_manager.broadcast_event(
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
            pool = get_mcp_connection_pool()
            await pool.mark_task_complete(task_id)
        except Exception as e:
            logger.warning(f"MCP 连接完成标记失败: task_id={task_id}, error={e}")

        # 如果是批量任务，触发下一批任务创建
        if batch_id:
            await self._trigger_next_batch(task_id, batch_id, user_id)

        logger.info(f"任务已完成: task_id={task_id}, recommendation={final_recommendation}")

    async def _trigger_next_batch(
        self,
        task_id: str,
        batch_id: str,
        user_id: str,
    ) -> None:
        """
        触发下一批任务创建

        Args:
            task_id: 已完成的任务 ID
            batch_id: 批量任务 ID
            user_id: 用户 ID
        """
        from modules.trading_agents.manager.batch_manager import get_batch_manager

        batch_manager = get_batch_manager()

        # 获取批量任务状态
        batch_status = await batch_manager.get_batch_status(batch_id)
        if not batch_status:
            logger.debug(f"批量任务不存在或已完成: batch_id={batch_id}")
            return

        # 通知批量任务管理器任务完成，触发下一批创建
        new_task_ids = await batch_manager.on_task_completed(
            task_id=task_id,
            batch_id=batch_id,
        )

        # 如果有新任务创建，启动它们
        if new_task_ids:
            logger.info(f"启动下一批任务: count={len(new_task_ids)}, batch_id={batch_id}")

            for new_task_id in new_task_ids:
                # 获取新创建的任务信息
                task_doc = await mongodb.database.analysis_tasks.find_one(
                    {"_id": ObjectId(new_task_id)}
                )
                if not task_doc:
                    logger.error(f"找不到新创建的任务: task_id={new_task_id}")
                    continue

                # 从数据库读取所有字段，确保数据一致性
                asyncio.create_task(
                    self.execute_analysis_workflow(
                        task_id=new_task_id,
                        user_id=user_id,
                        request=AnalysisTaskCreate(
                            stock_code=task_doc.get("stock_code", ""),
                            market=task_doc.get("market"),
                            trade_date=task_doc.get("trade_date"),
                            stages=AnalysisStagesConfig(**task_doc.get("stages", {})),
                            data_collection_model=task_doc.get("data_collection_model"),
                            debate_model=task_doc.get("debate_model"),
                        ),
                    )
                )

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
        ws_manager = await get_ws_manager()
        await ws_manager.broadcast_event(
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
            pool = get_mcp_connection_pool()
            await pool.mark_task_failed(task_id)
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

    async def create_task_background(
        self,
        user_id: str,
        request: AnalysisTaskCreate,
        config: Dict[str, Any]
    ) -> str:
        """
        后台任务：创建并执行分析任务

        此函数会在后台异步执行，避免阻塞 HTTP 响应。

        Args:
            user_id: 用户 ID
            request: 分析任务请求
            config: 智能体配置快照

        Returns:
            任务 ID
        """
        # 1. 创建任务记录
        task_id = await self.create_task(
            user_id=user_id,
            request=request,
            config=config
        )

        # 2. 标记任务为运行中
        await self.mark_task_running(task_id)

        # 3. 在后台异步执行工作流（不阻塞响应）
        # 注意：必须保存 Task 对象的引用，否则会被垃圾回收
        task = asyncio.create_task(
            self.execute_analysis_workflow(
                task_id=task_id,
                user_id=user_id,
                request=request
            ),
            name=f"workflow-{task_id}"
        )

        # 保存任务引用
        self._running_tasks[task_id] = task

        # 添加回调来追踪任务状态
        def task_callback(t):
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

        task.add_done_callback(task_callback)

        return task_id

    async def execute_analysis_workflow(
        self,
        task_id: str,
        user_id: str,
        request: AnalysisTaskCreate,
        _skip_model_loading: bool = False
    ) -> None:
        """
        执行分析工作流

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            request: 分析任务请求
            _skip_model_loading: 跳过模型加载（用于批量任务）
        """
        logger.info("="*60)
        logger.info(f"execute_analysis_workflow 开始: task_id={task_id}, user_id={user_id}")
        logger.info("="*60)

        # 用于并发控制
        batch_id = task_id
        data_collection_model_id = None
        debate_model_id = None

        try:
            # 1. 加载用户智能体配置
            logger.info(f"[{task_id}] 步骤1: 加载用户智能体配置...")
            from modules.trading_agents.services.agent_config_service import get_agent_config_service
            config_service = get_agent_config_service()
            agent_config = await config_service.get_user_config(user_id, create_if_missing=True)

            if not agent_config:
                raise Exception("无法加载用户智能体配置")

            # 将 Pydantic 对象转换为字典
            if hasattr(agent_config, 'model_dump'):
                agent_config = agent_config.model_dump(mode='json')
            elif hasattr(agent_config, 'dict'):
                agent_config = agent_config.dict()

            logger.info(f"[{task_id}] ✅ 用户智能体配置加载成功")

            # 2. 加载用户模型偏好
            logger.info(f"[{task_id}] 步骤2: 加载用户模型偏好...")
            from core.settings.services.user_service import get_user_settings_service
            settings_service = get_user_settings_service()
            user_settings = await settings_service.get_user_settings(user_id)
            logger.info(f"[{task_id}] ✅ 用户模型偏好加载成功")

            # 3. 确定使用的两个 AI 模型（带回退机制）
            if not _skip_model_loading:
                logger.info(f"[{task_id}] 步骤3: 解析AI模型...")
                from core.ai.model import get_model_service
                model_service = get_model_service()

                # 确定数据收集模型（带回退）
                logger.info(f"[{task_id}] 3.1 解析数据收集模型...")
                data_collection_model = await self._resolve_model_with_fallback(
                    model_service=model_service,
                    requested_model_id=request.data_collection_model,
                    user_settings=user_settings,
                    model_type="data_collection",
                    user_id=user_id
                )
                logger.info(f"[{task_id}] ✅ 数据收集模型解析成功")

                # 确定辩论模型（带回退）
                logger.info(f"[{task_id}] 3.2 解析辩论模型...")
                debate_model = await self._resolve_model_with_fallback(
                    model_service=model_service,
                    requested_model_id=request.debate_model,
                    user_settings=user_settings,
                    model_type="debate",
                    user_id=user_id
                )
                logger.info(f"[{task_id}] ✅ 辩论模型解析成功")

                data_collection_model_id = str(data_collection_model.id)
                debate_model_id = str(debate_model.id)

                logger.info(f"任务 {task_id} 模型解析完成: data_collection={data_collection_model_id}, debate={debate_model_id}")

            # 请求并发控制
            from modules.trading_agents.manager.concurrency_controller import get_concurrency_controller
            concurrency_controller = get_concurrency_controller()

            # 为数据收集模型请求并发
            if data_collection_model_id:
                from core.ai.model import get_model_service
                model_service = get_model_service()
                data_collection_model_obj = await model_service.get_model(data_collection_model_id, user_id)
                data_collection_config = {
                    "max_concurrency": data_collection_model_obj.max_concurrency,
                    "task_concurrency": data_collection_model_obj.task_concurrency,
                    "batch_concurrency": data_collection_model_obj.batch_concurrency,
                }
            else:
                data_collection_config = {}

            # 为辩论模型请求并发
            if debate_model_id:
                debate_model_obj = await model_service.get_model(debate_model_id, user_id)
                debate_config = {
                    "max_concurrency": debate_model_obj.max_concurrency,
                    "task_concurrency": debate_model_obj.task_concurrency,
                    "batch_concurrency": debate_model_obj.batch_concurrency,
                }
            else:
                debate_config = {}

            if data_collection_model_id and debate_model_id:
                logger.info(f"任务 {task_id} 请求并发控制槽位...")

                try:
                    # 等待数据收集模型槽位（超时 5 分钟）
                    logger.info(f"任务 {task_id} 等待数据收集模型槽位...")
                    await concurrency_controller.wait_for_execution(
                        model_id=data_collection_model_id,
                        task_id=task_id,
                        user_id=user_id,
                        model_config=data_collection_config,
                        timeout=300.0,
                    )
                    logger.info(f"任务 {task_id} 获取到数据收集模型槽位")

                    # 等待辩论模型槽位（超时 5 分钟）
                    logger.info(f"任务 {task_id} 等待辩论模型槽位...")
                    await concurrency_controller.wait_for_execution(
                        model_id=debate_model_id,
                        task_id=task_id,
                        user_id=user_id,
                        model_config=debate_config,
                        timeout=300.0,
                    )
                    logger.info(f"任务 {task_id} 获取到辩论模型槽位")

                except asyncio.TimeoutError as e:
                    logger.error(f"任务 {task_id} 等待并发槽位超时: {e}")
                    raise Exception(f"任务等待执行超时，请稍后重试") from e
                except Exception as e:
                    logger.error(f"任务 {task_id} 等待并发槽位时发生异常: {e}", exc_info=True)
                    raise Exception(f"任务等待并发槽位失败: {e}") from e

            # 5. 使用新调度器执行工作流
            logger.info(f"任务 {task_id} 开始执行工作流...")

            try:
                # 使用新的 WorkflowScheduler 执行工作流
                from modules.trading_agents.scheduler.workflow_scheduler import (
                    WorkflowScheduler,
                    create_workflow_scheduler,
                )
                from core.ai.service import AIService

                # 获取 AI 服务
                ai_service = AIService()

                # 获取 WebSocket 管理器用于进度推送
                ws_manager = await get_ws_manager()

                # 进度回调函数
                async def progress_callback(progress_data: Dict[str, Any]):
                    await ws_manager.broadcast_event(task_id, create_event(
                        event_type=EventType.TASK_STARTED,
                        task_id=task_id,
                        stock_code=request.stock_code,
                    ))

                # 创建调度器
                scheduler = create_workflow_scheduler(ai_service) \
                    .with_agent_config(agent_config) \
                    .with_progress_callback(progress_callback) \
                    .build()

                # 获取阶段配置
                stages_config = request.stages.model_dump() if request.stages else {}
                selected_agents = stages_config.get("stage1", {}).get("selected_agents")

                # 执行工作流
                final_state = await scheduler.run(
                    task_id=task_id,
                    user_id=user_id,
                    stock_code=request.stock_code,
                    stock_name=None,  # 可以后续从市场数据获取
                    market=request.market,
                    trade_date=request.trade_date,
                    selected_agents=selected_agents,
                    data_collection_model=data_collection_model_id or "claude-sonnet-4-20250514",
                    debate_model=debate_model_id or "claude-haiku-4-20250514",
                    stages=stages_config,
                )

                logger.info(f"任务 {task_id} 工作流执行完成，状态: {final_state.status}")

                # 保存最终结果到数据库
                await self.complete_task(
                    task_id=task_id,
                    final_recommendation=self._convert_recommendation(final_state.final_recommendation),
                    buy_price=final_state.buy_price,
                    sell_price=final_state.sell_price,
                    token_usage=final_state.token_usage.model_dump() if final_state.token_usage else {},
                )

                # 保存最终报告
                if final_state.final_report:
                    await self.add_task_report(task_id, "final_report", final_state.final_report)

            except Exception as e:
                logger.error(f"任务 {task_id} 工作流执行失败: {e}", exc_info=True)
                raise

            logger.info(f"分析任务执行成功: task_id={task_id}")

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"分析任务执行失败: task_id={task_id}, error={e}\n{error_trace}")

            # 标记任务失败
            await self.fail_task(
                task_id=task_id,
                error_message=str(e),
                error_details={"type": type(e).__name__, "traceback": error_trace}
            )

        finally:
            # 释放并发资源（两个模型都需要释放）
            if data_collection_model_id or debate_model_id:
                try:
                    from modules.trading_agents.manager.concurrency_controller import get_concurrency_controller
                    concurrency_controller = get_concurrency_controller()

                    # 释放数据收集模型槽位
                    if data_collection_model_id:
                        try:
                            await concurrency_controller.release_execution(
                                model_id=data_collection_model_id,
                                task_id=task_id,
                                user_id=user_id,
                                batch_id=batch_id,
                            )
                            logger.info(
                                f"已释放任务 {task_id} 的数据收集模型并发槽位: "
                                f"model_id={data_collection_model_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"释放数据收集模型并发槽位失败: task_id={task_id}, error={e}"
                            )

                    # 释放辩论模型槽位
                    if debate_model_id:
                        try:
                            await concurrency_controller.release_execution(
                                model_id=debate_model_id,
                                task_id=task_id,
                                user_id=user_id,
                                batch_id=batch_id,
                            )
                            logger.info(
                                f"已释放任务 {task_id} 的辩论模型并发槽位: "
                                f"model_id={debate_model_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"释放辩论模型并发槽位失败: task_id={task_id}, error={e}"
                            )
                except Exception as e:
                    logger.error(f"释放并发资源时发生错误: task_id={task_id}, error={e}")

            # 减少用户的并发任务计数
            try:
                from core.settings.services.user_service import get_user_settings_service
                settings_service = get_user_settings_service()
                await settings_service.decrement_concurrent_tasks(user_id)
                logger.info(f"已减少用户 {user_id} 的并发任务计数")
            except Exception as e:
                logger.error(f"减少并发任务计数失败: task_id={task_id}, user_id={user_id}, error={e}")

            # 释放 MCP 连接
            try:
                pool = get_mcp_connection_pool()
                await pool.release_task_connections(task_id)
                logger.info(f"已释放任务 {task_id} 的 MCP 连接")
            except Exception as e:
                logger.error(f"释放 MCP 连接失败: task_id={task_id}, error={e}")

    async def _resolve_model_with_fallback(
        self,
        model_service,
        requested_model_id: Optional[str],
        user_settings,
        model_type: str,
        user_id: str
    ):
        """
        解析模型（带回退机制）

        回退顺序：
        1. 任务参数指定的模型
        2. 用户默认模型
        3. 系统默认模型
        """
        model = None
        source = None
        user_model_id = None

        # 优先级1：任务参数指定
        if requested_model_id:
            model = await model_service.get_model(requested_model_id, user_id, is_admin=False)
            if model:
                source = f"任务参数指定({model.name})"
                logger.info(f"使用{model_type}模型: {source}")
                return model
            else:
                logger.warning(f"任务参数指定的{model_type}模型不可用: {requested_model_id}")

        # 优先级2：用户默认模型
        if user_settings and user_settings.trading_agents_settings:
            user_model_id = getattr(
                user_settings.trading_agents_settings,
                f"{model_type}_model_id",
                None
            )
            if user_model_id:
                model = await model_service.get_model(user_model_id, user_id, is_admin=False)
                if model:
                    source = f"用户默认模型({model.name})"
                    logger.info(f"使用{model_type}模型: {source}")
                    return model
                else:
                    logger.warning(f"用户默认的{model_type}模型不可用: {user_model_id}")

        # 优先级3：系统默认模型
        model = await model_service.get_default_model(user_id=user_id)
        if model:
            source = f"系统默认模型({model.name})"
            logger.info(f"使用{model_type}模型: {source}")
            return model

        # 全部不可用
        raise Exception(
            f"无可用的{model_type}模型。"
            f"任务参数指定: {requested_model_id}, "
            f"用户默认: {user_model_id if user_settings else 'None'}, "
            f"系统默认: 不可用"
        )

    def _convert_recommendation(self, recommendation: Optional[str]) -> Optional[RecommendationEnum]:
        """
        转换推荐结果字符串为枚举

        Args:
            recommendation: 推荐结果字符串

        Returns:
            RecommendationEnum 或 None
        """
        if not recommendation:
            return None

        # 映射常见的推荐结果格式
        mapping = {
            # 中文格式
            "强烈买入": RecommendationEnum.BUY,
            "买入": RecommendationEnum.BUY,
            "持有": RecommendationEnum.HOLD,
            "卖出": RecommendationEnum.SELL,
            "强烈卖出": RecommendationEnum.SELL,
            # 英文格式
            "STRONG_BUY": RecommendationEnum.BUY,
            "BUY": RecommendationEnum.BUY,
            "HOLD": RecommendationEnum.HOLD,
            "SELL": RecommendationEnum.SELL,
            "STRONG_SELL": RecommendationEnum.SELL,
        }

        return mapping.get(recommendation.upper(), RecommendationEnum.HOLD)


# =============================================================================
# 全局任务管理器实例
# =============================================================================

task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    return task_manager
