"""
Phase 1: 信息收集与基础分析

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15

并行分析师团队，动态创建智能体。
"""

from .factory import (
    Phase1AgentFactory,
    execute_phase1,
)
from .template import Phase1AgentTemplate

__all__ = [
    "Phase1AgentTemplate",
    "Phase1AgentFactory",
    "execute_phase1",
]
