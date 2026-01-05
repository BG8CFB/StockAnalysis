"""
LangGraph 工作流模块

基于 LangGraph 官方最佳实践实现的四阶段股票分析工作流。

官方文档: https://docs.langchain.com/oss/python/langgraph/
"""

# 状态定义
from .state import (
    TradingAgentInputState,
    TradingAgentState,
    TradingAgentOutputState,
    create_initial_state,
    TaskStatus,
    RecommendationType,
)

# 工作流图
from .graph import create_trading_agent_graph

# 执行器
from .executor import TradingAgentWorkflow, create_workflow_executor

# 适配器
from .adapter import get_langgraph_adapter, LangGraphWorkflowAdapter

# 集成函数
from .integration import execute_analysis_workflow_langgraph

__all__ = [
    # 状态
    "TradingAgentInputState",
    "TradingAgentState",
    "TradingAgentOutputState",
    "create_initial_state",
    "TaskStatus",
    "RecommendationType",
    # 工作流
    "create_trading_agent_graph",
    # 执行器
    "TradingAgentWorkflow",
    "create_workflow_executor",
    # 适配器
    "get_langgraph_adapter",
    "LangGraphWorkflowAdapter",
    # 集成
    "execute_analysis_workflow_langgraph",
]
