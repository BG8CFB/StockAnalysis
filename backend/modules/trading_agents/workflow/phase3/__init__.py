"""
Phase 3: 策略风格与风险评估

**版本**: v4.0 (策略分析师+风险管理重构版)
**最后更新**: 2026-01-16

激进、中性、保守策略分析师，以及风险管理委员会主席。
"""

from .aggressive_debator import AggressiveDebator
from .neutral_debator import NeutralDebator
from .conservative_debator import ConservativeDebator
from .risk_manager import RiskManager

__all__ = [
    "AggressiveDebator",
    "NeutralDebator",
    "ConservativeDebator",
    "RiskManager",
    "execute_phase3",
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


async def execute_phase3(
    state: WorkflowState,
    model: BaseChatModel,
    config: Dict[str, Any]
) -> WorkflowState:
    """
    执行 Phase 3: 策略风格与风险评估

    并发执行逻辑：
    - 激进、中性、保守策略分析师：并行执行
    - 风险管理委员会主席：等待所有策略分析师完成后串行执行

    Args:
        state: 工作流状态
        model: LLM 模型
        config: 智能体配置

    Returns:
        更新后的工作流状态
    """
    import asyncio

    # 获取 WebSocket 管理器
    from modules.trading_agents.api.websocket_manager import websocket_manager

    logger.info(f"[Phase 3] 开始执行, 任务ID: {state.task_id}")

    # 更新状态
    state.current_phase = 3
    state.status = TaskStatus.RUNNING

    # 检查阶段是否启用
    phase3_config = config.get("phase3", {})
    if not phase3_config.get("enabled", True):
        logger.warning("[Phase 3] 阶段未启用，跳过")
        state.progress = 75.0  # Phase 3 完成后进度 75%
        return state

    # 获取智能体配置
    agents_config = get_enabled_agents(config, "phase3")

    # 发送阶段智能体列表事件
    phase_agents_event = create_phase_agents_event(
        task_id=state.task_id,
        phase=3,
        phase_name="策略风格与风险评估",
        execution_mode="hybrid",  # 混合模式（策略师并发，风控串行）
        max_concurrency=3,  # 3个策略师并发
        agents=agents_config
    )
    await websocket_manager.broadcast_event(state.task_id, phase_agents_event)
    logger.info(f"[Phase 3] 已发送智能体列表事件, 智能体数量: {len(agents_config)}")

    # 创建智能体实例（传入 task_id 和 websocket_manager 用于工具调用事件推送）
    debators = []
    risk_manager = None

    for agent_config in agents_config:
        slug = agent_config["slug"]
        if slug == "aggressive-debator":
            debators.append(AggressiveDebator(model, agent_config, task_id=state.task_id, websocket_manager=websocket_manager))
        elif slug == "neutral-debator":
            debators.append(NeutralDebator(model, agent_config, task_id=state.task_id, websocket_manager=websocket_manager))
        elif slug == "conservative-debator":
            debators.append(ConservativeDebator(model, agent_config, task_id=state.task_id, websocket_manager=websocket_manager))
        elif slug == "risk-manager":
            risk_manager = RiskManager(model, agent_config, task_id=state.task_id, websocket_manager=websocket_manager)

    if not debators:
        logger.warning("[Phase 3] 没有策略分析师")

    if not risk_manager:
        logger.error("[Phase 3] 缺少风险管理委员会主席")
        state.status = TaskStatus.FAILED
        state.error_message = "缺少风险管理委员会主席"
        return state

    # 创建阶段执行记录（混合模式：策略分析师并发，主席串行）
    phase3_execution = PhaseExecution(
        phase=3,
        phase_name="策略风格与风险评估",
        started_at=datetime.utcnow(),
        execution_mode="mixed",
        max_concurrency=len(debators)  # 策略分析师可以并行
    )

    # 并发执行所有策略分析师
    async def execute_debator(debator):
        # 发送策略分析师开始事件
        await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
            task_id=state.task_id,
            agent_slug=debator.slug,
            agent_name=debator.name
        ))
        
        try:
            result = await debator.analyze(state, state.investment_decision)
            
            if result and result.get("output"):
                # 发送报告生成事件
                await websocket_manager.broadcast_event(state.task_id, create_report_generated_event(
                    task_id=state.task_id,
                    agent_slug=result["slug"],
                    agent_name=result["name"],
                    content=result["output"]
                ))
                # 发送策略分析师完成事件
                await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
                    task_id=state.task_id,
                    agent_slug=result["slug"],
                    agent_name=result["name"],
                    token_usage={}  # 暂无 token 用量
                ))
            return result
        except Exception as e:
            logger.error(f"[Phase 3] 策略分析师 {debator.slug} 执行异常: {e}")
            return e

    strategy_tasks = [execute_debator(debator) for debator in debators]
    strategy_results = await asyncio.gather(*strategy_tasks, return_exceptions=True)

    # 处理策略分析师结果
    strategy_reports = []
    for i, result in enumerate(strategy_results):
        if isinstance(result, Exception):
            continue

        if result and result.get("output"):
            strategy_reports.append(result)
            state.strategy_reports.append({
                "slug": result["slug"],
                "name": result["name"],
                "content": result["output"],
                "timestamp": datetime.utcnow().isoformat()
            })

    # 执行风险管理委员会主席（串行，等待所有策略分析师完成）
    # 发送风险管理委员会主席开始事件
    await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
        task_id=state.task_id,
        agent_slug="risk-manager",
        agent_name="风险管理委员会主席"
    ))
    manager_result = await risk_manager.assess(state, strategy_reports, state.investment_decision)

    # 发送风险管理委员会主席完成事件
    if manager_result and manager_result.get("output"):
        await websocket_manager.broadcast_event(state.task_id, create_report_generated_event(
            task_id=state.task_id,
            agent_slug="risk-manager",
            agent_name="风险管理委员会主席",
            content=manager_result["output"]
        ))
        await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
            task_id=state.task_id,
            agent_slug="risk-manager",
            agent_name="风险管理委员会主席",
            token_usage={}  # 暂无 token 用量
        ))

    # 更新状态
    if manager_result.get("decision"):
        decision = manager_result["decision"]
        state.risk_approval = decision
        # 添加报告内容到 risk_approval，以便持久化
        if manager_result.get("output"):
            state.risk_approval["content"] = manager_result["output"]

        # 更新最终推荐（风险经理可以否决或调整）
        if decision.get("recommendation"):
            state.final_recommendation = decision["recommendation"]
        if decision.get("risk_level"):
            state.risk_level = decision["risk_level"]

    # 更新执行记录
    phase3_execution.completed_at = datetime.utcnow()
    phase3_execution.status = TaskStatus.COMPLETED

    # 添加智能体执行记录
    for debator in debators:
        phase3_execution.agents.append(
            AgentExecution(
                slug=debator.slug,
                name=debator.name,
                started_at=phase3_execution.started_at,
                completed_at=phase3_execution.completed_at,
                status=TaskStatus.COMPLETED
            )
        )

    phase3_execution.agents.append(
        AgentExecution(
            slug="risk-manager",
            name="风险管理委员会主席",
            started_at=phase3_execution.started_at,
            completed_at=phase3_execution.completed_at,
            status=TaskStatus.COMPLETED
        )
    )

    state.phase_executions.append(phase3_execution)

    # 更新进度
    state.progress = 75.0  # Phase 3 完成后进度 75%

    logger.info(f"[Phase 3] 完成, 最终推荐: {state.final_recommendation}")

    return state
