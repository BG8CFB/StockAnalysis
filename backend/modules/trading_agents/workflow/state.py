"""
LangGraph 工作流状态定义

遵循 LangGraph 官方最佳实践：
- 使用 TypedDict 定义状态结构
- 使用 Annotated[type, reducer] 指定状态更新策略
- 使用 operator.add 实现列表累积

官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#state
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal
from datetime import datetime
from enum import Enum
import operator

from modules.trading_agents.schemas import UserAgentConfigResponse


def max_reducer(left: int, right: int) -> int:
    """取最大值的reducer，用于处理并发计数更新"""
    return max(left, right)


# =============================================================================
# 辅助类型定义
# =============================================================================

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 运行中
    PHASE1 = "phase1"  # 第一阶段
    PHASE2 = "phase2"  # 第二阶段
    PHASE3 = "phase3"  # 第三阶段
    PHASE4 = "phase4"  # 第四阶段
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    EXPIRED = "expired"  # 已过期


class RecommendationType(str, Enum):
    """投资建议类型"""
    STRONG_BUY = "STRONG_BUY"  # 强烈买入
    BUY = "BUY"  # 买入
    HOLD = "HOLD"  # 持有
    SELL = "SELL"  # 卖出
    STRONG_SELL = "STRONG_SELL"  # 强烈卖出


# =============================================================================
# 输入状态（用户输入）
# =============================================================================

class TradingAgentInputState(TypedDict):
    """
    工作流输入状态

    遵循官方最佳实践：定义独立的输入 schema
    """
    required: str  # 用户 ID
    stock_code: str  # 股票代码
    trade_date: str  # 交易日期
    task_id: str  # 任务 ID

    # 可选配置
    max_debate_rounds: Optional[int]  # 最大辩论轮次（默认 2）
    phase2_concurrency: Optional[int]  # Phase 2 辩论并发数（默认 1）
    phase3_concurrency: Optional[int]  # Phase 3 风险评估并发数（默认 3）
    enable_phase1: Optional[bool]  # 启用第一阶段
    enable_phase2: Optional[bool]  # 启用第二阶段
    enable_phase3: Optional[bool]  # 启用第三阶段
    enable_phase4: Optional[bool]  # 启用第四阶段

    # 模型配置
    model_config: Optional[Dict[str, Any]]  # 模型配置
    agent_config: Optional[Dict[str, Any]]  # 智能体配置


# =============================================================================
# 内部状态（完整的工作流状态）
# =============================================================================

class TradingAgentState(TypedDict):
    """
    TradingAgents 工作流主状态

    遵循 LangGraph 官方最佳实践：
    - 使用 TypedDict 定义状态结构
    - 使用 Annotated[type, operator.add] 实现列表累积（reducer 模式）
    - 未指定 reducer 的字段默认为覆盖模式

    官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#reducers
    """

    # ===== 基础信息（覆盖模式，默认 reducer） =====
    user_id: str
    stock_code: str
    trade_date: str
    task_id: str
    current_phase: str  # 当前阶段
    status: str  # 任务状态
    start_time: str  # 开始时间
    end_time: Optional[str]  # 结束时间

    # ===== 配置信息（覆盖） =====
    max_debate_rounds: int  # 最大辩论轮次
    phase2_concurrency: int  # Phase 2 辩论并发数（1=串行，2=并发）
    phase3_concurrency: int  # Phase 3 风险评估并发数（1/2/3+）
    enable_phase1: bool
    enable_phase2: bool
    enable_phase3: bool
    enable_phase4: bool
    model_config: Dict[str, Any]  # **AI 模型配置（data_collection_model, debate_model）**
    agent_config: Dict[str, Any]  # **智能体配置（Phase 1 动态节点）**

    # ===== Phase 1: 分析师报告（累积模式） =====
    # 使用 operator.add reducer：每个节点的输出会自动追加到列表
    analyst_reports: Annotated[List[Dict[str, Any]], operator.add]

    # Phase 1 完成计数（使用 operator.add 累加）
    expected_analysts: int  # 预期的分析师数量
    completed_analysts: Annotated[int, operator.add]  # 已完成的分析师数量（累加模式）

    # ===== Phase 2: 辩论记录（累积模式） =====
    # 完整报告（包含初始观点 + 所有辩论轮次）
    bull_base_report: Optional[Dict[str, Any]]  # 看涨完整报告（覆盖模式，只保留最终版）
    bear_base_report: Optional[Dict[str, Any]]  # 看跌完整报告（覆盖模式，只保留最终版）

    # 辩论轮次快照（仅用于追溯和前端展示）
    debate_turns: Annotated[List[Dict[str, Any]], operator.add]  # 辩论轮次记录
    manager_decision: Annotated[List[Dict[str, Any]], operator.add]  # 研究经理裁决
    trade_plan: Annotated[List[Dict[str, Any]], operator.add]  # 交易计划

    # Phase 2 执行状态（覆盖模式）
    bull_initial_completed: bool  # 看涨初始报告已完成
    bear_initial_completed: bool  # 看跌初始报告已完成
    current_debate_round: int  # 当前辩论轮次（从 0 开始）

    # ===== Phase 3: 风险评估（累积模式） =====
    risk_assessments: Annotated[List[Dict[str, Any]], operator.add]  # 三派评估
    cro_summary: Annotated[List[Dict[str, Any]], operator.add]  # CRO 总结

    # ===== Phase 4: 最终报告 =====
    final_report: Optional[Dict[str, Any]]  # 最终报告（覆盖，只保留最后一个）

    # ===== 元数据（累积） =====
    token_usage: Annotated[List[Dict[str, Any]], operator.add]  # Token 使用追踪
    errors: Annotated[List[Dict[str, Any]], operator.add]  # 错误记录
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]  # 工具调用记录

    # ===== 统计和追踪（新增字段） =====
    tool_stats: Dict[str, Any]  # 工具调用统计（覆盖模式）
    phase_executions: Dict[str, Any]  # 各阶段执行统计（覆盖模式）
    concurrency_groups: Dict[str, Any]  # 并发组信息（覆盖模式）
    agent_messages: Annotated[List[Dict[str, Any]], operator.add]  # 智能体消息流（累积模式）


# =============================================================================
# 输出状态（用户输出）
# =============================================================================

class TradingAgentOutputState(TypedDict):
    """
    工作流输出状态

    遵循官方最佳实践：定义独立的输出 schema
    """
    task_id: str
    user_id: str
    stock_code: str
    status: str
    final_report: Optional[Dict[str, Any]]
    recommendation: Optional[str]  # 投资建议
    token_usage: Dict[str, int]  # 总计 Token 使用量
    start_time: str
    end_time: Optional[str]


# =============================================================================
# 工具函数
# =============================================================================

def create_initial_state(
    task_id: str,
    user_id: str,
    stock_code: str,
    trade_date: str,
    max_debate_rounds: int = 2,
    phase2_concurrency: int = 1,
    phase3_concurrency: int = 3,
    enable_phase1: bool = True,
    enable_phase2: bool = True,
    enable_phase3: bool = True,
    enable_phase4: bool = True,
    model_config: Optional[Dict[str, Any]] = None,
    agent_config: Optional[UserAgentConfigResponse] = None,
) -> TradingAgentState:
    """
    创建初始工作流状态

    遵循官方最佳实践：提供辅助函数创建初始状态

    **重要修改**: 根据 agent_config 动态计算 expected_analysts

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        stock_code: 股票代码
        trade_date: 交易日期
        max_debate_rounds: 最大辩论轮次
        enable_phase1: 启用第一阶段
        enable_phase2: 启用第二阶段
        enable_phase3: 启用第三阶段
        enable_phase4: 启用第四阶段
        model_config: 模型配置
        agent_config: 智能体配置（用于动态计算 expected_analysts）

    Returns:
        初始化的 TradingAgentState
    """
    # **关键修改**: 根据 agent_config 动态计算 expected_analysts
    expected_analysts = 4  # 默认值

    # **详细调试日志**
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[create_initial_state] 开始计算 expected_analysts")
    logger.info(f"[create_initial_state] agent_config 类型: {type(agent_config)}")
    logger.info(f"[create_initial_state] agent_config 内容: {agent_config}")

    if agent_config:
        # 处理字典类型的配置
        if isinstance(agent_config, dict):
            logger.info(f"[create_initial_state] 使用字典路径处理")
            phase1_config = agent_config.get("phase1", {})
            logger.info(f"[create_initial_state] phase1_config: {phase1_config}")
            phase1_agents = phase1_config.get("agents", [])
            logger.info(f"[create_initial_state] phase1_agents (原始): {phase1_agents}")
            # 计算启用的分析师数量
            enabled_agents = [a for a in phase1_agents if a.get("enabled")]
            logger.info(f"[create_initial_state] enabled_agents (过滤后): {enabled_agents}")
            logger.info(f"[create_initial_state] enabled_agents 数量: {len(enabled_agents)}")
            expected_analysts = len(enabled_agents) if enabled_agents else 4
        else:
            # Pydantic 对象
            logger.info(f"[create_initial_state] 使用 Pydantic 对象路径处理")
            phase1_config = agent_config.phase1 if agent_config.phase1 else None
            logger.info(f"[create_initial_state] phase1_config: {phase1_config}")
            phase1_agents = phase1_config.agents if phase1_config else []
            logger.info(f"[create_initial_state] phase1_agents (原始): {phase1_agents}")
            # 计算启用的分析师数量
            enabled_agents = [a for a in phase1_agents if a.enabled]
            logger.info(f"[create_initial_state] enabled_agents (过滤后): {enabled_agents}")
            logger.info(f"[create_initial_state] enabled_agents 数量: {len(enabled_agents)}")
            expected_analysts = len(enabled_agents) if enabled_agents else 4
    else:
        logger.warning(f"[create_initial_state] agent_config 为空，使用默认值 4")

    logger.info(f"[create_initial_state] 最终 expected_analysts: {expected_analysts}")

    return {
        # 基础信息
        "user_id": user_id,
        "stock_code": stock_code,
        "trade_date": trade_date,
        "task_id": task_id,
        "current_phase": "pending",
        "status": TaskStatus.PENDING.value,
        "start_time": datetime.now().isoformat(),
        "end_time": None,

        # 配置
        "max_debate_rounds": max_debate_rounds,
        "phase2_concurrency": phase2_concurrency,
        "phase3_concurrency": phase3_concurrency,
        "enable_phase1": enable_phase1,
        "enable_phase2": enable_phase2,
        "enable_phase3": enable_phase3,
        "enable_phase4": enable_phase4,
        "model_config": model_config or {},  # **新增：保存模型配置到状态**
        "agent_config": agent_config or {},  # **新增：保存智能体配置到状态**

        # Phase 1（动态数量）
        "analyst_reports": [],
        "expected_analysts": expected_analysts,  # **根据配置动态设置**
        "completed_analysts": 0,

        # Phase 2
        "bull_base_report": None,  # 新增：看涨完整报告
        "bear_base_report": None,  # 新增：看跌完整报告
        "debate_turns": [],
        "manager_decision": [],
        "trade_plan": [],
        "bull_initial_completed": False,  # 新增：看涨初始报告完成状态
        "bear_initial_completed": False,  # 新增：看跌初始报告完成状态
        "current_debate_round": 0,  # 新增：当前辩论轮次

        # Phase 3
        "risk_assessments": [],
        "cro_summary": [],

        # Phase 4
        "final_report": None,

        # 元数据
        "token_usage": [],
        "errors": [],
        "tool_calls": [],

        # 统计和追踪
        "tool_stats": {},
        "phase_executions": {},
        "concurrency_groups": {},
        "agent_messages": [],
    }
