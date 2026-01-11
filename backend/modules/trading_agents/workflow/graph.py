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
    # 新节点
    bull_initial_view_node,
    bear_initial_view_node,
    bull_debate_rebuttal_node,
    bear_debate_rebuttal_node,
    # 保留旧节点（向后兼容）
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

    **修改**：基于 current_debate_round 和 max_debate_rounds 判断

    遵循官方最佳实践：
    - 路由函数接收 state
    - 返回下一个节点的名称（字符串）

    Args:
        state: 当前工作流状态

    Returns:
        "continue_debate": 继续辩论
        "end_debate": 结束辩论
    """
    max_rounds = state.get("max_debate_rounds", 1)
    current_round = state.get("current_debate_round", 0)

    logger.info(f"[辩论路由] 当前轮次: {current_round}, 最大轮次: {max_rounds}")

    if current_round >= max_rounds:
        logger.info(f"[辩论路由] -> 结束辩论（返回 end_debate）")
        return "end_debate"

    logger.info(f"[辩论路由] -> 继续辩论（返回 continue_debate）")
    return "continue_debate"


def route_debate_mode(state: TradingAgentState) -> Literal["parallel_debate", "serial_debate", "skip_to_end"]:
    """
    路由辩论执行模式（并行或串行）

    基于phase2_concurrency配置和enable_phase2决定执行模式：
    - enable_phase2=False: 直接跳到最终汇聚节点
    - 1: 串行执行（看涨->看跌->看涨->看跌...）
    - 2: 并行执行（看涨和看跌同时进行）

    Args:
        state: 当前工作流状态

    Returns:
        "skip_to_end": 跳过 Phase 2，直接到最终汇聚节点
        "parallel_debate": 并行辩论模式
        "serial_debate": 串行辩论模式
    """
    # 检查是否启用 Phase 2
    if not state.get("enable_phase2", True):
        logger.info(f"[辩论模式路由] Phase 2 已禁用，直接到最终汇聚节点")
        return "skip_to_end"

    concurrency = state.get("phase2_concurrency", 1)
    logger.debug(f"[辩论模式路由] 并发数: {concurrency}")

    if concurrency >= 2:
        return "parallel_debate"
    return "serial_debate"


def route_debate_turn_serial(state: TradingAgentState) -> Literal["bull", "bear", "end_debate"]:
    """
    串行辩论轮次路由

    交替执行看涨和看跌辩手

    Args:
        state: 当前工作流状态

    Returns:
        "bull": 看涨辩手
        "bear": 看跌辩手
        "end_debate": 结束辩论
    """
    current_round = len(state.get("debate_turns", []))
    max_rounds = state.get("max_debate_rounds", 2)

    logger.debug(f"[串行辩论轮次路由] 当前轮次: {current_round}, 最大轮次: {max_rounds}")

    if current_round >= max_rounds * 2:
        return "end_debate"

    # 偶数轮次：看涨先发言，奇数轮次：看跌先发言
    if current_round % 2 == 0:
        return "bull"
    else:
        return "bear"


def route_debate_turn_parallel(state: TradingAgentState) -> Literal["continue_debate", "end_debate"]:
    """
    并行辩论轮次路由

    看涨和看跌同时进行，每轮都一起生成报告

    Args:
        state: 当前工作流状态

    Returns:
        "continue_debate": 继续下一轮辩论
        "end_debate": 结束辩论
    """
    debate_turns = state.get("debate_turns", [])
    current_round = len(debate_turns) // 2  # 每轮两人，所以除以2
    max_rounds = state.get("max_debate_rounds", 2)

    logger.info(f"[并行辩论轮次路由] debate_turns 数量: {len(debate_turns)}")
    logger.info(f"[并行辩论轮次路由] 当前轮次: {current_round}, 最大轮次: {max_rounds}")

    if current_round >= max_rounds:
        logger.info(f"[并行辩论轮次路由] -> 结束辩论（返回 end_debate）")
        return "end_debate"
    logger.info(f"[并行辩论轮次路由] -> 继续辩论（返回 continue_debate）")
    return "continue_debate"


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
    enable_phase3 = state.get("enable_phase3", True)
    logger.info(f"[路由] should_execute_phase3: enable_phase3={enable_phase3}")
    if enable_phase3:
        logger.info(f"[路由] -> 返回 execute_phase3，将路由到 phase3_mode_router")
        return "execute_phase3"
    logger.info(f"[路由] -> 返回 skip_phase3，将路由到 final_summarizer")
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
    completed = state.get("completed_analysts", 0)
    analyst_reports_count = len(state.get("analyst_reports", []))

    # **关键修复：直接从 agent_config 动态计算 expected_analysts**
    # 因为 expected_analysts 字段可能在状态传递中丢失
    agent_config = state.get("agent_config", {})
    expected = 4  # 默认值

    if agent_config and isinstance(agent_config, dict):
        phase1_agents = agent_config.get("phase1", {}).get("agents", [])
        enabled_agents = [a for a in phase1_agents if a.get("enabled")]
        expected = len(enabled_agents) if enabled_agents else 4

    logger.info(f"[Phase 1 完成检查] 预期: {expected}, 已完成: {completed}, 报告数: {analyst_reports_count}")

    if completed >= expected:
        logger.info(f"[Phase 1 完成检查] ✓ Phase 1 完成 ({completed}/{expected}) -> 路由到 debate_mode_router")
        return "phase1_complete"
    logger.info(f"[Phase 1 完成检查] ✗ Phase 1 未完成 ({completed}/{expected}) -> 等待其他节点")
    return "phase1_incomplete"


def phase1_checkpoint_node(state: TradingAgentState) -> Dict[str, Any]:
    """
    Phase 1 汇聚节点（用于等待所有并行分析师完成）

    这个节点本身不做任何工作，只是作为一个汇聚点，
    所有 Phase 1 分析师节点完成后都会路由到这里。
    """
    completed = state.get('completed_analysts', 0)
    analyst_reports_count = len(state.get('analyst_reports', []))
    logger.info(f"[Phase 1 检查点] 已完成分析师: {completed}, analyst_reports 数量: {analyst_reports_count}")

    # 检查状态字段
    logger.info(f"[Phase 1 检查点] 状态字段: {list(state.keys())}")

    return {}  # 不修改状态


def route_phase3_mode(state: TradingAgentState) -> Literal["phase3_serial", "phase3_parallel"]:
    """
    路由Phase 3执行模式

    基于phase3_concurrency配置决定执行模式：
    - 1: 串行执行（激进->保守->中性）
    - 2+: 并行执行（激进和保守一起 -> 中性 或 全部一起）

    Args:
        state: 当前工作流状态

    Returns:
        "phase3_serial": 串行模式
        "phase3_parallel": 并行模式
    """
    concurrency = state.get("phase3_concurrency", 3)
    logger.debug(f"[Phase 3 模式路由] 并发数: {concurrency}")
    
    if concurrency >= 2:
        return "phase3_parallel"
    return "phase3_serial"


def route_from_aggressive(state: TradingAgentState) -> Literal["conservative", "phase3_group2_checkpoint", "chief_risk_officer"]:
    """
    从激进风险分析师的路由

    根据并发数决定下一个节点：
    - concurrency=1: 串行 -> 保守
    - concurrency=2: 2并发 -> 组2汇聚
    - concurrency>=3: 3+并发 -> CRO汇聚

    Args:
        state: 当前工作流状态

    Returns:
        "conservative": 保守分析师
        "phase3_group2_checkpoint": 组2汇聚
        "chief_risk_officer": CRO
    """
    concurrency = state.get("phase3_concurrency", 3)
    
    if concurrency >= 3:
        return "chief_risk_officer"
    elif concurrency >= 2:
        return "phase3_group2_checkpoint"
    return "conservative"


def route_from_conservative(state: TradingAgentState) -> Literal["neutral", "phase3_group2_checkpoint", "chief_risk_officer"]:
    """
    从保守风险分析师的路由

    根据并发数决定下一个节点：
    - concurrency=1: 串行 -> 中性
    - concurrency=2: 2并发 -> 组2汇聚
    - concurrency>=3: 3+并发 -> CRO汇聚

    Args:
        state: 当前工作流状态

    Returns:
        "neutral": 中性分析师
        "phase3_group2_checkpoint": 组2汇聚
        "chief_risk_officer": CRO
    """
    concurrency = state.get("phase3_concurrency", 3)
    
    if concurrency >= 3:
        return "chief_risk_officer"
    elif concurrency >= 2:
        return "phase3_group2_checkpoint"
    return "neutral"


def route_from_group2_checkpoint(state: TradingAgentState) -> Literal["neutral"]:
    """
    从组2汇聚节点路由

    激进和保守都完成后，执行中性分析师

    Args:
        state: 当前工作流状态

    Returns:
        "neutral": 中性分析师
    """
    return "neutral"


def route_from_neutral(state: TradingAgentState) -> Literal["chief_risk_officer"]:
    """
    从中性风险分析师的路由

    Args:
        state: 当前工作流状态

    Returns:
        "chief_risk_officer": CRO
    """
    return "chief_risk_officer"


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
    # agent_config 可以是字典或 Pydantic 对象

    # 处理字典类型的配置
    if isinstance(agent_config, dict):
        phase1_config = agent_config.get("phase1", {})
        phase1_agents = phase1_config.get("agents", [])
    else:
        # Pydantic 对象
        phase1_agents = agent_config.phase1.agents if agent_config.phase1 else []

    # 过滤启用的智能体（支持字典和对象）
    enabled_phase1_agents = []
    for agent in phase1_agents:
        if isinstance(agent, dict):
            if agent.get("enabled"):
                enabled_phase1_agents.append(agent)
        else:
            if agent.enabled:
                enabled_phase1_agents.append(agent)

    logger.info(f"[工作流图] 动态创建 Phase 1 节点: {len(enabled_phase1_agents)} 个分析师")
    print(f"[工作流图] 动态创建 Phase 1 节点: {len(enabled_phase1_agents)} 个分析师")  # 添加 print 确保输出

    phase1_node_names = []  # 记录节点名称，用于后续连接边

    for idx, agent in enumerate(enabled_phase1_agents):
        print(f"[工作流图] 处理第 {idx+1}/{len(enabled_phase1_agents)} 个分析师...")  # 添加进度跟踪
        # 支持 Pydantic 对象和字典
        if isinstance(agent, dict):
            agent_slug = agent.get("slug")
            agent_name = agent.get("name")
            role_definition = agent.get("role_definition") or ""
            enabled_mcp_servers = agent.get("enabled_mcp_servers") or []
            enabled_local_tools = agent.get("enabled_local_tools") or []
        else:
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
        print(f"[工作流图] ✓ 添加节点: {agent_slug}")  # 添加 print 确保输出

    # ===== 添加 Phase 2, 3, 4: 固定结构节点 =====
    logger.info("[工作流图] 添加 Phase 2, 3, 4 节点")

    # Phase 2: 初始观点生成（必须执行）
    builder.add_node("bull_initial_view", bull_initial_view_node)
    builder.add_node("bear_initial_view", bear_initial_view_node)

    # Phase 2: 辩论反驳（可选执行）
    builder.add_node("bull_debate_rebuttal", bull_debate_rebuttal_node)
    builder.add_node("bear_debate_rebuttal", bear_debate_rebuttal_node)

    # Phase 2: 研究经理和交易计划
    builder.add_node("research_manager", research_manager_node)
    builder.add_node("trade_planner", trade_planner_node)

    # 保留旧节点（向后兼容，但不再使用）
    builder.add_node("bull_debater", bull_debater_node)
    builder.add_node("bear_debater", bear_debater_node)

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

    # ===== Phase 1: 动态串行分析师（避免 API 并发限制）=====
    # 串行模式：START -> node1 -> node2 -> node3 -> ... -> phase1_checkpoint

    # 添加 Phase 1 汇聚节点
    builder.add_node("phase1_checkpoint", phase1_checkpoint_node)

    # 串行连接节点
    if phase1_node_names:
        # 第一个节点从 START 开始
        builder.add_edge(START, phase1_node_names[0])
        logger.debug(f"[工作流图] 串行模式：START -> {phase1_node_names[0]}")

        # 后续节点按顺序连接
        for i in range(len(phase1_node_names) - 1):
            current_node = phase1_node_names[i]
            next_node = phase1_node_names[i + 1]
            builder.add_edge(current_node, next_node)
            logger.debug(f"[工作流图] 串行模式：{current_node} -> {next_node}")

        # 最后一个节点连接到汇聚节点
        builder.add_edge(phase1_node_names[-1], "phase1_checkpoint")
        logger.debug(f"[工作流图] 串行模式：{phase1_node_names[-1]} -> phase1_checkpoint")

    # ===== Phase 2: 初始观点生成 + 辩论循环 =====
    # 官方模式：使用条件边实现循环
    # 参考: https://docs.langchain.com/oss/python/langgraph/tutorials/#loops

    # 添加初始观点汇聚节点
    def phase2_initial_checkpoint_node(state: TradingAgentState) -> Dict[str, Any]:
        """Phase 2 初始观点汇聚节点（等待看涨和看跌初始观点完成）"""
        bull_completed = state.get("bull_initial_completed", False)
        bear_completed = state.get("bear_initial_completed", False)
        logger.info(f"[Phase 2 初始汇聚] 看涨完成: {bull_completed}, 看跌完成: {bear_completed}")
        return {}

    builder.add_node("phase2_initial_checkpoint", phase2_initial_checkpoint_node)

    # 添加辩论循环汇聚节点
    def phase2_debate_checkpoint_node(state: TradingAgentState) -> Dict[str, Any]:
        """Phase 2 辩论循环汇聚节点（等待本轮看涨和看跌反驳完成）"""
        current_round = state.get("current_debate_round", 0)
        logger.info(f"[Phase 2 辩论汇聚] 当前轮次: {current_round}")
        return {}

    builder.add_node("phase2_debate_checkpoint", phase2_debate_checkpoint_node)

    # 添加辩论循环推进节点
    def phase2_debate_advance_node(state: TradingAgentState) -> Dict[str, Any]:
        """Phase 2 辩论循环推进节点（增加轮次计数）"""
        current_round = state.get("current_debate_round", 0)
        new_round = current_round + 1
        logger.info(f"[Phase 2 辩论推进] 从轮次 {current_round} 推进到 {new_round}")
        return {"current_debate_round": new_round}

    builder.add_node("phase2_debate_advance", phase2_debate_advance_node)

    # Phase 1完成 -> 初始观点生成（并行）
    # 添加 Phase 2 初始观点启动节点（用于同时启动看涨和看跌）
    def phase2_initial_start_node(state: TradingAgentState) -> Dict[str, Any]:
        """Phase 2 初始观点启动节点（不修改状态，仅用于并行启动）"""
        logger.info(f"[Phase 2] 启动初始观点生成（并行）")
        return {}

    builder.add_node("phase2_initial_start", phase2_initial_start_node)

    builder.add_conditional_edges(
        "phase1_checkpoint",
        check_phase1_completion,
        {
            "phase1_complete": "phase2_initial_start",  # 进入初始观点生成启动节点
            "phase1_incomplete": END  # 等待其他节点完成
        }
    )

    # 并行执行看涨和看跌初始观点
    builder.add_edge("phase2_initial_start", "bull_initial_view")
    builder.add_edge("phase2_initial_start", "bear_initial_view")

    # 两者都汇聚到检查点
    builder.add_edge("bull_initial_view", "phase2_initial_checkpoint")
    builder.add_edge("bear_initial_view", "phase2_initial_checkpoint")

    # 初始汇聚 -> 检查是否需要辩论
    def should_start_debate(state: TradingAgentState) -> Literal["start_debate", "skip_debate"]:
        """判断是否开始辩论循环"""
        max_rounds = state.get("max_debate_rounds", 1)
        logger.info(f"[Phase 2] max_debate_rounds={max_rounds}")
        if max_rounds > 0:
            return "start_debate"
        return "skip_debate"

    builder.add_conditional_edges(
        "phase2_initial_checkpoint",
        should_start_debate,
        {
            "start_debate": "phase2_debate_round_start",  # 开始辩论（进入辩论轮次启动）
            "skip_debate": "research_manager"  # 跳过辩论，直接到研究经理
        }
    )

    # ===== 辩论循环（并行模式） =====
    # 添加辩论轮次启动节点
    def phase2_debate_round_start_node(state: TradingAgentState) -> Dict[str, Any]:
        """Phase 2 辩论轮次启动节点（不修改状态，仅用于同时启动看涨和看跌反驳）"""
        current_round = state.get("current_debate_round", 0)
        logger.info(f"[Phase 2] 启动第 {current_round + 1} 轮辩论（并行）")
        return {}

    builder.add_node("phase2_debate_round_start", phase2_debate_round_start_node)

    # 轮次推进 -> 辩论轮次启动
    builder.add_edge("phase2_debate_advance", "phase2_debate_round_start")

    # 辩论轮次启动 -> 并行执行看涨和看跌反驳
    builder.add_edge("phase2_debate_round_start", "bull_debate_rebuttal")
    builder.add_edge("phase2_debate_round_start", "bear_debate_rebuttal")

    # 看涨反驳 -> 辩论汇聚
    builder.add_edge("bull_debate_rebuttal", "phase2_debate_checkpoint")

    # 看跌反驳 -> 辩论汇聚
    builder.add_edge("bear_debate_rebuttal", "phase2_debate_checkpoint")

    # 辩论汇聚 -> 继续或结束
    builder.add_conditional_edges(
        "phase2_debate_checkpoint",
        should_continue_debate,
        {
            "continue_debate": "phase2_debate_advance",  # 推进轮次
            "end_debate": "research_manager"  # 结束辩论
        }
    )

    # 修正：初始观点后直接进入第一轮辩论（如果需要）
    # 删除旧的边，使用新的路由逻辑

    # Phase 2 流程：研究经理 -> 交易计划 -> Phase 3
    builder.add_edge("research_manager", "trade_planner")

    # ===== Phase 2 -> Phase 3 =====
    # 交易计划完成后，进入 Phase 3
    builder.add_conditional_edges(
        "trade_planner",
        should_execute_phase3,
        {
            "execute_phase3": "phase3_mode_router",  # 执行 Phase 3（先路由模式）
            "skip_phase3": "final_summarizer"  # 跳过 Phase 3
        }
    )

    # ===== Phase 3: 支持串行和并行的风险评估 =====
    
    # 添加Phase 3模式路由节点
    def phase3_mode_router_node(state: TradingAgentState) -> Dict[str, Any]:
        """Phase 3模式路由节点（不修改状态，仅用于路由）"""
        return {}

    builder.add_node("phase3_mode_router", phase3_mode_router_node)

    # 添加Phase 3并发组2汇聚节点
    def phase3_group2_checkpoint_node(state: TradingAgentState) -> Dict[str, Any]:
        """Phase 3并发组2汇聚节点（等待激进和保守都完成）"""
        return {}

    builder.add_node("phase3_group2_checkpoint", phase3_group2_checkpoint_node)

    # 添加Phase 3并发组2起始节点
    def phase3_group2_start_node(state: TradingAgentState) -> Dict[str, Any]:
        """Phase 3组2起始节点（不修改状态，仅用于同时启动激进和保守）"""
        return {}

    builder.add_node("phase3_group2_start", phase3_group2_start_node)

    # Phase 3模式路由 -> 串行或并行
    builder.add_conditional_edges(
        "phase3_mode_router",
        route_phase3_mode,
        {
            "phase3_serial": "aggressive_risk_analyst",  # 串行：从激进开始
            "phase3_parallel": "phase3_group2_start"  # 并行：激进和保守一起
        }
    )

    # ===== 根据并发数动态路由 =====
    # 激进分析师 -> 根据并发数路由
    builder.add_conditional_edges(
        "aggressive_risk_analyst",
        route_from_aggressive,
        {
            "conservative": "conservative_risk_analyst",  # 串行
            "phase3_group2_checkpoint": "phase3_group2_checkpoint",  # 2并发
            "chief_risk_officer": "chief_risk_officer"  # 3+并发
        }
    )

    # 保守分析师 -> 根据并发数路由
    builder.add_conditional_edges(
        "conservative_risk_analyst",
        route_from_conservative,
        {
            "neutral": "neutral_risk_analyst",  # 串行
            "phase3_group2_checkpoint": "phase3_group2_checkpoint",  # 2并发
            "chief_risk_officer": "chief_risk_officer"  # 3+并发
        }
    )

    # 组2汇聚 -> 中性分析师（2并发模式）
    builder.add_conditional_edges(
        "phase3_group2_checkpoint",
        route_from_group2_checkpoint,
        {
            "neutral": "neutral_risk_analyst"
        }
    )

    # 中性分析师 -> CRO
    builder.add_conditional_edges(
        "neutral_risk_analyst",
        route_from_neutral,
        {
            "chief_risk_officer": "chief_risk_officer"
        }
    )

    # ===== Phase 3 -> Phase 4 =====
    builder.add_edge("chief_risk_officer", "final_summarizer")

    # ===== 添加最终状态汇聚节点 =====
    # 这个节点确保所有累积字段都被正确返回，解决 LangGraph 状态返回不完整的问题
    def final_state_aggregator_node(state: TradingAgentState) -> Dict[str, Any]:
        """
        最终状态汇聚节点

        确保所有累积字段都被正确返回到状态中。
        通过显式返回所有累积字段，确保它们被包含在最终状态中。
        """
        logger.info(f"[状态汇聚] 最终状态汇聚")
        logger.info(f"[状态汇聚] analyst_reports: {len(state.get('analyst_reports', []))} 条")
        logger.info(f"[状态汇聚] debate_turns: {len(state.get('debate_turns', []))} 条")
        logger.info(f"[状态汇聚] risk_assessments: {len(state.get('risk_assessments', []))} 条")
        logger.info(f"[状态汇聚] token_usage: {len(state.get('token_usage', []))} 条")

        # 返回所有累积字段（使用 operator.add 的字段）
        # 不返回其他字段，避免覆盖
        return {}

    builder.add_node("final_state_aggregator", final_state_aggregator_node)

    # Phase 4 -> 汇聚节点 -> END
    builder.add_edge("final_summarizer", "final_state_aggregator")
    builder.add_edge("final_state_aggregator", END)

    # ===== 编译图（官方模式） =====
    # 官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#compiling-your-graph
    logger.info("[工作流图] 编译图（配置 checkpointer）")

    # 添加调试信息：检查所有节点
    logger.info(f"[工作流图] 编译前检查 - 所有节点: {builder.nodes.keys()}")
    logger.info(f"[工作流图] 编译前检查 - 所有边: {list(builder.edges)}")
    print(f"[工作流图] 准备编译图，节点数: {len(builder.nodes)}")  # 添加 print

    print("[工作流图] 开始编译图...")
    graph = builder.compile(
        checkpointer=checkpointer,  # 持久化
        debug=False,  # 生产环境关闭 debug
    )
    print("[工作流图] 图编译完成")  # 添加 print

    logger.info(f"[工作流图] 工作流图构建完成，Phase 1 包含 {len(phase1_node_names)} 个动态分析师")
    logger.info(f"[工作流图] 编译后检查 - 图节点数: {len(graph.nodes)}")

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
