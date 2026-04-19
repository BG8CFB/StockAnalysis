"""
TradingAgents 工作流状态定义

不使用 LangGraph，使用简单的字典和 asyncio 调度。
状态在调度器和各阶段 runner 之间传递。

**版本**: v3.1 (统一状态定义)
**最后更新**: 2026-01-28
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    PHASE1 = "phase1"
    PHASE2 = "phase2"
    PHASE3 = "phase3"
    PHASE4 = "phase4"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"
    EXPIRED = "expired"


class RecommendationType(str, Enum):
    """投资建议类型"""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


# =============================================================================
# 辅助数据类（从 models/state.py 迁移）
# =============================================================================


@dataclass
class TokenUsage:
    """Token 使用统计"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "TokenUsage") -> "TokenUsage":
        """累加 Token 使用量"""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class AgentExecution:
    """智能体执行记录"""

    slug: str
    name: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
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
    status: str = "pending"


class WorkflowState:
    """
    工作流状态类

    在四个阶段之间传递的共享状态。
    不使用 LangGraph TypedDict，使用普通 Python 类。
    """

    def __init__(
        self,
        task_id: str,
        user_id: str,
        stock_code: str,
        trade_date: str,
        model_config: Optional[Dict[str, Any]] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        market: str = "A_STOCK",
        max_debate_rounds: int = 2,
        enable_phase1: bool = True,
        enable_phase2: bool = True,
        enable_phase3: bool = True,
        enable_phase4: bool = True,
    ):
        # 处理 None 值为空字典
        if model_config is None:
            model_config = {}
        if agent_config is None:
            agent_config = {}

        # ===== 基础信息 =====
        self.task_id = task_id
        self.user_id = user_id
        self.stock_code = stock_code
        self.trade_date = trade_date
        self.market = market
        self.current_phase: str | int = "pending"
        self.status = TaskStatus.PENDING.value
        self.start_time = datetime.now().isoformat()
        self.end_time: Optional[str] = None

        # ===== 配置信息 =====
        self.max_debate_rounds = max_debate_rounds
        self.enable_phase1 = enable_phase1
        self.enable_phase2 = enable_phase2
        self.enable_phase3 = enable_phase3
        self.enable_phase4 = enable_phase4
        self.model_config = model_config  # {"data_collection_model": "...", "debate_model": "..."}
        self.agent_config = agent_config  # {"phase1": {"agents": [...]}, ...}

        # ===== Phase 1: 分析师报告 =====
        self.analyst_reports: List[Dict[str, Any]] = []
        self.completed_analysts = 0
        self.expected_analysts = self._calculate_expected_analysts(agent_config)

        # ===== Phase 2: 研究与辩论 =====
        self.bull_base_report: Optional[Dict[str, Any]] = None
        self.bear_base_report: Optional[Dict[str, Any]] = None
        self.debate_turns: List[Dict[str, Any]] = []
        self.manager_decision: Optional[Dict[str, Any]] = None
        self.trade_plan: Optional[Dict[str, Any]] = None

        # ===== Phase 2: 风险评估 =====
        self.risk_assessments: List[Dict[str, Any]] = []
        self.cro_summary: Optional[Dict[str, Any]] = None

        # ===== Phase 3: 策略分析 =====
        self.strategy_reports: List[Dict[str, Any]] = []
        self.investment_decision: Optional[Dict[str, Any]] = None
        self.trading_plan: Optional[Dict[str, Any]] = None
        self.risk_approval: Optional[Dict[str, Any]] = None
        self.final_recommendation: Optional[str] = None
        self.risk_level: Optional[str] = None

        # ===== Phase 4: 最终报告 =====
        self.summary_report: Optional[Dict[str, Any]] = None
        self.summary_confidence: Optional[str] = None
        self.price_predictions: Optional[Dict[str, Any]] = None
        self.final_report: Optional[str] = None
        self.recommendation: Optional[str] = None

        # ===== 股票信息 =====
        self.stock_name: Optional[str] = None

        # ===== 执行状态 =====
        self.phase_executions: List[PhaseExecution] = []
        self.progress: float = 0.0
        self.completed_at: Optional[datetime] = None
        self.started_at: Optional[str] = None
        self.error_message: Optional[str] = None
        self.current_agent: Optional[str] = None

        # ===== 价格预测 =====
        self.buy_price: Optional[float] = None
        self.sell_price: Optional[float] = None

        # ===== 细粒度进度追踪 =====
        self.total_agent_executions = 0  # 总智能体执行次数
        self.completed_agent_executions = 0  # 已完成智能体执行次数
        self.phase_agent_counts: Dict[int, int] = {}  # 各阶段智能体数量映射

        # ===== 元数据 =====
        self.token_usage: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []

    def _calculate_expected_analysts(self, agent_config: Dict[str, Any]) -> int:
        """根据配置计算预期的分析师数量"""
        try:
            phase1_agents = agent_config.get("phase1", {}).get("agents", [])
            enabled_count = sum(1 for a in phase1_agents if a.get("enabled", True))
            return enabled_count if enabled_count > 0 else 4
        except Exception:
            return 4

    def calculate_progress(self) -> float:
        """
        计算当前进度（基于智能体执行情况）

        Returns:
            进度百分比 (0.0 - 100.0)，保留一位小数
        """
        if self.total_agent_executions == 0:
            return 0.0
        # 保留一位小数，避免无限循环小数（如 6.6666667%）
        return round((self.completed_agent_executions / self.total_agent_executions) * 100, 1)

    def initialize_progress_tracking(self, phase1_count: int, debate_rounds: int = 2) -> None:
        """
        初始化进度追踪

        Args:
            phase1_count: Phase 1 的智能体数量
            debate_rounds: Phase 2 的辩论轮数（默认 2）
        """
        # Phase 1: N 个分析师
        phase1_executions = phase1_count

        # Phase 2: 辩论轮数 × 2 (bull + bear) + 2 (manager + trader)
        # 例如：2 轮辩论 = 2×2 + 2 = 6 次执行
        phase2_executions = debate_rounds * 2 + 2

        # Phase 3: 4 个智能体（3 个策略师 + 1 个风控）
        phase3_executions = 4

        # Phase 4: 1 个智能体（总结智能体）
        phase4_executions = 1

        # 存储各阶段智能体数量
        self.phase_agent_counts = {
            1: phase1_executions,
            2: phase2_executions,
            3: phase3_executions,
            4: phase4_executions,
        }

        # 计算总智能体执行次数
        self.total_agent_executions = (
            phase1_executions + phase2_executions + phase3_executions + phase4_executions
        )

        # 初始化进度为 0
        self.completed_agent_executions = 0
        self.progress = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 API 返回）"""
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "stock_code": self.stock_code,
            "status": self.status,
            "current_phase": self.current_phase,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "analyst_reports_count": len(self.analyst_reports),
            "debate_rounds": len(self.debate_turns),
            "risk_assessments_count": len(self.risk_assessments),
            "has_final_report": self.final_report is not None,
            "recommendation": self.recommendation,
            "token_usage": self._calculate_total_tokens(),
        }

    def _calculate_total_tokens(self) -> Dict[str, int]:
        """计算总 Token 使用量"""
        total: Dict[str, int] = {}
        for usage in self.token_usage:
            tokens = usage.get("tokens", {})
            for key, value in tokens.items():
                total[key] = total.get(key, 0) + value
        return total

    def add_token_usage(self, phase: str, model_id: str, tokens: Dict[str, int]) -> None:
        """添加 Token 使用记录"""
        self.token_usage.append(
            {
                "phase": phase,
                "model_id": model_id,
                "tokens": tokens,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_error(self, phase: str, error: str, details: Optional[Dict] = None) -> None:
        """添加错误记录"""
        self.errors.append(
            {
                "phase": phase,
                "error": error,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_tool_call(self, phase: str, agent: str, tool: str, result: Any) -> None:
        """添加工具调用记录"""
        self.tool_calls.append(
            {
                "phase": phase,
                "agent": agent,
                "tool": tool,
                "result": str(result),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def is_phase_enabled(self, phase: str) -> bool:
        """检查阶段是否启用"""
        return getattr(self, f"enable_{phase}", True)

    def get_model_id(self, phase: str) -> str:
        """获取阶段对应的模型 ID"""
        if phase in ["phase1"]:
            result = self.model_config.get("data_collection_model", "glm-4.7")
            return str(result) if result is not None else "glm-4.7"
        else:
            result = self.model_config.get("debate_model", "glm-4.7")
            return str(result) if result is not None else "glm-4.7"

    def get_phase1_agents(self) -> List[Dict[str, Any]]:
        """获取 Phase 1 启用的智能体配置"""
        agents = self.agent_config.get("phase1", {}).get("agents", [])
        return [a for a in agents if a.get("enabled", True)]


def create_initial_state(
    task_id: str,
    user_id: str,
    stock_code: str,
    trade_date: str,
    model_config: Optional[Dict[str, Any]] = None,
    agent_config: Optional[Dict[str, Any]] = None,
    market: str = "A_STOCK",
    max_debate_rounds: int = 2,
    enable_phase1: bool = True,
    enable_phase2: bool = True,
    enable_phase3: bool = True,
    enable_phase4: bool = True,
) -> WorkflowState:
    """
    创建初始工作流状态

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        stock_code: 股票代码
        trade_date: 交易日期
        model_config: 模型配置
        agent_config: 智能体配置
        market: 市场类型
        max_debate_rounds: 最大辩论轮次
        enable_phase1: 启用第一阶段
        enable_phase2: 启用第二阶段
        enable_phase3: 启用第三阶段
        enable_phase4: 启用第四阶段

    Returns:
        WorkflowState 实例
    """
    # 处理 None 值为空字典
    if model_config is None:
        model_config = {}
    if agent_config is None:
        agent_config = {}

    return WorkflowState(
        task_id=task_id,
        user_id=user_id,
        stock_code=stock_code,
        trade_date=trade_date,
        model_config=model_config,
        agent_config=agent_config,
        market=market,
        max_debate_rounds=max_debate_rounds,
        enable_phase1=enable_phase1,
        enable_phase2=enable_phase2,
        enable_phase3=enable_phase3,
        enable_phase4=enable_phase4,
    )
