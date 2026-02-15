"""
TradingAgents 工作流调度器

**版本**: v4.0 (重构版)
**最后更新**: 2026-01-16

使用函数式调用 + LangChain create_agent 实现四阶段工作流。

调度流程（并发设计）:
- Phase 1 (所有分析师并发, 受 task_concurrency 控制)
- Phase 2 (看涨+看跌并发, 投资组合经理+交易员串行)
- Phase 3 (策略分析师并发, 风险管理委员会主席串行)
- Phase 4 (总结智能体串行, 必须执行)

阶段说明:
- Phase 1: 信息收集与基础分析（必需，最少1-2个分析师）
- Phase 2: 多空博弈与投资决策（看涨+看跌+投资组合经理+交易员）
- Phase 3: 策略风格与风险评估（激进+中性+保守+风险管理委员会主席）
- Phase 4: 总结智能体（必须执行，提供最终投资建议和价格预测）
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from modules.trading_agents.models.state import (
    WorkflowState,
    create_initial_state,
    TaskStatus,
)
from modules.trading_agents.workflow import phase1, phase2, phase3, phase4
from core.ai.service import AIService

logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """
    工作流调度器

    按顺序调度四个阶段，使用函数式调用而非 LangGraph。
    """

    def __init__(
        self,
        ai_service: AIService,
        agent_config: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ):
        """
        初始化调度器

        Args:
            ai_service: AI 服务
            agent_config: 智能体配置
            progress_callback: 进度回调函数（WebSocket 推送）
        """
        self.ai_service = ai_service
        self.agent_config = agent_config
        self.progress_callback = progress_callback

        # 运行中的任务（用于取消）
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def run(
        self,
        task_id: str,
        user_id: str,
        stock_code: str,
        stock_name: Optional[str],
        market: str = "A_STOCK",
        trade_date: Optional[str] = None,
        selected_agents: Optional[list[str]] = None,
        data_collection_model: str = "claude-sonnet-4-20250514",
        debate_model: str = "claude-haiku-4-20250514",
        stages: Optional[Dict[str, Any]] = None,
        data_collection_task_concurrency: Optional[int] = None,
    ) -> WorkflowState:
        """
        运行完整工作流

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            stock_code: 股票代码
            stock_name: 股票名称
            market: 市场类型
            trade_date: 交易日期
            selected_agents: 用户选择的 Phase 1 智能体 slug 列表
            data_collection_model: 数据收集模型 ID
            debate_model: 辩论模型 ID
            stages: 阶段配置
            data_collection_task_concurrency: Phase 1 最大并发数（从模型配置获取）

        Returns:
            最终状态
        """
        # 创建初始状态
        state = create_initial_state(
            task_id=task_id,
            user_id=user_id,
            stock_code=stock_code,
            trade_date=trade_date or datetime.utcnow().strftime("%Y-%m-%d"),
            market=market
        )
        state.stock_name = stock_name

        logger.info(f"[调度器] 开始任务: {task_id}, {stock_code}")
        self._notify_progress(state, "task_created", "任务创建")

        try:
            # 获取阶段配置
            if stages is None:
                stages = {}
            phase1_config = stages.get("stage1") or stages.get("phase1") or {}
            phase2_config = stages.get("stage2") or stages.get("phase2") or {}
            phase3_config = stages.get("stage3") or stages.get("phase3") or {}
            phase4_config = stages.get("stage4") or stages.get("phase4") or {}

            # 获取模型
            data_collection_model_instance = await self.ai_service.get_model_async(data_collection_model or "claude-sonnet-4-20250514", user_id)
            
            # 确保 debate_model 有效
            if not debate_model:
                # 如果没有指定，尝试使用 data_collection_model 或默认模型
                debate_model = data_collection_model or "claude-haiku-4-20250514"
            
            debate_model_instance = await self.ai_service.get_model_async(debate_model, user_id)
            
            # 检查模型实例是否有有效的 API Key (如果 API Key 为空，get_model_async 会返回空配置的实例)
            # 这里我们通过检查私有属性 _api_key 来验证 (LangChain Adapter 实现)
            # 或者尝试获取默认模型作为兜底
            if not getattr(debate_model_instance, "api_key", None) and not getattr(debate_model_instance, "openai_api_key", None):
                 logger.warning(f"[调度器] Debate model {debate_model} API Key 为空，尝试使用 Data Collection model")
                 debate_model_instance = data_collection_model_instance

            # Phase 1: 信息收集与基础分析（所有分析师并发，受 task_concurrency 控制）
            if phase1_config.get("enabled", True):
                self._notify_progress(state, "phase1_start", "开始 Phase 1: 信息收集与基础分析")

                state = await phase1.execute_phase1(
                    state,
                    self.ai_service,
                    self.agent_config,
                    selected_agents=selected_agents,
                    model_id=data_collection_model,
                    max_concurrency=data_collection_task_concurrency
                )

                logger.info(f"[调度器] Phase 1 完成: {len(state.analyst_reports)} 份报告")
                self._notify_progress(state, "phase1_complete", "Phase 1 完成")

            # Phase 2: 多空博弈与投资决策（看涨+看跌并发，投资组合经理+交易员串行）
            if phase2_config.get("enabled", True) and should_continue(state):
                self._notify_progress(state, "phase2_start", "开始 Phase 2: 多空博弈与投资决策")

                debate_rounds = phase2_config.get("debate", {}).get("rounds", 2)

                state = await phase2.execute_phase2(
                    state,
                    debate_model_instance,
                    self.agent_config,
                    debate_rounds=debate_rounds
                )

                logger.info(f"[调度器] Phase 2 完成: {len(state.debate_turns)} 轮辩论")
                self._notify_progress(state, "phase2_complete", "Phase 2 完成")

            # Phase 3: 策略风格与风险评估（策略分析师并发，风险管理委员会主席串行）
            if phase3_config.get("enabled", True) and should_continue(state):
                self._notify_progress(state, "phase3_start", "开始 Phase 3: 策略风格与风险评估")

                state = await phase3.execute_phase3(
                    state,
                    debate_model_instance,
                    self.agent_config
                )

                logger.info(f"[调度器] Phase 3 完成, 推荐: {state.final_recommendation}")
                self._notify_progress(state, "phase3_complete", "Phase 3 完成")

            # Phase 4: 总结智能体（必须执行，提供最终投资建议和价格预测）
            if should_continue(state):
                self._notify_progress(state, "phase4_start", "开始 Phase 4: 总结智能体")

                state = await phase4.execute_phase4(
                    state,
                    debate_model_instance,
                    self.agent_config
                )

                logger.info(f"[调度器] Phase 4 完成, 推荐: {state.final_recommendation}")
                self._notify_progress(state, "phase4_complete", "Phase 4 完成")

            # 生成最终报告
            state.final_report = self._generate_final_report(state)

            # 任务完成
            state.status = TaskStatus.COMPLETED
            state.current_phase = 0
            state.completed_at = datetime.utcnow()
            state.progress = 100.0

            self._notify_progress(state, "task_completed", "任务完成")

            logger.info(f"[调度器] 任务完成: {task_id}")
            return state

        except asyncio.CancelledError:
            logger.warning(f"[调度器] 任务被取消: {task_id}")
            state.status = TaskStatus.CANCELLED
            state.current_phase = 0
            state.completed_at = datetime.utcnow()
            self._notify_progress(state, "task_cancelled", "任务已取消")
            raise

        except Exception as e:
            logger.error(f"[调度器] 任务失败: {task_id}, 错误: {e}")
            state.status = TaskStatus.FAILED
            state.current_phase = 0
            state.completed_at = datetime.utcnow()
            state.error_message = str(e)
            self._notify_progress(state, "task_failed", f"任务失败: {str(e)}")
            raise

    async def run_in_background(
        self,
        task_id: str,
        user_id: str,
        stock_code: str,
        stock_name: Optional[str],
        market: str = "A_STOCK",
        trade_date: Optional[str] = None,
        selected_agents: Optional[list[str]] = None,
        data_collection_model: str = "claude-sonnet-4-20250514",
        debate_model: str = "claude-haiku-4-20250514",
        stages: Optional[Dict[str, Any]] = None,
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
                stock_name=stock_name,
                market=market,
                trade_date=trade_date,
                selected_agents=selected_agents,
                data_collection_model=data_collection_model,
                debate_model=debate_model,
                stages=stages,
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
                    return TaskStatus.CANCELLED
                elif task.exception():
                    return TaskStatus.FAILED
                else:
                    return TaskStatus.COMPLETED
            else:
                return TaskStatus.RUNNING
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
                    "user_id": state.user_id,
                    "event": event,
                    "message": message,
                    "current_phase": state.current_phase,
                    "status": state.status,
                    "progress": state.progress,
                    "stock_code": state.stock_code,
                    "stock_name": state.stock_name,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # 在 Phase 完成时添加报告数据，用于数据库保存
                if event == "phase1_complete" and hasattr(state, 'analyst_reports'):
                    progress_data["analyst_reports"] = state.analyst_reports
                elif event == "phase2_complete":
                    # Phase 2 完成时保存辩论相关数据
                    if hasattr(state, 'debate_turns'):
                        progress_data["debate_turns"] = state.debate_turns
                    if hasattr(state, 'investment_decision'):
                        progress_data["investment_decision"] = state.investment_decision
                    if hasattr(state, 'trading_plan'):
                        progress_data["trading_plan"] = state.trading_plan
                elif event == "phase3_complete":
                    # Phase 3 完成时保存策略报告
                    if hasattr(state, 'strategy_reports'):
                        progress_data["strategy_reports"] = state.strategy_reports
                    if hasattr(state, 'risk_approval'):
                        progress_data["risk_approval"] = state.risk_approval
                elif event == "phase4_complete":
                    # Phase 4 完成时保存最终数据
                    if hasattr(state, 'summary_report'):
                        progress_data["summary_report"] = state.summary_report
                    if hasattr(state, 'final_recommendation'):
                        progress_data["final_recommendation"] = state.final_recommendation
                    if hasattr(state, 'risk_level'):
                        progress_data["risk_level"] = state.risk_level
                    if hasattr(state, 'buy_price'):
                        progress_data["buy_price"] = state.buy_price
                    if hasattr(state, 'sell_price'):
                        progress_data["sell_price"] = state.sell_price

                # 任务完成时保存最终报告（实时推送到前端）
                if event == "task_completed":
                    if hasattr(state, 'final_report'):
                        progress_data["final_report"] = state.final_report
                    if hasattr(state, 'final_recommendation'):
                        progress_data["final_recommendation"] = state.final_recommendation
                    if hasattr(state, 'risk_level'):
                        progress_data["risk_level"] = state.risk_level
                    if hasattr(state, 'buy_price'):
                        progress_data["buy_price"] = state.buy_price
                    if hasattr(state, 'sell_price'):
                        progress_data["sell_price"] = state.sell_price

                # 在每个阶段完成时保存工具调用记录
                if event.endswith("_complete"):
                    if hasattr(state, 'tool_calls'):
                        progress_data["tool_calls"] = state.tool_calls
                    
                    if hasattr(state, 'phase_executions'):
                        # Convert dataclasses to dicts
                        progress_data["phase_executions"] = [
                            {
                                "phase": p.phase,
                                "phase_name": p.phase_name,
                                "started_at": p.started_at,
                                "completed_at": p.completed_at,
                                "execution_mode": p.execution_mode,
                                "max_concurrency": p.max_concurrency,
                                "status": p.status,
                                "agents": [
                                    {
                                        "slug": a.slug,
                                        "name": a.name,
                                        "started_at": a.started_at,
                                        "completed_at": a.completed_at,
                                        "status": a.status,
                                        "error_message": a.error_message,
                                        "output": a.output
                                    } for a in p.agents
                                ]
                            } for p in state.phase_executions
                        ]

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

    def _generate_final_report(self, state: WorkflowState) -> str:
        """
        生成最终报告

        Args:
            state: 工作流状态

        Returns:
            最终报告 (Markdown 格式)
        """
        report = f"""# {state.stock_name or state.stock_code} 投资分析报告

