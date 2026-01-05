"""
LangGraph 工作流图定义

遵循 LangGraph 官方最佳实践：
- 使用 StateGraph 定义图
- 使用 add_node 添加节点
- 使用 add_edge 添加普通边
- 使用 add_conditional_edges 添加条件边
- 使用 compile 编译图并配置 checkpointer

官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/
"""

import logging
from typing import Literal, Dict, Any, Optional
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.redis import RedisSaver
    REDIS_CHECKPOINTER_AVAILABLE = True
except ImportError:
    REDIS_CHECKPOINTER_AVAILABLE = False

from .state import (
    TradingAgentState,
    TradingAgentInputState,
    TradingAgentOutputState,
    TaskStatus
)
from .nodes import (
    # Phase 1
    technical_analyst_node,
    fundamental_analyst_node,
    sentiment_analyst_node,
    news_analyst_node,
    # Phase 2
    bull_debater_node,
    bear_debater_node,
    research_manager_node,
    trade_planner_node,
    # Phase 3
    aggressive_risk_analyst_node,
    conservative_risk_analyst_node,
    neutral_risk_analyst_node,
    chief_risk_officer_node,
    # Phase 4
    final_summarizer_node
)

logger = logging.getLogger(__name__)


# =============================================================================
# 路由函数（官方模式：基于状态决定下一个节点）
# =============================================================================

def should_continue_debate(state: TradingAgentState) -> Literal["continue_debate", "end_debate"]:
    """
    判断是否继续辩论

    遵循官方最佳实践：
    - 路由函数接收 state
    - 返回下一个节点的名称（字符串）

    Args:
        state: 当前工作流状态

    Returns:
        "continue_debate": 继续辩论
        "end_debate": 结束辩论
    """
    max_rounds = state.get("max_debate_rounds", 2)
    current_round = len(state.get("debate_turns", []))

    logger.debug(f"[辩论路由] 当前轮次: {current_round}, 最大轮次: {max_rounds}")

    if current_round >= max_rounds:
        return "end_debate"

    # 可选：检查是否收敛
    # if has_debate_converged(state["debate_turns"]):
    #     return "end_debate"

    return "continue_debate"


def route_debate_turn(state: TradingAgentState) -> Literal["bull", "bear"]:
    """
    路由到看涨或看跌辩手

    基于轮次交替执行

    Args:
        state: 当前工作流状态

    Returns:
        "bull": 看涨辩手
        "bear": 看跌辩手
    """
    current_round = len(state.get("debate_turns", []))

    logger.debug(f"[辩论轮次路由] 当前轮次: {current_round}")

    # 偶数轮：看涨先发言，奇数轮：看跌先发言
    if current_round % 2 == 0:
        return "bull"
    else:
        return "bear"


def should_execute_phase1(state: TradingAgentState) -> Literal["execute_phase1", "skip_phase1"]:
    """判断是否执行 Phase 1"""
    if state.get("enable_phase1", True):
        return "execute_phase1"
    return "skip_phase1"


def should_execute_phase2(state: TradingAgentState) -> Literal["execute_phase2", "skip_phase2"]:
    """判断是否执行 Phase 2"""
    if state.get("enable_phase2", True):
        return "execute_phase2"
    return "skip_phase2"


def should_execute_phase3(state: TradingAgentState) -> Literal["execute_phase3", "skip_phase3"]:
    """判断是否执行 Phase 3"""
    if state.get("enable_phase3", True):
        return "execute_phase3"
    return "skip_phase3"


def should_execute_phase4(state: TradingAgentState) -> Literal["execute_phase4", "skip_phase4"]:
    """判断是否执行 Phase 4"""
    if state.get("enable_phase4", True):
        return "execute_phase4"
    return "skip_phase4"


def check_phase1_completion(state: TradingAgentState) -> Literal["phase1_complete", "phase1_incomplete"]:
    """
    检查 Phase 1 是否完成

    遵循官方最佳实践：使用路由函数检查条件

    Args:
        state: 当前工作流状态

    Returns:
        "phase1_complete": Phase 1 完成
        "phase1_incomplete": Phase 1 未完成
    """
    expected = state.get("expected_analysts", 4)
    completed = state.get("completed_analysts", 0)

    logger.debug(f"[Phase 1 完成检查] 预期: {expected}, 已完成: {completed}")

    if completed >= expected:
        return "phase1_complete"
    return "phase1_incomplete"


