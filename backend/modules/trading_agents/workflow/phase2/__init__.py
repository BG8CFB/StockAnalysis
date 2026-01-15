"""
Phase 2: 多空博弈与投资决策

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15

多空辩论，三个固定智能体。
"""

from .bull_researcher import BullResearcher
from .bear_researcher import BearResearcher
from .research_manager import ResearchManager

__all__ = [
    "BullResearcher",
    "BearResearcher",
    "ResearchManager",
    "execute_phase2",
]

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from modules.trading_agents.models.state import (
    WorkflowState,
    AgentExecution,
    PhaseExecution,
    TaskStatus,
)
from modules.trading_agents.config import get_enabled_agents

logger = logging.getLogger(__name__)


async def execute_phase2(
    state: WorkflowState,
    model: BaseChatModel,
    config: Dict[str, Any],
    debate_rounds: int = 2
) -> WorkflowState:
    """
    执行 Phase 2: 多空博弈与投资决策

    Args:
        state: 工作流状态
        model: LLM 模型
        config: 智能体配置
        debate_rounds: 辩论轮数

    Returns:
        更新后的工作流状态
    """
    logger.info(f"[Phase 2] 开始执行, 任务ID: {state.task_id}")

    # 更新状态
    state.current_phase = 2
    state.status = TaskStatus.RUNNING

    # 检查阶段是否启用
    phase2_config = config.get("phase2", {})
    if not phase2_config.get("enabled", True):
        logger.warning("[Phase 2] 阶段未启用，跳过")
        state.progress = 50.0  # Phase 2 完成后进度 50%
        return state

    # 获取智能体配置
    agents_config = get_enabled_agents(config, "phase2")

    # 创建智能体实例
    agents = {}
    for agent_config in agents_config:
        slug = agent_config["slug"]
        if slug == "bull-researcher":
            agents["bull"] = BullResearcher(model, agent_config)
        elif slug == "bear-researcher":
            agents["bear"] = BearResearcher(model, agent_config)
        elif slug == "research-manager":
            agents["manager"] = ResearchManager(model, agent_config)

    if "bull" not in agents or "bear" not in agents or "manager" not in agents:
        logger.error("[Phase 2] 缺少必需的智能体")
        state.status = TaskStatus.FAILED
        state.error_message = "缺少必需的智能体"
        return state

    # 创建阶段执行记录
    phase2_execution = PhaseExecution(
        phase=2,
        phase_name="多空博弈与投资决策",
        started_at=datetime.utcnow(),
        execution_mode="serial",
        max_concurrency=1
    )

    # 获取分析师报告
    analyst_reports = state.analyst_reports

    # 执行多轮辩论
    debate_turns = []
    bull_view = None
    bear_view = None

    for round_idx in range(debate_rounds):
        logger.info(f"[Phase 2] 第 {round_idx + 1} 轮辩论")

        # 看涨分析师
        bull_result = await agents["bull"].analyze(state, analyst_reports)
        bull_view = bull_result["output"]

        # 看跌分析师（在第二轮及之后，可以反驳看涨观点）
        bear_result = await agents["bear"].analyze(
            state,
            analyst_reports,
            bull_view if round_idx > 0 else None
        )
        bear_view = bear_result["output"]

        # 记录辩论轮次
        debate_turns.append({
            "round": round_idx + 1,
            "bull_view": bull_view,
            "bear_view": bear_view
        })

    # 研究经理做出最终决策
    manager_result = await agents["manager"].decide(state, bull_view, bear_view)

    # 更新状态
    state.debate_turns = debate_turns
    state.investment_decision = manager_result.get("decision")

    if manager_result.get("decision"):
        decision = manager_result["decision"]
        state.final_recommendation = decision.get("recommendation")
        state.risk_level = decision.get("risk_level")
        state.buy_price = decision.get("buy_price")
        state.sell_price = decision.get("sell_price")

    # 更新执行记录
    phase2_execution.completed_at = datetime.utcnow()
    phase2_execution.status = TaskStatus.COMPLETED

    # 添加智能体执行记录
    for slug, name in [("bull", "看涨分析师"), ("bear", "看跌分析师"), ("manager", "研究经理")]:
        phase2_execution.agents.append(
            AgentExecution(
                slug=slug,
                name=name,
                started_at=phase2_execution.started_at,
                completed_at=phase2_execution.completed_at,
                status=TaskStatus.COMPLETED
            )
        )

    state.phase_executions.append(phase2_execution)

    # 更新进度
    state.progress = 50.0  # Phase 2 完成后进度 50%

    logger.info(f"[Phase 2] 完成, 推荐: {state.final_recommendation}")

    return state
