"""
LangGraph 节点函数

遵循 LangGraph 官方最佳实践：
- 节点是 Python 函数（sync 或 async）
- 接收 state 作为参数，可选接收 config 和 runtime
- 返回状态更新的字典（不是完整状态）
- 使用 operator.add reducer 自动累积状态

官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#nodes

**重要设计原则**：
- Phase 1 节点完全动态化，通过 create_phase1_node_factory 工厂函数创建
- Phase 2, 3, 4 节点结构固定，但提示词从配置加载
- 所有节点从配置文件加载 role_definition
- **AI 系统集成**: 使用项目核心 AIModelService，支持双模型配置
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from langchain_core.runnables import RunnableConfig

from .state import TradingAgentState, TaskStatus

logger = logging.getLogger(__name__)


# =============================================================================
# LLM Provider 缓存（进程级）
# =============================================================================

_llm_provider_cache: Dict[tuple, "LLMProvider"] = {}
"""LLM Provider 缓存，避免重复创建

缓存键: (user_id, model_id)
例如: ("user123", "glm-4.6")
"""


def clear_llm_cache():
    """清除所有 LLM Provider 缓存"""
    global _llm_provider_cache
    _llm_provider_cache.clear()
    logger.info("[LLM] 清除所有 LLM Provider 缓存")


async def _get_llm_for_agent(
    state: TradingAgentState,
    agent_slug: str,
    phase: str
) -> "LLMProvider":
    """
    获取智能体的 LLM Provider（集成项目核心 AI 系统）

    **重要改造**:
    - 使用 AIModelService 获取模型配置
    - 支持双模型配置（data_collection_model vs debate_model）
    - 实现 LLM Provider 缓存
    - 删除环境变量硬编码

    遵循官方最佳实践：
    - 异步函数，调用 AIModelService
    - 根据 phase 参数选择对应模型
    - 实现模型回退机制

    Args:
        state: 工作流状态
        agent_slug: 智能体标识符
        phase: 阶段标识（"phase1" 或 "phase2"）
            - phase1: 使用 data_collection_model
            - phase2: 使用 debate_model（Phase 2/3/4 共用）

    Returns:
        LLMProvider 实例

    Raises:
        ValueError: 无法获取有效的模型配置
    """
    from core.ai.llm.openai_compat import LLMProviderFactory
    from core.ai.model.service import get_model_service

    user_id = state.get("user_id")
    model_config = state.get("model_config", {})

    # ===== 1. 根据 phase 选择对应的 model_id =====
    if phase == "phase1":
        model_id = model_config.get("data_collection_model")
        logger.debug(f"[LLM] Phase 1 使用数据收集模型: {model_id}")
    else:  # phase2 (Phase 2/3/4)
        model_id = model_config.get("debate_model")
        logger.debug(f"[LLM] Phase {phase} 使用辩论模型: {model_id}")

    # ===== 2. 如果用户未指定模型，使用系统默认模型 =====
    if not model_id:
        logger.warning(f"[LLM] 用户未配置 {phase} 模型，尝试使用系统默认模型")
        model_service = get_model_service()
        default_model = await model_service.get_default_model(user_id)
        if not default_model:
            raise ValueError(
                f"无法获取模型配置: user_id={user_id}, phase={phase}. "
                f"请配置系统默认模型或在任务中指定模型。"
            )
        model_id = default_model.model_id
        logger.info(f"[LLM] 使用系统默认模型: {model_id}")

    # ===== 3. 检查缓存 =====
    cache_key = (user_id, model_id)
    if cache_key in _llm_provider_cache:
        logger.debug(f"[LLM] 缓存命中: model={model_id}, agent={agent_slug}")
        return _llm_provider_cache[cache_key]

    # ===== 4. 从 AIModelService 获取模型配置 =====
    logger.debug(f"[LLM] 从 AIModelService 获取模型配置: {model_id}")
    model_service = get_model_service()
    model_config_obj = await model_service.get_model(model_id, user_id)

    # ===== 5. 验证模型配置 =====
    if not model_config_obj:
        # 模型不存在，尝试回退到默认模型
        logger.warning(f"[LLM] 模型不存在: {model_id}，尝试回退到默认模型")
        default_model = await model_service.get_default_model(user_id)
        if not default_model:
            raise ValueError(f"无法获取模型配置: model_id={model_id}, 且无可用默认模型")
        model_config_obj = default_model
        model_id = default_model.model_id

    if not model_config_obj.enabled:
        raise ValueError(f"模型已禁用: model_id={model_id}, name={model_config_obj.name}")

    if not model_config_obj.api_key_valid:
        raise ValueError(
            f"模型 API Key 无效: model_id={model_id}, name={model_config_obj.name}. "
            f"请重新配置 API Key。"
        )

    # ===== 6. 创建 LLM Provider =====
    provider_type = model_config_obj.platform_name.value if model_config_obj.platform_name else "custom"

    llm = LLMProviderFactory.create_provider(
        provider_type=provider_type,
        api_base_url=model_config_obj.api_base_url,
        api_key=model_config_obj.api_key,  # 已解密
        model_id=model_config_obj.model_id,
        temperature=model_config_obj.temperature,
        timeout_seconds=model_config_obj.timeout_seconds,
    )

    logger.info(
        f"[LLM] 创建 LLM Provider: "
        f"model={model_config_obj.model_id} ({model_config_obj.name}), "
        f"provider={provider_type}, "
        f"phase={phase}, "
        f"agent={agent_slug}"
    )

    # ===== 7. 缓存 LLM Provider 实例 =====
    _llm_provider_cache[cache_key] = llm

    return llm


# =============================================================================
# 节点工厂函数（Phase 1 动态节点创建）
# =============================================================================

def create_phase1_node_factory(
    agent_slug: str,
    agent_name: str,
    role_definition: str,
    enabled_mcp_servers: list = None,
    enabled_local_tools: list = None
) -> Callable:
    """
    创建 Phase 1 分析师节点函数（工厂模式）

    这是核心函数，完全消除了 Phase 1 的硬编码问题。
    每个分析师节点都是根据配置动态生成的。

    遵循 LangGraph 官方最佳实践：
    - 节点是 async 函数
    - 接收 state 和可选的 config
    - 返回状态更新的字典

    Args:
        agent_slug: 智能体标识符（如 market_technical）
        agent_name: 智能体显示名称
        role_definition: 角色定义（提示词）
        enabled_mcp_servers: 启用的 MCP 服务器列表
        enabled_local_tools: 启用的本地工具列表

    Returns:
        节点函数（async def node(state, config) -> Dict[str, Any]）

    Example:
        >>> technical_node = create_phase1_node_factory(
        ...     agent_slug="market_technical",
        ...     agent_name="市场技术分析师",
        ...     role_definition="你是一位专业的技术分析师..."
        ... )
        >>> # 在 graph.py 中使用：
        >>> builder.add_node("market_technical", technical_node)
    """
    enabled_mcp_servers = enabled_mcp_servers or []
    enabled_local_tools = enabled_local_tools or []

    async def phase1_analyst_node(
        state: TradingAgentState,
        config: RunnableConfig
    ) -> Dict[str, Any]:
        """
        Phase 1 分析师节点（动态生成）

        Args:
            state: 当前工作流状态
            config: 运行时配置

        Returns:
            状态更新字典（包含 analyst_reports, completed_analysts, token_usage）
        """
        logger.info(f"[{agent_name}] 开始分析股票: {state['stock_code']}")

        try:
            # 获取 LLM（使用数据收集模型）
            llm = await _get_llm_for_agent(state, agent_slug, phase="phase1")

            # 获取工具（基于 agent 配置）
            tools = _get_tools_for_agent(state, agent_slug, enabled_mcp_servers, enabled_local_tools)

            # 构建提示词（使用配置中的 role_definition）
            prompt = _build_phase1_prompt(
                agent_slug=agent_slug,
                agent_name=agent_name,
                role_definition=role_definition,
                state=state
            )

            # 调用 LLM
            from core.ai.llm.provider import Message
            messages = [
                Message(role="system", content=f"你是{agent_name}。"),
                Message(role="user", content=prompt)
            ]

            # 如果有工具，使用带工具的 LLM
            if tools:
                result = await llm.generate_with_tools(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"  # LLM 自动决定是否使用工具
                )
                content = result.get("content", "")
                tool_calls_made = result.get("tool_calls", [])
            else:
                result = await llm.generate(messages=messages)
                content = result.get("content", "")
                tool_calls_made = []

            # 记录工具调用
            tool_call_records = []
            for tool_call in tool_calls_made:
                tool_call_records.append({
                    "agent": agent_slug,
                    "tool": tool_call.get("name", "unknown"),
                    "timestamp": datetime.now().isoformat()
                })

            # 记录 Token 消耗
            token_record = {
                "phase": "phase1",
                "agent": agent_slug,
                "prompt_tokens": result.get("prompt_tokens", 0),
                "completion_tokens": result.get("completion_tokens", 0),
                "total_tokens": result.get("total_tokens", 0),
                "timestamp": datetime.now().isoformat()
            }

            # 构建分析师报告（只传递最终报告，不传递中间过程）
            analyst_report = {
                "agent_slug": agent_slug,
                "agent_name": agent_name,
                "content": content,  # 最终报告内容
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"[{agent_name}] 分析完成，Token: {token_record['total_tokens']}")

            # 返回状态更新（使用累积器）
            return {
                "analyst_reports": [analyst_report],  # 列表会自动累积
                "completed_analysts": state.get("completed_analysts", 0) + 1,
                "token_usage": [token_record],  # 列表会自动累积
                "tool_calls": tool_call_records  # 列表会自动累积
            }

        except Exception as e:
            logger.error(f"[{agent_name}] 分析失败: {e}", exc_info=True)

            # 记录错误
            error_record = {
                "phase": "phase1",
                "agent": agent_slug,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

            return {
                "errors": [error_record],  # 列表会自动累积
                "completed_analysts": state.get("completed_analysts", 0) + 1  # 即使失败也计数
            }

    # 设置节点函数的元数据（便于调试）
    phase1_analyst_node.__name__ = f"{agent_slug}_node"
    phase1_analyst_node.__qualname__ = f"create_phase1_node_factory.{agent_slug}_node"

    return phase1_analyst_node


# =============================================================================
# 辅助函数
# =============================================================================
def _get_tools_for_agent(
    state: TradingAgentState,
    agent_slug: str,
    enabled_mcp_servers: list = None,
    enabled_local_tools: list = None
) -> list:
    """
    获取智能体的工具列表

    Args:
        state: 工作流状态
        agent_slug: 智能体标识符
        enabled_mcp_servers: 启用的 MCP 服务器列表
        enabled_local_tools: 启用的本地工具列表

    Returns:
        工具列表
    """
    # TODO: 从 ToolRegistry 获取实际工具
    # 暂时返回空列表
    enabled_mcp_servers = enabled_mcp_servers or []
    enabled_local_tools = enabled_local_tools or []

    logger.debug(f"[Tools] 获取工具列表: agent={agent_slug}, mcp_servers={len(enabled_mcp_servers)}, local_tools={len(enabled_local_tools)}")
    return []


def _build_phase1_prompt(
    agent_slug: str,
    agent_name: str,
    role_definition: str,
    state: TradingAgentState
) -> str:
    """
    构建 Phase 1 智能体的提示词

    **重要**: 使用配置中的 role_definition，不再硬编码。

    Args:
        agent_slug: 智能体标识符
        agent_name: 智能体显示名称
        role_definition: 角色定义（从配置文件加载）
        state: 工作流状态

    Returns:
        提示词字符串
    """
    # 基础信息
    base_info = f"""
## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}
- 任务 ID：{state['task_id']}
"""

    # 直接使用配置中的 role_definition
    # 不再有任何硬编码的提示词
    prompt = f"""{role_definition}

{base_info}

请严格按照你的角色定义，生成专业的分析报告（Markdown 格式）。
"""

    return prompt


def _build_debate_prompt(
    state: TradingAgentState,
    agent_type: str,  # "bull" or "bear"
    round_idx: int
) -> str:
    """
    构建辩论提示词

    Args:
        state: 工作流状态
        agent_type: 智能体类型（bull 或 bear）
        round_idx: 当前轮次

    Returns:
        提示词字符串
    """
    base_info = f"""
## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}
- 任务 ID：{state['task_id']}
"""

    # 添加分析师报告
    if state['analyst_reports']:
        base_info += "\n## 分析师报告摘要\n"
        for report in state['analyst_reports']:
            base_info += f"\n### {report.get('agent_name', '分析师')}\n"
            base_info += f"{report.get('content', '')}\n"

    # 添加对手观点（如果是反驳轮次）
    if round_idx > 0 and state['debate_turns']:
        last_turn = state['debate_turns'][-1]
        if agent_type == "bull":
            opponent_view = last_turn.get('bear_argument', '')
            role = "看跌研究员"
        else:
            opponent_view = last_turn.get('bull_argument', '')
            role = "看涨研究员"

        if opponent_view:
            base_info += f"""

