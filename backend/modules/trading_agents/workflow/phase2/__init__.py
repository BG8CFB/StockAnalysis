"""
Phase 2: 多空博弈与投资决策

**版本**: v4.0 (包含 Trader 重构版)
**最后更新**: 2026-01-16

多空辩论 + 投资组合经理 + 交易员。
"""

from .bull_researcher import BullResearcher
from .bear_researcher import BearResearcher
from .research_manager import ResearchManager
from .trader import Trader

__all__ = [
    "BullResearcher",
    "BearResearcher",
    "ResearchManager",
    "Trader",
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
from modules.trading_agents.workflow.events import (
    create_phase_agents_event,
    create_agent_started_event,
    create_agent_completed_event,
    create_report_generated_event,
)

logger = logging.getLogger(__name__)


async def execute_phase2(
    state: WorkflowState,
    model: BaseChatModel,
    config: Dict[str, Any],
    debate_rounds: int = 2
) -> WorkflowState:
    """
    执行 Phase 2: 多空博弈与投资决策

    并发执行逻辑：
    - 第一轮：看涨和看跌分析师完全并行执行（无依赖）
    - 第二轮及以后：串行执行（看跌需要看涨观点进行反驳）
    - 研究经理：等待所有辩论轮次完成后串行执行
    - 交易员：等待研究经理完成后串行执行

    Args:
        state: 工作流状态
        model: LLM 模型
        config: 智能体配置
        debate_rounds: 辩论轮数

    Returns:
        更新后的工作流状态
    """
    import asyncio

    # 获取 WebSocket 管理器
    from modules.trading_agents.api.websocket_manager import websocket_manager

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

    # 发送阶段智能体列表事件
    phase_agents_event = create_phase_agents_event(
        task_id=state.task_id,
        phase=2,
        phase_name="多空博弈与投资决策",
        execution_mode="hybrid",  # 混合模式（部分并发，部分串行）
        max_concurrency=2,  # 辩论阶段最大并发为2
        agents=agents_config
    )
    await websocket_manager.broadcast_event(state.task_id, phase_agents_event)
    logger.info(f"[Phase 2] 已发送智能体列表事件, 智能体数量: {len(agents_config)}")

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
        elif slug == "trader":
            agents["trader"] = Trader(model, agent_config)

    # 检查必需智能体（Trader 可选）
    if "bull" not in agents or "bear" not in agents or "manager" not in agents:
        logger.error("[Phase 2] 缺少必需的智能体")
        state.status = TaskStatus.FAILED
        state.error_message = "缺少必需的智能体"
        return state

    if "trader" not in agents:
        logger.warning("[Phase 2] 未配置交易员智能体")

    # 创建阶段执行记录（混合模式：看涨看跌并发，经理和交易员串行）
    phase2_execution = PhaseExecution(
        phase=2,
        phase_name="多空博弈与投资决策",
        started_at=datetime.utcnow(),
        execution_mode="mixed",
        max_concurrency=2  # 看涨和看跌可以并行
    )

    # 获取分析师报告
    analyst_reports = state.analyst_reports

    # 执行多轮辩论
    debate_turns = []
    bull_view = None
    bear_view = None

    for round_idx in range(debate_rounds):
        logger.info(f"[Phase 2] 第 {round_idx + 1} 轮辩论")

        if round_idx == 0:
            # 第一轮：看涨和看跌完全并行执行（无依赖）
            # 发送看涨分析师开始事件
            await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
                task_id=state.task_id,
                agent_slug="bull-researcher",
                agent_name="看涨分析师"
            ))
            # 发送看跌分析师开始事件
            await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
                task_id=state.task_id,
                agent_slug="bear-researcher",
                agent_name="看跌分析师"
            ))

            bull_task = agents["bull"].analyze(state, analyst_reports)
            bear_task = agents["bear"].analyze(state, analyst_reports, None)

            bull_result, bear_result = await asyncio.gather(bull_task, bear_task)
            bull_view = bull_result["output"]
            bear_view = bear_result["output"]

            # 发送看涨分析师完成事件
            if bull_result.get("output"):
                await websocket_manager.broadcast_event(state.task_id, create_report_generated_event(
                    task_id=state.task_id,
                    agent_slug="bull-researcher",
                    agent_name="看涨分析师",
                    content=bull_result["output"]
                ))
                await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
                    task_id=state.task_id,
                    agent_slug="bull-researcher",
                    agent_name="看涨分析师",
                    token_usage={}  # 暂无 token 用量
                ))
            # 发送看跌分析师完成事件
            if bear_result.get("output"):
                await websocket_manager.broadcast_event(state.task_id, create_report_generated_event(
                    task_id=state.task_id,
                    agent_slug="bear-researcher",
                    agent_name="看跌分析师",
                    content=bear_result["output"]
                ))
                await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
                    task_id=state.task_id,
                    agent_slug="bear-researcher",
                    agent_name="看跌分析师",
                    token_usage={}  # 暂无 token 用量
                ))
        else:
            # 第二轮及以后：串行执行（看跌需要看涨观点进行反驳）
            # 发送看涨分析师开始事件
            await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
                task_id=state.task_id,
                agent_slug="bull-researcher",
                agent_name="看涨分析师"
            ))
            bull_result = await agents["bull"].analyze(state, analyst_reports)
            bull_view = bull_result["output"]
            # 发送看涨分析师完成事件
            if bull_result.get("output"):
                await websocket_manager.broadcast_event(state.task_id, create_report_generated_event(
                    task_id=state.task_id,
                    agent_slug="bull-researcher",
                    agent_name="看涨分析师",
                    content=bull_result["output"]
                ))
                await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
                    task_id=state.task_id,
                    agent_slug="bull-researcher",
                    agent_name="看涨分析师",
                    token_usage={}  # 暂无 token 用量
                ))

            # 发送看跌分析师开始事件
            await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
                task_id=state.task_id,
                agent_slug="bear-researcher",
                agent_name="看跌分析师"
            ))
            bear_result = await agents["bear"].analyze(
                state,
                analyst_reports,
                bull_view  # 看跌分析师基于看涨观点进行反驳
            )
            bear_view = bear_result["output"]
            # 发送看跌分析师完成事件
            if bear_result.get("output"):
                await websocket_manager.broadcast_event(state.task_id, create_report_generated_event(
                    task_id=state.task_id,
                    agent_slug="bear-researcher",
                    agent_name="看跌分析师",
                    content=bear_result["output"]
                ))
                await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
                    task_id=state.task_id,
                    agent_slug="bear-researcher",
                    agent_name="看跌分析师",
                    token_usage={}  # 暂无 token 用量
                ))

        # 记录辩论轮次
        debate_turns.append({
            "round": round_idx + 1,
            "bull_view": bull_view,
            "bear_view": bear_view
        })

    # 研究经理做出最终决策（串行，等待所有辩论完成）
    # 发送研究经理开始事件
    await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
        task_id=state.task_id,
        agent_slug="research-manager",
        agent_name="研究经理"
    ))
    manager_result = await agents["manager"].decide(state, bull_view, bear_view)
    # 发送研究经理完成事件
    if manager_result.get("output"):
        await websocket_manager.broadcast_event(state.task_id, create_report_generated_event(
            task_id=state.task_id,
            agent_slug="research-manager",
            agent_name="研究经理",
            content=manager_result["output"]
        ))
        await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
            task_id=state.task_id,
            agent_slug="research-manager",
            agent_name="研究经理",
            token_usage={}  # 暂无 token 用量
        ))

    # 更新状态
    state.debate_turns = debate_turns
    state.investment_decision = manager_result.get("decision")

    if manager_result.get("decision"):
        decision = manager_result["decision"]
        state.final_recommendation = decision.get("recommendation")
        state.risk_level = decision.get("risk_level")
        state.buy_price = decision.get("buy_price")
        state.sell_price = decision.get("sell_price")

    # 交易员制定执行计划（串行，等待研究经理完成）
    if "trader" in agents:
        logger.info(f"[Phase 2] 交易员开始制定计划")
        # 发送交易员开始事件
        await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
            task_id=state.task_id,
            agent_slug="trader",
            agent_name="专业交易员"
        ))
        trader_result = await agents["trader"].plan(state, state.investment_decision)

        # 更新交易计划
        if trader_result.get("output"):
            state.trading_plan = {
                "content": trader_result["output"],
                "timestamp": datetime.utcnow().isoformat()
            }
            # 发送交易员完成事件
            await websocket_manager.broadcast_event(state.task_id, create_report_generated_event(
                task_id=state.task_id,
                agent_slug="trader",
                agent_name="专业交易员",
                content=trader_result["output"]
            ))
            await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
                task_id=state.task_id,
                agent_slug="trader",
                agent_name="专业交易员",
                token_usage={}  # 暂无 token 用量
            ))

    # 更新执行记录
    phase2_execution.completed_at = datetime.utcnow()
    phase2_execution.status = TaskStatus.COMPLETED

    # 添加智能体执行记录
    agent_list = [("bull", "看涨分析师"), ("bear", "看跌分析师"), ("manager", "研究经理")]
    if "trader" in agents:
        agent_list.append(("trader", "专业交易员"))

    for slug, name in agent_list:
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
