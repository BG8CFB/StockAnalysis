"""
第三阶段：风险评估

包含激进派、保守派、中性派和首席风控官。
"""

from .risk_analysts import AggressiveRiskAgent, ConservativeRiskAgent, NeutralRiskAgent
from .risk import ChiefRiskOfficer, create_phase3_agents
from .risk_manager import RiskDiscussionManager

__all__ = [
    "AggressiveRiskAgent",
    "ConservativeRiskAgent",
    "NeutralRiskAgent",
    "ChiefRiskOfficer",
    "RiskDiscussionManager",
    "create_phase3_agents",
]
