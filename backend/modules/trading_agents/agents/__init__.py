"""
TradingAgents 智能体模块

包含所有智能体的实现。
"""

from .base import BaseAgent, AnalystAgent, DebateAgent, SummaryAgent
# Phase 1: 使用工厂模式创建分析师，不再导出具体的 Analyst 类
from .phase1.analysts import GenericAnalystTemplate, AnalystFactory, create_phase1_agents
from .phase2.debaters import BullDebater, BearDebater, TradePlanner, create_phase2_agents
from .phase3.risk import ChiefRiskOfficer, create_phase3_agents
from .phase4.summary import FinalSummarizer, create_phase4_agents

__all__ = [
    # Base
    "BaseAgent",
    "AnalystAgent",
    "DebateAgent",
    "SummaryAgent",
    # Phase 1
    "GenericAnalystTemplate",
    "AnalystFactory",
    "create_phase1_agents",
    # Phase 2
    "BullDebater",
    "BearDebater",
    "TradePlanner",
    "create_phase2_agents",
    # Phase 3
    "ChiefRiskOfficer",
    "create_phase3_agents",
    # Phase 4
    "FinalSummarizer",
    "create_phase4_agents",
]
