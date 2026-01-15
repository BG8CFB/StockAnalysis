"""
TradingAgents 工作流模块

包含工作流调度器和四阶段智能体执行函数。

**版本**: v2.0
**最后更新**: 2026-01-15
"""

# 导入工作流调度器
from .scheduler import (
    WorkflowScheduler,
    WorkflowSchedulerBuilder,
    create_workflow_scheduler,
    should_continue,
)

# 导入工作流状态
from .state import (
    WorkflowState,
    create_initial_state,
    TaskStatus,
)

# 导入四阶段执行函数
from .phase1 import execute_phase1
from .phase2 import execute_phase2
from .phase3 import execute_phase3
from .phase4 import execute_phase4

__all__ = [
    # 调度器
    "WorkflowScheduler",
    "WorkflowSchedulerBuilder",
    "create_workflow_scheduler",
    "should_continue",
    # 状态
    "WorkflowState",
    "create_initial_state",
    "TaskStatus",
    # 阶段执行
    "execute_phase1",
    "execute_phase2",
    "execute_phase3",
    "execute_phase4",
]
