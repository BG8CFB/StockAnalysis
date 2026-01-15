"""
Phase 4: 策略风格与风险评估

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15

激进、中性、保守策略分析师，以及风险管理委员会主席。
"""

from .aggressive_debator import AggressiveDebator
from .neutral_debator import NeutralDebator
from .conservative_debator import ConservativeDebator
from .risk_manager import RiskManager
from .execute import execute_phase4

__all__ = [
    "AggressiveDebator",
    "NeutralDebator",
    "ConservativeDebator",
    "RiskManager",
    "execute_phase4",
]
