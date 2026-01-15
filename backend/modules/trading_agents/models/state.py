"""
TradingAgents 工作流状态模型

定义了四阶段工作流的状态结构，用于在各个阶段之间传递数据。

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"
    EXPIRED = "expired"


class Recommendation(str, Enum):
    """推荐等级枚举"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class TokenUsage:
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: 'TokenUsage') -> 'TokenUsage':
        """累加 Token 使用量"""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )


@dataclass
class AgentExecution:
    """智能体执行记录"""
    slug: str
    name: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = TaskStatus.PENDING
    token_usage: Optional[TokenUsage] = None
    error_message: Optional[str] = None
    output: Optional[str] = None


@dataclass
class PhaseExecution:
    """阶段执行记录"""
    phase: int
    phase_name: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_mode: str = "concurrent"  # concurrent / serial
    max_concurrency: int = 1
    agents: List[AgentExecution] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    status: str = TaskStatus.PENDING


@dataclass
class WorkflowState:
    """
    工作流状态

    用于在四阶段工作流中传递状态数据。
    每个阶段可以读取和更新状态。
    """

    # 基本信息
    user_id: str
    task_id: str
    stock_code: str
    stock_name: Optional[str] = None
    market: str = "a_share"
    trade_date: Optional[str] = None

    # 任务状态
    status: TaskStatus = TaskStatus.PENDING
    current_phase: int = 0
    current_agent: Optional[str] = None
    progress: float = 0.0

    # 错误信息
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # Phase 1: 分析师团队
    analyst_reports: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 2: 多空博弈
    debate_turns: List[Dict[str, Any]] = field(default_factory=list)
    investment_decision: Optional[Dict[str, Any]] = None

    # Phase 3: 交易执行策划
    trading_plan: Optional[Dict[str, Any]] = None

    # Phase 4: 策略风格与风险评估
    strategy_reports: List[Dict[str, Any]] = field(default_factory=list)
    risk_approval: Optional[Dict[str, Any]] = None

    # 最终报告
    final_report: Optional[str] = None
    final_recommendation: Optional[Recommendation] = None
    risk_level: Optional[RiskLevel] = None
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None

    # Token 用量
    token_usage: TokenUsage = field(default_factory=TokenUsage)

    # 工具调用记录
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    # 执行记录（用于前端展示时间线）
    phase_executions: List[PhaseExecution] = field(default_factory=list)

    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def add_token_usage(self, phase: int, usage: TokenUsage) -> None:
        """添加 Token 使用量"""
        self.token_usage = self.token_usage.add(usage)

    def add_tool_call(self, tool_call: Dict[str, Any]) -> None:
        """添加工具调用记录"""
        self.tool_calls.append(tool_call)

    def get_phase_summary(self) -> Dict[str, Any]:
        """获取阶段摘要"""
        return {
            "task_id": self.task_id,
            "stock_code": self.stock_code,
            "status": self.status,
            "current_phase": self.current_phase,
            "progress": self.progress,
            "token_usage": {
                "prompt_tokens": self.token_usage.prompt_tokens,
                "completion_tokens": self.token_usage.completion_tokens,
                "total_tokens": self.token_usage.total_tokens,
            }
        }


# =============================================================================
# 创建初始状态的工具函数
# =============================================================================

def create_initial_state(
    task_id: str,
    user_id: str,
    stock_code: str,
    trade_date: str,
    market: str = "a_share"
) -> WorkflowState:
    """
    创建初始工作流状态

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        stock_code: 股票代码
        trade_date: 交易日期
        market: 市场类型

    Returns:
        初始化的 WorkflowState
    """
    return WorkflowState(
        user_id=user_id,
        task_id=task_id,
        stock_code=stock_code,
        trade_date=trade_date,
        market=market,
        status=TaskStatus.PENDING,
        current_phase=0,
        progress=0.0
    )


def should_continue(state: WorkflowState, interrupt_signal: bool = False) -> bool:
    """
    判断工作流是否应该继续

    Args:
        state: 当前工作流状态
        interrupt_signal: 中断信号

    Returns:
        是否继续
    """
    if interrupt_signal:
        return False

    if state.status in [TaskStatus.CANCELLED, TaskStatus.STOPPED, TaskStatus.FAILED, TaskStatus.EXPIRED]:
        return False

    return True
