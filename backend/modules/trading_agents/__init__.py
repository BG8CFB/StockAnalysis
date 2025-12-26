"""
TradingAgents - 多智能体股票分析系统

这是一个基于 LangGraph 的多智能体协作股票分析模块，支持：
- 四阶段流水线分析（分析师团队 → 研究员辩论 → 风险评估 → 总结输出）
- 动态智能体配置
- MCP 工具集成
- 并发控制与资源池管理
- 实时状态推送
"""

__version__ = "1.0.0"

from .api import router as trading_agents_router

__all__ = ["trading_agents_router"]