**生成时间**: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
**股票代码**: {state.stock_code}
**市场**: {state.market}

---

## 投资建议

**推荐等级**: {state.final_recommendation or "待定"}
**风险等级**: {state.risk_level or "待定"}
**目标价位**: 买入 ¥{state.buy_price or "-"}, 卖出 ¥{state.sell_price or "-"}

---

## Phase 1: 分析师团队报告

"""

        # 添加分析师报告摘要
        for i, analyst_report in enumerate(state.analyst_reports, 1):
            report += f"\n### {i}. {analyst_report['name']}\n\n"
            report += f"{analyst_report['content'][:500]}...\n\n"

        # 添加辩论记录
        if state.debate_turns:
            report += "\n---\n\n## Phase 2: 多空辩论记录\n\n"
            for turn in state.debate_turns:
                report += f"\n### 第 {turn['round']} 轮辩论\n\n"
                bull_view = turn.get('bull_view')
                bear_view = turn.get('bear_view')
                if bull_view:
                    report += f"**看涨观点**:\n\n{bull_view[:300]}...\n\n"
                if bear_view:
                    report += f"**看跌观点**:\n\n{bear_view[:300]}...\n\n"

        # 添加交易计划
        if state.trading_plan:
            report += "\n---\n\n## Phase 2: 交易执行计划\n\n"
            report += f"{state.trading_plan.get('content', '')[:500]}...\n\n"

        # 添加策略报告
        if state.strategy_reports:
            report += "\n---\n\n## Phase 3: 策略风格分析\n\n"
            for strategy_report in state.strategy_reports:
                report += f"\n### {strategy_report['name']}\n\n"
                report += f"{strategy_report['content'][:300]}...\n\n"

        # 添加总结报告
        if state.summary_report:
            report += "\n---\n\n## Phase 4: 总结报告\n\n"
            report += f"{state.summary_report.get('content', '')}\n\n"

        # 添加风险提示
        report += "\n---\n\n## 风险提示\n\n"
        report += "本报告基于 AI 分析生成，仅供参考，不构成投资建议。"
        report += "投资有风险，入市需谨慎。\n"

        return report


def should_continue(state: WorkflowState) -> bool:
    """
    判断工作流是否应该继续

    Args:
        state: 当前工作流状态

    Returns:
        是否继续
    """
    return state.status not in [
        TaskStatus.CANCELLED,
        TaskStatus.STOPPED,
        TaskStatus.FAILED,
        TaskStatus.EXPIRED
    ]


class WorkflowSchedulerBuilder:
    """
    工作流调度器构建器

    用于构建配置好的调度器实例。
    """

    def __init__(
        self,
        ai_service: Optional[AIService] = None
    ):
        """
        初始化构建器

        Args:
            ai_service: AI 服务
        """
        self.ai_service = ai_service
        self.agent_config = {}
        self.progress_callback = None

    def with_ai_service(self, ai_service: AIService) -> "WorkflowSchedulerBuilder":
        """设置 AI 服务"""
        self.ai_service = ai_service
        return self

    def with_agent_config(self, config: Dict[str, Any]) -> "WorkflowSchedulerBuilder":
        """设置智能体配置"""
        self.agent_config = config
        return self

    def with_progress_callback(self, callback: Callable) -> "WorkflowSchedulerBuilder":
        """设置进度回调"""
        self.progress_callback = callback
        return self

    def build(self) -> WorkflowScheduler:
        """构建调度器"""
        return WorkflowScheduler(
            ai_service=self.ai_service,
            agent_config=self.agent_config,
            progress_callback=self.progress_callback,
        )


def create_workflow_scheduler(
    ai_service: AIService
) -> WorkflowSchedulerBuilder:
    """
    创建工作流调度器构建器

    Args:
        ai_service: AI 服务

    Returns:
        WorkflowSchedulerBuilder 实例
    """
    return WorkflowSchedulerBuilder(ai_service)