def check_phase3_completion(state: TradingAgentState) -> Literal["phase3_complete", "phase3_incomplete"]:
    """
    检查 Phase 3 是否完成

    Args:
        state: 当前工作流状态

    Returns:
        "phase3_complete": Phase 3 完成
        "phase3_incomplete": Phase 3 未完成
    """
    expected = 3  # 激进、保守、中性三派
    completed = len(state.get("risk_assessments", []))

    logger.debug(f"[Phase 3 完成检查] 预期: {expected}, 已完成: {completed}")

    if completed >= expected:
        return "phase3_complete"
    return "phase3_incomplete"


# =============================================================================
# 工作流图构建
# =============================================================================

def create_trading_agent_graph(
    checkpointer_path: str = "data/trading_agents_checkpoints.db",
    use_redis_checkpointer: bool = True
) -> StateGraph:
    """
    创建 TradingAgents 工作流图

    完全遵循 LangGraph 官方最佳实践：
    1. 使用 StateGraph 定义图（支持多 schema）
    2. 使用 add_node 添加节点
    3. 使用 add_edge 添加普通边（确定性的转换）
    4. 使用 add_conditional_edges 添加条件边（基于状态的路由）
    5. 使用 compile 编译并指定 checkpointer（持久化）

    官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#compiling-your-graph

    Args:
        checkpointer_path: 检查点数据库路径（未使用，保留兼容性）
        use_redis_checkpointer: 是否使用 Redis checkpointer（默认 True）

    Returns:
        编译后的 StateGraph
    """
    logger.info("[工作流图] 开始构建 TradingAgents 工作流图")

    # 创建检查点保存器（优先使用 Redis）
    if use_redis_checkpointer and REDIS_CHECKPOINTER_AVAILABLE:
        try:
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            checkpointer = RedisSaver.from_conn_string(redis_url)
            logger.info(f"[工作流图] 使用 Redis checkpointer: {redis_url}")
        except Exception as e:
            logger.warning(f"[工作流图] Redis checkpointer 初始化失败: {e}，回退到 MemorySaver")
            checkpointer = MemorySaver()
    else:
        if not REDIS_CHECKPOINTER_AVAILABLE:
            logger.warning("[工作流图] RedisSaver 不可用，使用 MemorySaver")
        else:
            logger.info("[工作流图] 使用 MemorySaver")
        checkpointer = MemorySaver()

    # 创建图（指定多 schema）
    # 官方模式：使用 input_schema 和 output_schema 定义接口
    builder = StateGraph(
        TradingAgentState,
        input_schema=TradingAgentInputState,
        output_schema=TradingAgentOutputState
    )

    # ===== 添加所有节点 =====
    # 官方模式：使用 add_node(name, func)
    logger.info("[工作流图] 添加节点")

    # Phase 1: 分析师（并行执行）
    builder.add_node("technical_analyst", technical_analyst_node)
    builder.add_node("fundamental_analyst", fundamental_analyst_node)
    builder.add_node("sentiment_analyst", sentiment_analyst_node)
    builder.add_node("news_analyst", news_analyst_node)

    # Phase 2: 辩论
    builder.add_node("bull_debater", bull_debater_node)
    builder.add_node("bear_debater", bear_debater_node)
    builder.add_node("research_manager", research_manager_node)
    builder.add_node("trade_planner", trade_planner_node)

    # Phase 3: 风险评估（并行执行）
    builder.add_node("aggressive_risk_analyst", aggressive_risk_analyst_node)
    builder.add_node("conservative_risk_analyst", conservative_risk_analyst_node)
    builder.add_node("neutral_risk_analyst", neutral_risk_analyst_node)
    builder.add_node("chief_risk_officer", chief_risk_officer_node)

    # Phase 4: 总结
    builder.add_node("final_summarizer", final_summarizer_node)

    # ===== 定义边（Edges） =====
    # 官方模式：
    # - add_edge(from_node, to_node): 普通边（确定性转换）
    # - add_conditional_edges(node, routing_func, {condition: node}): 条件边

    logger.info("[工作流图] 定义边")

    # ===== Phase 1: 并行分析师 =====
    # 官方模式：从 START 连接到多个节点实现并行执行
    # 参考: https://docs.langchain.com/oss/python/langgraph/graph-api/#edges
    builder.add_edge(START, "technical_analyst")
    builder.add_edge(START, "fundamental_analyst")
    builder.add_edge(START, "sentiment_analyst")
    builder.add_edge(START, "news_analyst")

    # Phase 1 完成检查 -> Phase 2
    # 使用条件边检查是否所有分析师都完成
    builder.add_conditional_edges(
        "technical_analyst",
        check_phase1_completion,
        {
            "phase1_complete": "bull_debater",  # 进入 Phase 2
            "phase1_incomplete": "technical_analyst"  # 继续等待（实际不会再次执行）
        }
    )
    # 对其他分析师也添加相同的检查...
    builder.add_conditional_edges(
        "fundamental_analyst",
        check_phase1_completion,
        {
            "phase1_complete": "bull_debater",
            "phase1_incomplete": "fundamental_analyst"
        }
    )
    builder.add_conditional_edges(
        "sentiment_analyst",
        check_phase1_completion,
        {
            "phase1_complete": "bull_debater",
            "phase1_incomplete": "sentiment_analyst"
        }
    )
    builder.add_conditional_edges(
        "news_analyst",
        check_phase1_completion,
        {
            "phase1_complete": "bull_debater",
            "phase1_incomplete": "news_analyst"
        }
    )

    # ===== Phase 2: 辩论循环 =====
    # 官方模式：使用条件边实现循环
    # 参考: https://docs.langchain.com/oss/python/langgraph/tutorials/#loops

    # 看涨 -> 看跌（循环）
    builder.add_conditional_edges(
        "bull_debater",
        should_continue_debate,
        {
            "continue_debate": "bear_debater",  # 继续辩论
            "end_debate": "research_manager"  # 结束辩论，进入研究经理
        }
    )

    # 看跌 -> 看涨（循环）
    builder.add_conditional_edges(
        "bear_debater",
        should_continue_debate,
        {
            "continue_debate": "bull_debater",
            "end_debate": "research_manager"
        }
    )

    # Phase 2 流程：研究经理 -> 交易计划 -> Phase 3
    builder.add_edge("research_manager", "trade_planner")

    # ===== Phase 2 -> Phase 3 =====
    # 交易计划完成后，进入 Phase 3
    builder.add_conditional_edges(
        "trade_planner",
        should_execute_phase3,
        {
            "execute_phase3": "aggressive_risk_analyst",  # 执行 Phase 3
            "skip_phase3": "final_summarizer"  # 跳过 Phase 3
        }
    )

    # ===== Phase 3: 并行风险评估 =====
    # 交易计划 -> 三派并行
    builder.add_edge("trade_planner", "conservative_risk_analyst")
    builder.add_edge("trade_planner", "neutral_risk_analyst")

    # Phase 3 完成检查 -> CRO
    builder.add_conditional_edges(
        "aggressive_risk_analyst",
        check_phase3_completion,
        {
            "phase3_complete": "chief_risk_officer",
            "phase3_incomplete": "aggressive_risk_analyst"
        }
    )
    builder.add_conditional_edges(
        "conservative_risk_analyst",
        check_phase3_completion,
        {
            "phase3_complete": "chief_risk_officer",
            "phase3_incomplete": "conservative_risk_analyst"
        }
    )
    builder.add_conditional_edges(
        "neutral_risk_analyst",
        check_phase3_completion,
        {
            "phase3_complete": "chief_risk_officer",
            "phase3_incomplete": "neutral_risk_analyst"
        }
    )

    # ===== Phase 3 -> Phase 4 =====
    builder.add_edge("chief_risk_officer", "final_summarizer")

    # ===== Phase 4 -> END =====
    builder.add_edge("final_summarizer", END)

    # ===== 编译图（官方模式） =====
    # 官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#compiling-your-graph
    logger.info("[工作流图] 编译图（配置 checkpointer）")

    graph = builder.compile(
        checkpointer=checkpointer,  # 持久化
        debug=False,  # 生产环境关闭 debug
    )

    logger.info("[工作流图] 工作流图构建完成")

    return graph


# =============================================================================
# 工具函数
# =============================================================================

def visualize_graph(graph: StateGraph, output_path: str = "data/workflow_graph.png"):
    """
    可视化工作流图

    Args:
        graph: StateGraph 实例
        output_path: 输出图片路径
    """
    try:
        from IPython.display import Image, display

        # 生成图的可视化
        img = graph.get_graph().draw_mermaid_png()

        # 保存到文件
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img)

        logger.info(f"[工作流图] 图可视化已保存到: {output_path}")

    except Exception as e:
        logger.warning(f"[工作流图] 无法生成可视化: {e}")
