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
    enable_phase1: bool
    enable_phase2: bool
    enable_phase3: bool
    enable_phase4: bool

    # ===== Phase 1: 分析师报告（累积模式） =====
    # 使用 operator.add reducer：每个节点的输出会自动追加到列表
    analyst_reports: Annotated[List[Dict[str, Any]], operator.add]

    # Phase 1 完成计数
    expected_analysts: int  # 预期的分析师数量
    completed_analysts: int  # 已完成的分析师数量

    # ===== Phase 2: 辩论记录（累积模式） =====
    debate_turns: Annotated[List[Dict[str, Any]], operator.add]  # 辩论轮次记录
    manager_decision: Annotated[List[Dict[str, Any]], operator.add]  # 研究经理裁决
    trade_plan: Annotated[List[Dict[str, Any]], operator.add]  # 交易计划

    # ===== Phase 3: 风险评估（累积模式） =====
    risk_assessments: Annotated[List[Dict[str, Any]], operator.add]  # 三派评估
    cro_summary: Annotated[List[Dict[str, Any]], operator.add]  # CRO 总结

    # ===== Phase 4: 最终报告 =====
    final_report: Optional[Dict[str, Any]]  # 最终报告（覆盖，只保留最后一个）

    # ===== 元数据（累积） =====
    token_usage: Annotated[List[Dict[str, Any]], operator.add]  # Token 使用追踪
    errors: Annotated[List[Dict[str, Any]], operator.add]  # 错误记录
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]  # 工具调用记录


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
    enable_phase1: bool = True,
    enable_phase2: bool = True,
    enable_phase3: bool = True,
    enable_phase4: bool = True,
    model_config: Optional[Dict[str, Any]] = None,
    agent_config: Optional[Dict[str, Any]] = None,
) -> TradingAgentState:
    """
    创建初始工作流状态

    遵循官方最佳实践：提供辅助函数创建初始状态

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
        agent_config: 智能体配置

    Returns:
        初始化的 TradingAgentState
    """
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
        "enable_phase1": enable_phase1,
        "enable_phase2": enable_phase2,
        "enable_phase3": enable_phase3,
        "enable_phase4": enable_phase4,

        # Phase 1
        "analyst_reports": [],
        "expected_analysts": 4,  # 默认 4 个分析师
        "completed_analysts": 0,

        # Phase 2
        "debate_turns": [],
        "manager_decision": [],
        "trade_plan": [],

        # Phase 3
        "risk_assessments": [],
        "cro_summary": [],

        # Phase 4
        "final_report": None,

        # 元数据
        "token_usage": [],
        "errors": [],
        "tool_calls": [],
    }
