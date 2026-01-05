"""
LangGraph 工作流图定义

遵循 LangGraph 官方最佳实践：
- 使用 StateGraph 定义图
- 使用 add_node 添加节点
- 使用 add_edge 添加普通边
- 使用 add_conditional_edges 添加条件边
- 使用 compile 编译图并配置 checkpointer

官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/

**重要设计原则**：
- Phase 1 节点完全动态化，从用户配置动态创建
- Phase 2, 3, 4 节点结构固定，但提示词从配置加载
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
from modules.trading_agents.schemas import UserAgentConfigResponse
from .nodes import (
    # 节点工厂函数（Phase 1 动态创建）
    create_phase1_node_factory,
    # Phase 2（结构固定）
    bull_debater_node,
    bear_debater_node,
    research_manager_node,
    trade_planner_node,
    # Phase 3（结构固定）
    aggressive_risk_analyst_node,
    conservative_risk_analyst_node,
    neutral_risk_analyst_node,
    chief_risk_officer_node,
    # Phase 4（结构固定）
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


def phase1_checkpoint_node(state: TradingAgentState) -> Dict[str, Any]:
    """
    Phase 1 汇聚节点（用于等待所有并行分析师完成）

    这个节点本身不做任何工作，只是作为一个汇聚点，
    所有 Phase 1 分析师节点完成后都会路由到这里。
    """
    logger.debug(f"[Phase 1 检查点] 已完成分析师: {state.get('completed_analysts', 0)}")
    return {}  # 不修改状态


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
    use_redis_checkpointer: bool = True,
    agent_config: Optional[UserAgentConfigResponse] = None
) -> StateGraph:
    """
    创建 TradingAgents 工作流图

    完全遵循 LangGraph 官方最佳实践：
    1. 使用 StateGraph 定义图（支持多 schema）
    2. 使用 add_node 添加节点
    3. 使用 add_edge 添加普通边（确定性的转换）
    4. 使用 add_conditional_edges 添加条件边（基于状态的路由）
    5. 使用 compile 编译并指定 checkpointer（持久化）

    **重要特性**：
    - Phase 1 节点完全动态化，从 agent_config 动态创建
    - 支持用户自定义 Phase 1 智能体（添加/删除/修改）
    - Phase 2, 3, 4 结构固定但提示词可配置

    官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#compiling-your-graph

    Args:
        checkpointer_path: 检查点数据库路径（未使用，保留兼容性）
        use_redis_checkpointer: 是否使用 Redis checkpointer（默认 True）
        agent_config: 智能体配置（从 AgentConfigService 加载）

    Returns:
        编译后的 StateGraph
    """
    logger.info("[工作流图] 开始构建 TradingAgents 工作流图")

    # 加载默认配置（如果未提供）
    if agent_config is None:
        from modules.trading_agents.config.loader import load_default_config
        agent_config = load_default_config()
        logger.info("[工作流图] 使用默认智能体配置")

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

    # ===== 添加 Phase 1: 动态分析师节点 =====
    # **核心修改**: 完全动态化，不再有任何硬编码
    # agent_config 是 Pydantic 对象，不是字典
    phase1_agents = agent_config.phase1.agents if agent_config.phase1 else []

    # 过滤启用的智能体
    enabled_phase1_agents = [agent for agent in phase1_agents if agent.enabled]

    logger.info(f"[工作流图] 动态创建 Phase 1 节点: {len(enabled_phase1_agents)} 个分析师")

    phase1_node_names = []  # 记录节点名称，用于后续连接边

    for agent in enabled_phase1_agents:
        # agent 是 Pydantic 对象，不是字典
        agent_slug = agent.slug
        agent_name = agent.name
        role_definition = agent.role_definition or ""
        enabled_mcp_servers = agent.enabled_mcp_servers or []
        enabled_local_tools = agent.enabled_local_tools or []

        # 使用工厂函数动态创建节点
        node_func = create_phase1_node_factory(
            agent_slug=agent_slug,
            agent_name=agent_name,
            role_definition=role_definition,
            enabled_mcp_servers=enabled_mcp_servers,
            enabled_local_tools=enabled_local_tools
        )

        # 动态添加节点到图
        builder.add_node(agent_slug, node_func)
        phase1_node_names.append(agent_slug)

        logger.info(f"[工作流图] 添加 Phase 1 节点: {agent_slug} ({agent_name})")

    # ===== 添加 Phase 2, 3, 4: 固定结构节点 =====
    logger.info("[工作流图] 添加 Phase 2, 3, 4 节点")

    # Phase 2: 辩论
    builder.add_node("bull_debater", bull_debater_node)
    builder.add_node("bear_debater", bear_debater_node)
    builder.add_node("research_manager", research_manager_node)
    builder.add_node("trade_planner", trade_planner_node)

    # Phase 3: 风险评估
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

    # ===== Phase 1: 动态并行分析师 =====
    # 官方模式：从 START 连接到所有 Phase 1 节点实现并行执行
    # 参考: https://docs.langchain.com/oss/python/langgraph/graph-api/#edges

    # 添加 Phase 1 汇聚节点
    builder.add_node("phase1_checkpoint", phase1_checkpoint_node)

    for node_name in phase1_node_names:
        builder.add_edge(START, node_name)
        logger.debug(f"[工作流图] 连接 START -> {node_name}")

    # 所有 Phase 1 节点完成后路由到汇聚节点
    for node_name in phase1_node_names:
        builder.add_edge(node_name, "phase1_checkpoint")
        logger.debug(f"[工作流图] 连接 {node_name} -> phase1_checkpoint")

    # 汇聚节点检查是否所有分析师都完成
    builder.add_conditional_edges(
        "phase1_checkpoint",
        check_phase1_completion,
        {
            "phase1_complete": "bull_debater",  # 进入 Phase 2
            "phase1_incomplete": END  # 等待其他节点完成（LangGraph 会自动等待所有并行路径）
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

    logger.info(f"[工作流图] 工作流图构建完成，Phase 1 包含 {len(phase1_node_names)} 个动态分析师")

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
