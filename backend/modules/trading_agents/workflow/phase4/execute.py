"""
Phase 4 执行函数

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15

协调策略分析师和风险管理委员会主席，完成 Phase 4 执行。
"""

import logging
from typing import Dict, Any
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from modules.trading_agents.models.state import (
    WorkflowState,
    PhaseExecution,
    AgentExecution,
    TaskStatus,
)
from modules.trading_agents.config import get_enabled_agents
from modules.trading_agents.workflow.phase4.aggressive_debator import AggressiveDebator
from modules.trading_agents.workflow.phase4.neutral_debator import NeutralDebator
from modules.trading_agents.workflow.phase4.conservative_debator import ConservativeDebator
from modules.trading_agents.workflow.phase4.risk_manager import RiskManager

logger = logging.getLogger(__name__)


async def execute_phase4(
    state: WorkflowState,
    model: BaseChatModel,
    config: Dict[str, Any]
) -> WorkflowState:
    """
    执行 Phase 4: 策略风格与风险评估

    Args:
        state: 工作流状态
        model: LLM 模型
        config: 智能体配置

    Returns:
        更新后的工作流状态
    """
    logger.info(f"[Phase 4] 开始执行, 任务ID: {state.task_id}")

    # 更新状态
    state.current_phase = 4
    state.status = TaskStatus.RUNNING

    # 检查阶段是否启用
    phase4_config = config.get("phase4", {})
    if not phase4_config.get("enabled", True):
        logger.warning("[Phase 4] 阶段未启用，跳过")
        state.status = TaskStatus.COMPLETED
        state.progress = 100.0
        state.completed_at = datetime.utcnow()
        return state

    # 获取智能体配置
    agents_config = get_enabled_agents(config, "phase4")

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
        logger.warning("[Phase 4] 没有策略分析师")

    if not risk_manager:
        logger.error("[Phase 4] 缺少风险管理委员会主席")
        state.status = TaskStatus.FAILED
        state.error_message = "缺少风险管理委员会主席"
        return state

    # 创建阶段执行记录
    phase4_execution = PhaseExecution(
        phase=4,
        phase_name="策略风格与风险评估",
        started_at=datetime.utcnow(),
        execution_mode="serial",
        max_concurrency=1
    )

    # 执行策略分析师
    strategy_reports = []
    for debator in debators:
        result = await debator.analyze(state, state.investment_decision)
        strategy_reports.append(result)
        state.strategy_reports.append({
            "slug": result["slug"],
            "name": result["name"],
            "content": result["output"],
            "timestamp": datetime.utcnow().isoformat()
        })

    # 执行风险管理委员会主席
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
    phase4_execution.completed_at = datetime.utcnow()
    phase4_execution.status = TaskStatus.COMPLETED

    # 添加智能体执行记录
    for debator in debators:
        phase4_execution.agents.append(
            AgentExecution(
                slug=debator.slug,
                name=debator.name,
                started_at=phase4_execution.started_at,
                completed_at=phase4_execution.completed_at,
                status=TaskStatus.COMPLETED
            )
        )

    phase4_execution.agents.append(
        AgentExecution(
            slug="risk-manager",
            name="风险管理委员会主席",
            started_at=phase4_execution.started_at,
            completed_at=phase4_execution.completed_at,
            status=TaskStatus.COMPLETED
        )
    )

    state.phase_executions.append(phase4_execution)

    # 更新进度
    state.progress = 100.0
    state.status = TaskStatus.COMPLETED
    state.completed_at = datetime.utcnow()

    logger.info(f"[Phase 4] 完成, 最终推荐: {state.final_recommendation}")

    return state
