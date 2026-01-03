"""
TradingAgents 工作流状态定义

定义 LangGraph 工作流中使用的所有状态类型和合并函数。
"""

from typing import TypedDict, List, Dict, Optional, Any, Annotated
from enum import Enum
import operator


# =============================================================================
# 辅助类型定义
# =============================================================================

class AnalystOutput(TypedDict):
    """单个分析师的产出"""
    agent_name: str
    role: str
    content: str  # Markdown 格式的分析报告
    data_sources: List[str]
    timestamp: float
    token_usage: Dict[str, int]  # {"prompt_tokens": N, "completion_tokens": M, "total_tokens": X}


class DebateTurn(TypedDict):
    """一轮辩论的记录"""
    round_index: int       # 轮次索引 (1, 2, 3)
    bull_argument: str     # 看涨方本轮的反驳/观点
    bear_argument: str     # 看跌方本轮的反驳/观点


class ToolTrace(TypedDict):
    """工具调用追踪（用于前端实时展示）"""
    agent_name: str
    tool_name: str
    tool_input: str
    tool_output: str
    status: str  # "running", "completed", "failed"
    timestamp: float


# =============================================================================
# 核心状态定义
# =============================================================================

class AgentState(TypedDict):
    """LangGraph 工作流主状态"""

    # --- 基础信息 ---
    task_id: str
    user_id: str
    stock_code: str
    trade_date: str
    max_debate_rounds: int  # 用户配置的最大辩论轮次 (1-3)

    # --- 阶段 1：分析师产出 ---
    # 使用 operator.add 允许并行写入
    analyst_reports: Annotated[List[AnalystOutput], operator.add]

    # --- 阶段 1 完成检测 ---
    expected_analysts: int  # 预期的分析师数量
    completed_analysts: int  # 已完成的分析师数量
    selected_agents: List[str]  # 用户选择的第一阶段智能体标识符列表

    # --- 阶段 2：辩论过程 ---
    initial_bull_view: Optional[str]  # 第0轮：初始看涨观点
    initial_bear_view: Optional[str]  # 第0轮：初始看跌观点

    # 辩论历史：存储每一轮的交叉反驳记录
    debate_turns: Annotated[List[DebateTurn], operator.add]

    trade_plan: Optional[Dict[str, Any]]  # 最终交易计划

    # --- 阶段 3 & 4 ---
    risk_assessment: Optional[Dict[str, Any]]
    final_report: Optional[str]

    # --- Token 追踪 ---
    total_token_usage: Dict[str, int]  # {"prompt_tokens": N, "completion_tokens": M, "total_tokens": X}

    # --- 系统控制 ---
    status: str  # "running", "stopped", "completed", "failed", "expired"
    interrupt_signal: bool  # 用于接收用户停止指令


class InvestmentDebateState(TypedDict):
    """投资辩论状态（第二阶段）"""
    bull_opinion: Optional[str]      # 看涨观点
    bear_opinion: Optional[str]      # 看跌观点
    debate_round: int                # 当前辩论轮次
    manager_decision: Optional[str]  # 研究经理裁决
    investment_plan: Optional[str]   # 交易员投资计划


class RiskDebateState(TypedDict):
    """风险评估状态（第三阶段）"""
    aggressive_view: Optional[str]   # 激进派观点
    conservative_view: Optional[str] # 保守派观点
    neutral_view: Optional[str]      # 中性派观点
    discussion_round: int            # 当前讨论轮次
    risk_assessment: Optional[str]   # 首席风控官评估


# =============================================================================
# 状态合并函数 (Reducers)
# =============================================================================

def merge_reports(
    current: Dict[str, str],
    update: Dict[str, str]
) -> Dict[str, str]:
    """
    合并智能体报告

    规则：
    1. 新报告覆盖旧报告
    2. 保留所有已完成的报告
    3. 用于 LangGraph 的 reducer
    """
    return {**current, **update}


def merge_debate_state(
    current: Optional[InvestmentDebateState],
    update: InvestmentDebateState
) -> InvestmentDebateState:
    """
    合并辩论状态

    用于第二阶段多轮辩论的状态累积
    """
    if current is None:
        return update
    return {**current, **update}


def merge_token_usage(
    current: Dict[str, int],
    update: Dict[str, int]
) -> Dict[str, int]:
    """
    合并 token 使用量

    累加所有智能体的 token 消耗
    """
    result = current.copy()
    for key, value in update.items():
        result[key] = result.get(key, 0) + value
    return result


# =============================================================================
# 工具函数
# =============================================================================

def create_initial_state(
    task_id: str,
    user_id: str,
    stock_code: str,
    trade_date: str,
    max_debate_rounds: int = 2,
    expected_analysts: int = 3,
    selected_agents: list[str] | None = None
) -> AgentState:
    """
    创建初始工作流状态

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        stock_code: 股票代码
        trade_date: 交易日期
        max_debate_rounds: 最大辩论轮次
        expected_analysts: 预期的分析师数量
        selected_agents: 用户选择的第一阶段智能体标识符列表

    Returns:
        初始化的 AgentState
    """
    return {
        "task_id": task_id,
        "user_id": user_id,
        "stock_code": stock_code,
        "trade_date": trade_date,
        "max_debate_rounds": max_debate_rounds,
        "analyst_reports": [],
        "expected_analysts": expected_analysts,
        "completed_analysts": 0,
        "selected_agents": selected_agents or [],
        "initial_bull_view": None,
        "initial_bear_view": None,
        "debate_turns": [],
        "trade_plan": None,
        "risk_assessment": None,
        "final_report": None,
        "total_token_usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "status": "running",
        "interrupt_signal": False,
    }


def should_continue_debate(state: AgentState, max_rounds: int) -> bool:
    """
    判断辩论是否应该继续

    Args:
        state: 当前工作流状态
        max_rounds: 最大辩论轮次

    Returns:
        是否继续辩论
    """
    current_round = len(state.get("debate_turns", []))
    return current_round < max_rounds


def should_execute_phase(phase_enabled: bool, state: AgentState) -> bool:
    """
    判断阶段是否应该执行

    Args:
        phase_enabled: 阶段是否启用
        state: 当前工作流状态

    Returns:
        是否执行该阶段
    """
    # 检查任务是否被中断
    if state.get("interrupt_signal", False):
        return False

    # 检查阶段是否启用
    return phase_enabled