## 对手观点（上一轮{role}的观点）

<opponent_view>
{opponent_view}
</opponent_view>

请针对以上观点进行反驳。
"""

    if agent_type == "bull":
        return f"""你是一位经验丰富的看涨研究员。

你的任务是在投资辩论中代表看涨观点，论证股票的投资价值。

请：
1. 基于分析师报告中的看涨论据
2. 针对看跌研究员的观点进行反驳（如果有）
3. 提出更有力的看涨证据
4. 给出明确的看涨建议

{base_info}

输出格式：
- 首先总结你的核心看涨论点
- 然后逐条反驳对手的观点（如果有）
- 最后给出强有力的看涨结论
"""

    else:  # bear
        return f"""你是一位经验丰富的看跌研究员。

你的任务是在投资辩论中代表看跌观点，提示投资风险。

请：
1. 基于分析师报告中的看跌论据
2. 针对看涨研究员的观点进行反驳（如果有）
3. 提出更有力的风险证据
4. 给出明确的看跌建议

{base_info}

输出格式：
- 首先总结你的核心看跌论点
- 然后逐条反驳对手的观点（如果有）
- 最后给出强有力的看跌结论
"""


# =============================================================================
# Phase 2: 辩论节点（结构固定，提示词可配置）
# =============================================================================

async def bull_debater_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """
    看涨辩手节点

    从累积的 debate_turns 中读取历史记录
    """
    logger.info(f"[看涨辩手] 开始辩论，轮次: {len(state.get('debate_turns', []))}")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "bull_debater", phase="phase2")
        tools = _get_tools_for_agent(state, "bull_debater")

        # 构建提示词（包含历史记录）
        round_idx = len(state.get("debate_turns", []))
        prompt = _build_debate_prompt(state, "bull", round_idx)

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位经验丰富的看涨研究员。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages, tools=tools)

        # 返回状态更新（自动累积）
        return {
            "debate_turns": [{
                "round": round_idx,
                "bull_argument": response.content,
                "timestamp": datetime.now().isoformat()
            }],
            "token_usage": [{
                "phase": "phase2",
                "agent": "bull_debater",
                "tokens": response.usage if response.usage else {}
            }],
            "current_phase": "phase2"
        }

    except Exception as e:
        logger.error(f"[看涨辩手] 辩论失败: {e}")
        return {
            "errors": [{
                "phase": "phase2",
                "agent": "bull_debater",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
        }


async def bear_debater_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """看跌辩手节点"""
    logger.info(f"[看跌辩手] 开始辩论，轮次: {len(state.get('debate_turns', []))}")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "bear_debater", phase="phase2")
        tools = _get_tools_for_agent(state, "bear_debater")

        round_idx = len(state.get("debate_turns", []))
        prompt = _build_debate_prompt(state, "bear", round_idx)

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位经验丰富的看跌研究员。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages, tools=tools)

        # 获取上一轮的看涨观点（如果存在）
        last_turn = state.get("debate_turns", [])[-1] if state.get("debate_turns") else None
        bull_argument = last_turn.get("bull_argument", "") if last_turn else ""

        return {
            # 更新上一轮的 bear_argument
            "debate_turns": [{
                "round": round_idx,
                "bull_argument": bull_argument,  # 保留上一轮的看涨观点
                "bear_argument": response.content,
                "timestamp": datetime.now().isoformat()
            }],
            "token_usage": [{
                "phase": "phase2",
                "agent": "bear_debater",
                "tokens": response.usage if response.usage else {}
            }]
        }

    except Exception as e:
        logger.error(f"[看跌辩手] 辩论失败: {e}")
        return {
            "errors": [{
                "phase": "phase2",
                "agent": "bear_debater",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
        }


async def research_manager_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """研究经理节点（裁决辩论）"""
    logger.info(f"[研究经理] 开始裁决辩论")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "research_manager", phase="phase2")

        # 汇总辩论记录
        debate_summary = "\n\n".join([
            f"第{turn.get('round', 0)}轮:\n"
            f"看涨方: {turn.get('bull_argument', '')}\n"
            f"看跌方: {turn.get('bear_argument', '')}"
            for turn in state.get("debate_turns", [])
        ])

        prompt = f"""你是一位经验丰富的研究经理。

