"""
第四阶段：总结输出

包含总结智能体，负责生成最终投资建议。
"""

from .summary import FinalSummarizer, create_phase4_agents

__all__ = [
    "FinalSummarizer",
    "create_phase4_agents",
]
