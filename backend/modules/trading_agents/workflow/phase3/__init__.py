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

    # 创建智能体实例
    debators = []
    risk_manager = None

    for agent_config in agents_config:
        slug = agent_config["slug"]
        if slug == "aggressive-debator":
            debators.append(AggressiveDebator(model, agent_config))
        elif slug == "neutral-debator":
            debators.append(NeutralDebator(model, agent_config))
        elif slug == "conservative-debator":
            debators.append(ConservativeDebator(model, agent_config))
        elif slug == "risk-manager":
            risk_manager = RiskManager(model, agent_config)

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
    strategy_tasks = [
        debator.analyze(state, state.investment_decision)
        for debator in debators
    ]
    strategy_results = await asyncio.gather(*strategy_tasks, return_exceptions=True)

    # 处理策略分析师结果
    strategy_reports = []
    for i, result in enumerate(strategy_results):
        if isinstance(result, Exception):
            logger.error(f"[Phase 3] 策略分析师 {i} 执行异常: {result}")
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
    manager_result = await risk_manager.assess(state, strategy_reports, state.investment_decision)

    # 更新状态
    if manager_result.get("decision"):
        decision = manager_result["decision"]
        state.risk_approval = decision

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
