"""
第一阶段：分析师团队

采用工厂模式动态创建分析师，支持并行执行。
"""

from .analysts import GenericAnalystTemplate, AnalystFactory, create_phase1_agents

__all__ = [
    "GenericAnalystTemplate",
    "AnalystFactory",
    "create_phase1_agents",
]
