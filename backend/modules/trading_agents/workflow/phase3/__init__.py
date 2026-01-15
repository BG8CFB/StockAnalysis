"""
Phase 3: 交易执行策划

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15

专业交易员，制定具体的交易执行计划。
"""

from .trader import Trader, execute_phase3

__all__ = [
    "Trader",
    "execute_phase3",
]
