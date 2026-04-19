"""
TradingAgents 模型测试
"""

from modules.trading_agents.models.state import should_continue
from modules.trading_agents.workflow.state import (
    AgentExecution,
    RecommendationType,
    TaskStatus,
    TokenUsage,
    create_initial_state,
)


class TestTaskStatus:
    """任务状态枚举测试"""

    def test_all_statuses(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.PHASE1.value == "phase1"
        assert TaskStatus.PHASE2.value == "phase2"
        assert TaskStatus.PHASE3.value == "phase3"
        assert TaskStatus.PHASE4.value == "phase4"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_status_is_string(self) -> None:
        assert isinstance(TaskStatus.RUNNING, str)


class TestRecommendationType:
    """投资建议类型测试"""

    def test_all_recommendations(self) -> None:
        assert RecommendationType.STRONG_BUY.value == "STRONG_BUY"
        assert RecommendationType.BUY.value == "BUY"
        assert RecommendationType.HOLD.value == "HOLD"
        assert RecommendationType.SELL.value == "SELL"
        assert RecommendationType.STRONG_SELL.value == "STRONG_SELL"


class TestTokenUsage:
    """Token 使用统计测试"""

    def test_default_values(self) -> None:
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_custom_values(self) -> None:
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage.total_tokens == 150


class TestAgentExecution:
    """智能体执行记录测试"""

    def test_default_values(self) -> None:
        ae = AgentExecution(slug="test-agent", name="Test Agent")
        assert ae.name == "Test Agent"
        assert ae.slug == "test-agent"
        assert ae.status == "pending"
        assert ae.output is None

    def test_completed_execution(self) -> None:
        ae = AgentExecution(
            slug="financial-news",
            name="financial_news_analyst",
            status="completed",
            output="分析结果...",
            token_usage=TokenUsage(total_tokens=500),
        )
        assert ae.status == "completed"
        assert ae.token_usage is not None and ae.token_usage.total_tokens == 500


class TestWorkflowState:
    """工作流状态测试"""

    def test_create_initial_state(self) -> None:
        state = create_initial_state(
            task_id="test_001",
            user_id="user_001",
            stock_code="600519",
            trade_date="2024-01-15",
        )
        assert state.task_id == "test_001"
        assert state.user_id == "user_001"
        assert state.stock_code == "600519"
        assert state.status == TaskStatus.PENDING

    def test_should_continue_running(self) -> None:
        state = create_initial_state(
            task_id="t1",
            user_id="u1",
            stock_code="600519",
            trade_date="2024-01-15",
        )
        state.status = TaskStatus.RUNNING
        assert should_continue(state) is True

    def test_should_continue_cancelled(self) -> None:
        state = create_initial_state(
            task_id="t1",
            user_id="u1",
            stock_code="600519",
            trade_date="2024-01-15",
        )
        state.status = TaskStatus.CANCELLED
        assert should_continue(state) is False

    def test_should_continue_failed(self) -> None:
        state = create_initial_state(
            task_id="t1",
            user_id="u1",
            stock_code="600519",
            trade_date="2024-01-15",
        )
        state.status = TaskStatus.FAILED
        assert should_continue(state) is False

    def test_should_continue_with_interrupt(self) -> None:
        state = create_initial_state(
            task_id="t1",
            user_id="u1",
            stock_code="600519",
            trade_date="2024-01-15",
        )
        assert should_continue(state, interrupt_signal=True) is False

    def test_state_progress_tracking(self) -> None:
        state = create_initial_state(
            task_id="t1",
            user_id="u1",
            stock_code="600519",
            trade_date="2024-01-15",
        )
        state.initialize_progress_tracking(phase1_count=3, debate_rounds=2)
        assert state.total_agent_executions > 0