你的任务是评估辩论双方的论据，并给出裁决。

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 辩论记录
{debate_summary}

## 你的任务
请评估双方的论据，并给出你的裁决：
1. 哪一方的论据更有说服力？
2. 核心观点是什么？
3. 是否存在明显的风险或机会？

请给出明确的裁决结论。
"""

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位经验丰富的研究经理。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "manager_decision": [{
                "content": response.content,
                "timestamp": datetime.now().isoformat()
            }],
            "token_usage": [{
                "phase": "phase2",
                "agent": "research_manager",
                "tokens": response.usage if response.usage else {}
            }]
        }

    except Exception as e:
        logger.error(f"[研究经理] 裁决失败: {e}")
        return {
            "errors": [{
                "phase": "phase2",
                "agent": "research_manager",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
        }


async def trade_planner_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """交易计划节点"""
    logger.info(f"[交易计划] 开始制定交易计划")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "trade_planner", phase="phase2")

        # 汇总所有信息
        manager_decision = state.get("manager_decision", [])[-1].get("content", "") if state.get("manager_decision") else ""

        prompt = f"""你是一位专业的交易计划制定者。

基于研究经理的裁决，制定具体的交易计划。

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 研究经理的裁决
{manager_decision}

## 你的任务
请制定详细的交易计划，包括：
1. 操作建议（买入/卖出/持有）
2. 建议价格区间
3. 仓位配置建议
4. 止损止盈位
5. 风险控制措施

