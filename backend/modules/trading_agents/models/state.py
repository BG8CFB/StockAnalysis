"""
TradingAgents 工作流状态模型

**注意**: 此文件保留向后兼容性，所有状态定义已迁移到 workflow/state.py
请使用 workflow/state 模块中的 WorkflowState 类。

**版本**: v3.1 (统一状态定义)
**最后更新**: 2026-01-28
"""

# 重新导出 workflow/state 中的所有内容，确保兼容性
from enum import Enum
from typing import Any

from modules.trading_agents.workflow.state import (
    RecommendationType,
    TaskStatus,
    WorkflowState,
)

# 向后兼容别名
Recommendation = RecommendationType


class RiskLevel(str, Enum):
    """风险等级枚举"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# 创建初始状态的工具函数（向后兼容）
def create_initial_state(
    task_id: str,
    user_id: str,
    stock_code: str,
    trade_date: str,
    market: str = "A_STOCK",
    **kwargs: Any,
) -> WorkflowState:
    """
    创建初始工作流状态（向后兼容）

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        stock_code: 股票代码
        trade_date: 交易日期
        market: 市场类型
        **kwargs: 其他参数

    Returns:
        初始化的 WorkflowState
    """
    return WorkflowState(
        task_id=task_id,
        user_id=user_id,
        stock_code=stock_code,
        trade_date=trade_date,
        market=market,
        model_config=kwargs.get("model_config", {}),
        agent_config=kwargs.get("agent_config", {}),
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

    if state.status in [
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    ]:
        return False

    return True
