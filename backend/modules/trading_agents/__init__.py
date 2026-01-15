"""
TradingAgents - 多智能体股票分析系统

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15

这是一个基于 LangChain create_agent 的多智能体协作股票分析模块，支持：
- 四阶段流水线分析（分析师团队 → 研究员辩论 → 风险评估 → 总结输出）
- 动态智能体配置
- MCP 工具集成
- 并发控制与资源池管理
- 实时状态推送

架构说明：
- 使用函数式调用 + LangChain create_agent 替代 LangGraph
- 四阶段工作流：Phase 1 (并发) → Phase 2 (串行) → Phase 3 (串行) → Phase 4 (串行)
"""

__version__ = "3.0.0"

from .api import router as trading_agents_router

__all__ = ["trading_agents_router"]