请给出清晰、可执行的交易计划。
"""

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位专业的交易计划制定者。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "trade_plan": [{
                "content": response.content,
                "timestamp": datetime.now().isoformat()
            }],
            "token_usage": [{
                "phase": "phase2",
                "agent": "trade_planner",
                "tokens": response.usage if response.usage else {}
            }]
        }

    except Exception as e:
        logger.error(f"[交易计划] 制定失败: {e}")
        return {
            "errors": [{
                "phase": "phase2",
                "agent": "trade_planner",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
        }


# =============================================================================
# Phase 3: 风险评估节点
# =============================================================================

async def aggressive_risk_analyst_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """激进派风险分析师节点"""
    logger.info(f"[激进派风险分析师] 开始评估")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "aggressive_risk_analyst", phase="phase2")

        prompt = f"""你是一位激进派风险分析师，倾向于追求高收益。

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 交易计划
{state.get('trade_plan', [])[-1].get('content', '') if state.get('trade_plan') else ''}

请从激进派角度评估风险，给出你的建议。
"""

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位激进派风险分析师。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "risk_assessments": [{
                "analyst": "aggressive",
                "content": response.content,
                "timestamp": datetime.now().isoformat()
            }],
            "token_usage": [{
                "phase": "phase3",
                "agent": "aggressive_risk_analyst",
                "tokens": response.usage if response.usage else {}
            }],
            "current_phase": "phase3"
        }

    except Exception as e:
        logger.error(f"[激进派风险分析师] 评估失败: {e}")
        return {
            "errors": [{
                "phase": "phase3",
                "agent": "aggressive_risk_analyst",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
        }


async def conservative_risk_analyst_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """保守派风险分析师节点"""
    logger.info(f"[保守派风险分析师] 开始评估")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "conservative_risk_analyst", phase="phase2")

        prompt = f"""你是一位保守派风险分析师，注重本金安全。

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 交易计划
{state.get('trade_plan', [])[-1].get('content', '') if state.get('trade_plan') else ''}

