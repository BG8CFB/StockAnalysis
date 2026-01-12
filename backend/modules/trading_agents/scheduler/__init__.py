"""
TradingAgents 工作流调度器

负责按业务流程顺序调度四个阶段：
- Phase 1: 分析师团队（并发）
- Phase 2: 研究与辩论（串行）
- Phase 3: 风险评估（串行）
- Phase 4: 总结报告（串行）
"""

from .state import WorkflowState, create_initial_state, TaskStatus, RecommendationType

__all__ = [
    "WorkflowState",
    "create_initial_state",
    "TaskStatus",
    "RecommendationType",
]
