"""
TradingAgents 工作流调度器

使用 asyncio 调度四个阶段，不使用 LangGraph。

调度流程:
Phase 1 (并发) → Phase 2 (串行) → Phase 3 (串行) → Phase 4 (串行)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from .state import (
    WorkflowState,
    create_initial_state,
    TaskStatus,
)


logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """
    工作流调度器

    按顺序调度四个阶段，不使用 LangGraph。
    """

    def __init__(
        self,
        phase1_runner: Optional[Callable] = None,
        phase2_runner: Optional[Callable] = None,
        phase3_runner: Optional[Callable] = None,
        phase4_runner: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
    ):
        """
        初始化调度器

        Args:
            phase1_runner: Phase 1 运行器（并发执行分析师）
            phase2_runner: Phase 2 运行器（研究与辩论）
            phase3_runner: Phase 3 运行器（风险评估）
            phase4_runner: Phase 4 运行器（总结报告）
            progress_callback: 进度回调函数
        """
        self.phase1_runner = phase1_runner
        self.phase2_runner = phase2_runner
        self.phase3_runner = phase3_runner
        self.phase4_runner = phase4_runner
        self.progress_callback = progress_callback

        # 运行中的任务（用于取消）
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def run(
        self,
        task_id: str,
        user_id: str,
        stock_code: str,
        trade_date: str,
        model_config: Dict[str, Any],
        agent_config: Dict[str, Any],
        max_debate_rounds: int = 2,
        enable_phase1: bool = True,
        enable_phase2: bool = True,
        enable_phase3: bool = True,
        enable_phase4: bool = True,
    ) -> WorkflowState:
        """
        运行完整工作流

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            stock_code: 股票代码
            trade_date: 交易日期
            model_config: 模型配置
            agent_config: 智能体配置
            max_debate_rounds: 最大辩论轮次
            enable_phase1: 启用第一阶段
            enable_phase2: 启用第二阶段
            enable_phase3: 启用第三阶段
            enable_phase4: 启用第四阶段

        Returns:
            最终状态
        """
        # 创建初始状态
        state = create_initial_state(
            task_id=task_id,
            user_id=user_id,
            stock_code=stock_code,
            trade_date=trade_date,
            model_config=model_config,
            agent_config=agent_config,
            max_debate_rounds=max_debate_rounds,
            enable_phase1=enable_phase1,
            enable_phase2=enable_phase2,
            enable_phase3=enable_phase3,
            enable_phase4=enable_phase4,
        )

        logger.info(f"[调度器] 开始任务: {task_id}, {stock_code}")
        self._notify_progress(state, "start", "任务开始")

        try:
            # Phase 1: 分析师团队（并发）
            if enable_phase1 and self.phase1_runner:
                state.current_phase = "phase1"
                state.status = TaskStatus.PHASE1.value
                self._notify_progress(state, "phase1_start", "开始 Phase 1: 分析师团队")

                state = await self.phase1_runner(state)
                logger.info(f"[调度器] Phase 1 完成: {len(state.analyst_reports)} 份报告")
                self._notify_progress(state, "phase1_complete", "Phase 1 完成")

            # Phase 2: 研究与辩论（串行）
            if enable_phase2 and self.phase2_runner:
                state.current_phase = "phase2"
                state.status = TaskStatus.PHASE2.value
                self._notify_progress(state, "phase2_start", "开始 Phase 2: 研究与辩论")

                state = await self.phase2_runner(state)
                logger.info(f"[调度器] Phase 2 完成: {len(state.debate_turns)} 轮辩论")
                self._notify_progress(state, "phase2_complete", "Phase 2 完成")

            # Phase 3: 风险评估（串行）
            if enable_phase3 and self.phase3_runner:
                state.current_phase = "phase3"
                state.status = TaskStatus.PHASE3.value
                self._notify_progress(state, "phase3_start", "开始 Phase 3: 风险评估")

                state = await self.phase3_runner(state)
                logger.info(f"[调度器] Phase 3 完成: {len(state.risk_assessments)} 份评估")
                self._notify_progress(state, "phase3_complete", "Phase 3 完成")

            # Phase 4: 总结报告（串行）
            if enable_phase4 and self.phase4_runner:
                state.current_phase = "phase4"
                state.status = TaskStatus.PHASE4.value
                self._notify_progress(state, "phase4_start", "开始 Phase 4: 总结报告")

                state = await self.phase4_runner(state)
                logger.info(f"[调度器] Phase 4 完成: {state.recommendation}")
                self._notify_progress(state, "phase4_complete", "Phase 4 完成")

            # 任务完成
            state.status = TaskStatus.COMPLETED.value
            state.current_phase = "completed"
            state.end_time = datetime.now().isoformat()
            self._notify_progress(state, "complete", "任务完成")

            logger.info(f"[调度器] 任务完成: {task_id}")
            return state

        except asyncio.CancelledError:
            logger.warning(f"[调度器] 任务被取消: {task_id}")
            state.status = TaskStatus.CANCELLED.value
            state.current_phase = "cancelled"
            state.end_time = datetime.now().isoformat()
            self._notify_progress(state, "cancelled", "任务已取消")
            raise

        except Exception as e:
            logger.error(f"[调度器] 任务失败: {task_id}, 错误: {e}")
            state.status = TaskStatus.FAILED.value
            state.current_phase = "failed"
            state.end_time = datetime.now().isoformat()
            state.add_error(state.current_phase, str(e))
            self._notify_progress(state, "error", f"任务失败: {str(e)}")
            raise

    async def run_in_background(
        self,
        task_id: str,
        user_id: str,
        stock_code: str,
        trade_date: str,
        model_config: Dict[str, Any],
        agent_config: Dict[str, Any],
        max_debate_rounds: int = 2,
        enable_phase1: bool = True,
        enable_phase2: bool = True,
        enable_phase3: bool = True,
        enable_phase4: bool = True,
    ) -> asyncio.Task:
        """
        在后台运行任务

        Args:
            (同 run 方法)

        Returns:
            asyncio.Task 对象
        """
        task = asyncio.create_task(
            self.run(
                task_id=task_id,
                user_id=user_id,
                stock_code=stock_code,
                trade_date=trade_date,
                model_config=model_config,
                agent_config=agent_config,
                max_debate_rounds=max_debate_rounds,
                enable_phase1=enable_phase1,
                enable_phase2=enable_phase2,
                enable_phase3=enable_phase3,
                enable_phase4=enable_phase4,
            )
        )

        # 保存任务引用（用于取消）
        self._running_tasks[task_id] = task

        # 任务完成后清理
        def cleanup(task_id: str):
            self._running_tasks.pop(task_id, None)

        task.add_done_callback(lambda t: cleanup(task_id))

        return task

    async def cancel(self, task_id: str) -> bool:
        """
        取消正在运行的任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        task = self._running_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"[调度器] 取消任务: {task_id}")
            return True
        return False

    def get_task_status(self, task_id: str) -> Optional[str]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态或 None
        """
        task = self._running_tasks.get(task_id)
        if task:
            if task.done():
                if task.cancelled():
                    return TaskStatus.CANCELLED.value
                elif task.exception():
                    return TaskStatus.FAILED.value
                else:
                    return TaskStatus.COMPLETED.value
            else:
                return TaskStatus.RUNNING.value
        return None

    def _notify_progress(self, state: WorkflowState, event: str, message: str) -> None:
        """
        通知进度

        Args:
            state: 当前状态
            event: 事件类型
            message: 消息
        """
        if self.progress_callback:
            try:
                progress_data = {
                    "task_id": state.task_id,
                    "event": event,
                    "message": message,
                    "current_phase": state.current_phase,
                    "status": state.status,
                    "stock_code": state.stock_code,
                    "timestamp": datetime.now().isoformat(),
                }
                asyncio.create_task(self._safe_notify(progress_data))
            except Exception as e:
                logger.warning(f"[调度器] 通知进度失败: {e}")

    async def _safe_notify(self, progress_data: Dict[str, Any]) -> None:
        """安全地通知进度（捕获异常）"""
        try:
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(progress_data)
            else:
                self.progress_callback(progress_data)
        except Exception as e:
            logger.warning(f"[调度器] 进度回调异常: {e}")


class WorkflowSchedulerBuilder:
    """
    工作流调度器构建器

    用于构建配置好的调度器实例。
    """

    def __init__(self):
        self.phase1_runner = None
        self.phase2_runner = None
        self.phase3_runner = None
        self.phase4_runner = None
        self.progress_callback = None

    def with_phase1_runner(self, runner: Callable) -> "WorkflowSchedulerBuilder":
        """设置 Phase 1 运行器"""
        self.phase1_runner = runner
        return self

    def with_phase2_runner(self, runner: Callable) -> "WorkflowSchedulerBuilder":
        """设置 Phase 2 运行器"""
        self.phase2_runner = runner
        return self

    def with_phase3_runner(self, runner: Callable) -> "WorkflowSchedulerBuilder":
        """设置 Phase 3 运行器"""
        self.phase3_runner = runner
        return self

    def with_phase4_runner(self, runner: Callable) -> "WorkflowSchedulerBuilder":
        """设置 Phase 4 运行器"""
        self.phase4_runner = runner
        return self

    def with_progress_callback(self, callback: Callable) -> "WorkflowSchedulerBuilder":
        """设置进度回调"""
        self.progress_callback = callback
        return self

    def build(self) -> WorkflowScheduler:
        """构建调度器"""
        return WorkflowScheduler(
            phase1_runner=self.phase1_runner,
            phase2_runner=self.phase2_runner,
            phase3_runner=self.phase3_runner,
            phase4_runner=self.phase4_runner,
            progress_callback=self.progress_callback,
        )


def create_workflow_scheduler() -> WorkflowSchedulerBuilder:
    """
    创建工作流调度器构建器

    Returns:
        WorkflowSchedulerBuilder 实例
    """
    return WorkflowSchedulerBuilder()