请从保守派角度评估风险，给出你的建议。
"""

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位保守派风险分析师。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "risk_assessments": [{
                "analyst": "conservative",
                "content": response.content,
                "timestamp": datetime.now().isoformat()
            }],
            "token_usage": [{
                "phase": "phase3",
                "agent": "conservative_risk_analyst",
                "tokens": response.usage if response.usage else {}
            }]
        }

    except Exception as e:
        logger.error(f"[保守派风险分析师] 评估失败: {e}")
        return {
            "errors": [{
                "phase": "phase3",
                "agent": "conservative_risk_analyst",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
        }


async def neutral_risk_analyst_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """中性派风险分析师节点"""
    logger.info(f"[中性派风险分析师] 开始评估")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "neutral_risk_analyst", phase="phase2")

        prompt = f"""你是一位中性派风险分析师，追求风险和收益的平衡。

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 交易计划
{state.get('trade_plan', [])[-1].get('content', '') if state.get('trade_plan') else ''}

请从中性派角度评估风险，给出你的建议。
"""

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位中性派风险分析师。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "risk_assessments": [{
                "analyst": "neutral",
                "content": response.content,
                "timestamp": datetime.now().isoformat()
            }],
            "token_usage": [{
                "phase": "phase3",
                "agent": "neutral_risk_analyst",
                "tokens": response.usage if response.usage else {}
            }]
        }

    except Exception as e:
        logger.error(f"[中性派风险分析师] 评估失败: {e}")
        return {
            "errors": [{
                "phase": "phase3",
                "agent": "neutral_risk_analyst",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
        }


async def chief_risk_officer_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """首席风控官节点（总结风险评估）"""
    logger.info(f"[首席风控官] 开始总结风险评估")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "chief_risk_officer", phase="phase2")

        # 汇总三派评估
        assessments_summary = "\n\n".join([
            f"{assessment.get('analyst', '').title()}派: {assessment.get('content', '')}"
            for assessment in state.get("risk_assessments", [])
        ])

        prompt = f"""你是一位首席风控官（CRO）。

请综合三派的风险评估意见，给出最终的风险评估结论。

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 三派评估
{assessments_summary}

## 你的任务
请综合三派意见，给出：
1. 风险等级（高/中/低）
2. 风险评分（0-100分）
3. 核心风险点
4. 风险控制建议

