"""
Phase 4: 总结智能体

**版本**: v4.0 (总结智能体重构版)
**最后更新**: 2026-01-16

总结智能体，汇总所有分析结果，提供最终投资建议和价格预测。
"""

from .summarizer import SummarizerAgent, execute_phase4

__all__ = [
    "SummarizerAgent",
    "execute_phase4",
]