请给出清晰的风险评估结论。
"""

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位首席风控官。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "cro_summary": [{
                "content": response.content,
                "timestamp": datetime.now().isoformat()
            }],
            "token_usage": [{
                "phase": "phase3",
                "agent": "chief_risk_officer",
                "tokens": response.usage if response.usage else {}
            }]
        }

    except Exception as e:
        logger.error(f"[首席风控官] 总结失败: {e}")
        return {
            "errors": [{
                "phase": "phase3",
                "agent": "chief_risk_officer",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
        }


# =============================================================================
# Phase 4: 总结节点
# =============================================================================

async def final_summarizer_node(
    state: TradingAgentState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """
    最终总结节点

    汇总所有阶段的信息，生成最终报告
    """
    logger.info(f"[最终总结] 开始生成最终报告")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "final_summarizer", phase="phase2")

        # 汇总所有信息
        all_reports = "\n\n".join([
            f"## {report.get('agent_name', '分析师')}\n{report.get('content', '')}"
            for report in state.get("analyst_reports", [])
        ])

        debate_summary = "\n\n".join([
            f"第{turn.get('round', 0)}轮:\n看涨: {turn.get('bull_argument', '')}\n看跌: {turn.get('bear_argument', '')}"
            for turn in state.get("debate_turns", [])
        ])

        manager_decision = state.get("manager_decision", [])[-1].get("content", "") if state.get("manager_decision") else ""
        trade_plan = state.get("trade_plan", [])[-1].get("content", "") if state.get("trade_plan") else ""
        cro_summary = state.get("cro_summary", [])[-1].get("content", "") if state.get("cro_summary") else ""

        prompt = f"""你是一位首席投资顾问。

请汇总所有分析阶段的信息，生成最终的投资分析报告。

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 第一阶段：分析师团队报告
{all_reports}

## 第二阶段：辩论与交易计划
### 辩论记录
{debate_summary}

### 研究经理裁决
{manager_decision}

### 交易计划
{trade_plan}

## 第三阶段：风险评估
{cro_summary}

## 你的任务
请综合以上所有信息，生成最终的投资分析报告，包括：
1. 投资建议（强烈买入/买入/持有/卖出/强烈卖出）
2. 核心观点总结
3. 关键风险提示
4. 具体操作建议

请生成清晰、专业的最终报告（Markdown 格式）。
"""

        from core.ai.llm.provider import Message
        messages = [
            Message(role="system", content="你是一位首席投资顾问。"),
            Message(role="user", content=prompt)
        ]

        response = await llm.chat_completion(messages=messages)

        # 提取投资建议
        recommendation = _extract_recommendation(response.content)

        return {
            "final_report": {
                "content": response.content,
                "recommendation": recommendation,
                "timestamp": datetime.now().isoformat()
            },
            "token_usage": [{
                "phase": "phase4",
                "agent": "final_summarizer",
                "tokens": response.usage if response.usage else {}
            }],
            "current_phase": "phase4",
            "status": TaskStatus.COMPLETED.value,
            "end_time": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"[最终总结] 生成失败: {e}")
        return {
            "errors": [{
                "phase": "phase4",
                "agent": "final_summarizer",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }],
            "status": TaskStatus.FAILED.value,
            "end_time": datetime.now().isoformat()
        }


# =============================================================================
# 辅助函数
# =============================================================================

def _extract_recommendation(content: str) -> str:
    """
    从最终报告内容中提取投资建议

    Args:
        content: 报告内容

    Returns:
        投资建议（STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL）
    """
    content_lower = content.lower()

    if "强烈买入" in content or "strong buy" in content_lower:
        return "STRONG_BUY"
    elif "强烈卖出" in content or "strong sell" in content_lower:
        return "STRONG_SELL"
    elif "买入" in content or "buy" in content_lower:
        return "BUY"
    elif "卖出" in content or "sell" in content_lower:
        return "SELL"
    else:
        return "HOLD"
