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
- **WebSocket 集成**: 支持 agent_messages 推送到前端
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from langchain_core.runnables import RunnableConfig

from .state import TradingAgentState, TaskStatus
from modules.trading_agents.websocket.events import create_agent_message_event
from modules.trading_agents.websocket.manager import get_websocket_manager

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
    state: TradingAgentState, agent_slug: str, phase: str
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
        logger.info(f"[LLM] [{agent_slug}] 正在获取默认模型...")
        model_service = get_model_service()
        default_model = await model_service.get_default_model(user_id)
        logger.info(f"[LLM] [{agent_slug}] get_default_model() 返回: {default_model.model_id if default_model else None}")
        if not default_model:
            raise ValueError(
                f"无法获取模型配置: user_id={user_id}, phase={phase}. "
                f"请配置系统默认模型或在任务中指定模型。"
            )
        model_id = default_model.model_id
        logger.info(f"[LLM] [{agent_slug}] 使用系统默认模型: {model_id}")

    # ===== 3. 检查缓存 =====
    cache_key = (user_id, model_id)
    if cache_key in _llm_provider_cache:
        logger.debug(f"[LLM] 缓存命中: model={model_id}, agent={agent_slug}")
        return _llm_provider_cache[cache_key]

    # ===== 4. 从 AIModelService 获取模型配置 =====
    logger.debug(f"[LLM] 从 AIModelService 获取模型配置: {model_id}")
    logger.info(f"[LLM] [{agent_slug}] 正在调用 get_model({model_id}, {user_id})...")
    model_service = get_model_service()
    model_config_obj = await model_service.get_model(model_id, user_id)
    logger.info(f"[LLM] [{agent_slug}] get_model() 返回: {model_config_obj.name if model_config_obj else None}")

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
    provider_type = (
        model_config_obj.platform_name.value if model_config_obj.platform_name else "custom"
    )

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
    enabled_local_tools: list = None,
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
        state: TradingAgentState, config: RunnableConfig
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
            tools = await _get_tools_for_agent(
                state, agent_slug, enabled_mcp_servers, enabled_local_tools
            )

            # 构建提示词（使用配置中的 role_definition）
            prompt = _build_phase1_prompt(
                agent_slug=agent_slug,
                agent_name=agent_name,
                role_definition=role_definition,
                state=state,
            )

            # ===== 新增：记录 LLM 消息流 =====
            # 记录系统提示词
            try:
                ws_manager = get_websocket_manager()
                system_message = create_agent_message_event(
                    task_id=state.get("task_id", ""),
                    agent_slug=agent_slug,
                    agent_name=agent_name,
                    message_type="system",
                    content=f"你是{agent_name}。",
                )
                await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
                logger.debug(f"[{agent_name}] 已记录系统提示词到 WebSocket")
            except Exception as e:
                logger.warning(f"[{agent_name}] 记录系统提示词失败: {e}")

            # 记录用户输入
            try:
                ws_manager = get_websocket_manager()
                user_message = create_agent_message_event(
                    task_id=state.get("task_id", ""),
                    agent_slug=agent_slug,
                    agent_name=agent_name,
                    message_type="user",
                    content=prompt,
                )
                await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
                logger.debug(f"[{agent_name}] 已记录用户输入到 WebSocket")
            except Exception as e:
                logger.warning(f"[{agent_name}] 记录用户输入失败: {e}")

            # 调用 LLM
            from core.ai.llm.provider import Message

            messages = [
                Message(role="system", content=f"你是{agent_name}。"),
                Message(role="user", content=prompt),
            ]

            # 如果有工具，使用带工具的 LLM
            if tools:
                # ===== 新增：记录工具调用意图 =====
                try:
                    ws_manager = get_websocket_manager()
                    tool_thinking_message = create_agent_message_event(
                        task_id=state.get("task_id", ""),
                        agent_slug=agent_slug,
                        agent_name=agent_name,
                        message_type="assistant",
                        content="正在调用工具获取数据...",
                    )
                    await ws_manager.broadcast_event(
                        state.get("task_id", ""), tool_thinking_message
                    )
                    logger.debug(f"[{agent_name}] 已推送工具调用意图消息到 WebSocket")
                except Exception as e:
                    logger.warning(f"[{agent_name}] 推送工具调用意图消息失败: {e}")

                result = await llm.chat_completion(
                    messages=messages,
                    tools=tools,
                )
                content = result.content
                tool_calls_made = result.tool_calls or []
            else:
                result = await llm.chat_completion(messages=messages)
                content = result.content
                tool_calls_made = []

            # ===== 新增：记录 assistant 开始输出消息 =====
            try:
                ws_manager = get_websocket_manager()
                assistant_start_message = create_agent_message_event(
                    task_id=state.get("task_id", ""),
                    agent_slug=agent_slug,
                    agent_name=agent_name,
                    message_type="assistant",
                    content="开始分析...",
                )
                await ws_manager.broadcast_event(state.get("task_id", ""), assistant_start_message)
                logger.debug(f"[{agent_name}] 已推送 assistant 开始消息到 WebSocket")
            except Exception as e:
                logger.warning(f"[{agent_name}] 推送 assistant 开始消息失败: {e}")

            # 记录工具调用
            tool_call_records = []
            for tool_call in tool_calls_made:
                tool_call_records.append(
                    {
                        "agent": agent_slug,
                        "tool": tool_call.name if hasattr(tool_call, 'name') else str(tool_call),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # 记录 Token 消耗
            usage = result.usage or {}
            token_record = {
                "phase": "phase1",
                "agent": agent_slug,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "timestamp": datetime.now().isoformat(),
            }

            # 构建分析师报告（只传递最终报告，不传递中间过程）
            analyst_report = {
                "agent_slug": agent_slug,
                "agent_name": agent_name,
                "content": content,  # 最终报告内容
                "timestamp": datetime.now().isoformat(),
            }

            # ===== 新增：记录 assistant 完成消息 =====
            try:
                ws_manager = get_websocket_manager()
                complete_message = create_agent_message_event(
                    task_id=state.get("task_id", ""),
                    agent_slug=agent_slug,
                    agent_name=agent_name,
                    message_type="assistant",
                    content=content[:1000] if len(content) > 1000 else content,  # 截断超长内容
                )
                await ws_manager.broadcast_event(state.get("task_id", ""), complete_message)
                logger.debug(f"[{agent_name}] 已推送 assistant 完成消息到 WebSocket")
            except Exception as e:
                logger.warning(f"[{agent_name}] 推送 assistant 完成消息失败: {e}")

            logger.info(f"[{agent_name}] 分析完成，Token: {token_record['total_tokens']}")

            # 返回状态更新（使用累积器）
            result = {
                "analyst_reports": [analyst_report],  # 列表会自动累积
                "completed_analysts": state.get("completed_analysts", 0) + 1,
                "token_usage": [token_record],  # 列表会自动累积
                "tool_calls": tool_call_records,  # 列表会自动累积
            }
            logger.info(f"[{agent_name}] 返回状态: analyst_reports={len(result['analyst_reports'])}, completed_analysts={result['completed_analysts']}")
            return result

        except Exception as e:
            logger.error(f"[{agent_name}] 分析失败: {e}", exc_info=True)

            # 记录错误
            error_record = {
                "phase": "phase1",
                "agent": agent_slug,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

            return {
                "errors": [error_record],  # 列表会自动累积
                "completed_analysts": state.get("completed_analysts", 0) + 1,  # 即使失败也计数
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
    enabled_local_tools: list = None,
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

    logger.debug(
        f"[Tools] 获取工具列表: agent={agent_slug}, mcp_servers={len(enabled_mcp_servers)}, local_tools={len(enabled_local_tools)}"
    )
    return []


def _build_phase1_prompt(
    agent_slug: str, agent_name: str, role_definition: str, state: TradingAgentState
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
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}
"""

    # 直接使用配置中的 role_definition
    # 不再有任何硬编码的提示词
    prompt = f"""{role_definition}

{base_info}

请严格按照你的角色定义，生成专业的分析报告（Markdown 格式）。
"""

    return prompt


def _build_phase2_initial_prompt(
    state: TradingAgentState,
    agent_type: str,  # "bull" or "bear"
) -> str:
    """
    构建 Phase 2 初始观点提示词

    Args:
        state: 工作流状态
        agent_type: 智能体类型（bull 或 bear）

    Returns:
        提示词字符串
    """
    base_info = f"""
## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}
"""

    # 添加 Phase 1 分析师报告（强制上下文）
    if state["analyst_reports"]:
        base_info += "\n## 第一阶段：分析师团队报告\n\n"
        for report in state["analyst_reports"]:
            base_info += f"### {report.get('agent_name', '分析师')}\n\n"
            base_info += f"{report.get('content', '')}\n\n"
    else:
        base_info += "\n## 第一阶段：分析师团队报告\n\n（暂无报告）\n"

    if agent_type == "bull":
        return f"""你是一位经验丰富的看涨研究员。

你的任务是基于第一阶段分析师团队的报告，构建看涨投资逻辑。

请：
1. 仔细阅读第一阶段所有分析师的报告
2. 提炼其中的看涨论据和投资机会
3. 构建完整的看涨投资逻辑
4. 给出明确的看涨建议

{base_info}

请生成完整的看涨逻辑分析报告（Markdown 格式），包括：
- 核心看涨论点
- 支撑证据（来自第一阶段报告）
- 投资机会分析
- 明确的看涨建议
"""

    else:  # bear
        return f"""你是一位经验丰富的看跌研究员。

你的任务是基于第一阶段分析师团队的报告，识别投资风险。

请：
1. 仔细阅读第一阶段所有分析师的报告
2. 提炼其中的看跌论据和风险因素
3. 构建完整的风险分析框架
4. 给出明确的风险提示

{base_info}

请生成完整的看跌风险分析报告（Markdown 格式），包括：
- 核心风险点
- 支撑证据（来自第一阶段报告）
- 潜在风险因素
- 明确的看跌建议或风险提示
"""


def _build_debate_rebuttal_prompt(
    state: TradingAgentState,
    agent_type: str,  # "bull" or "bear"
    round_idx: int,
) -> str:
    """
    构建辩论反驳提示词

    Args:
        state: 工作流状态
        agent_type: 智能体类型（bull 或 bear）
        round_idx: 当前轮次

    Returns:
        提示词字符串
    """
    base_info = f"""
## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}
"""

    # 添加 Phase 1 分析师报告
    if state["analyst_reports"]:
        base_info += "\n## 第一阶段：分析师团队报告（参考）\n\n"
        for report in state["analyst_reports"]:
            base_info += f"### {report.get('agent_name', '分析师')}\n\n"
            base_info += f"{report.get('content', '')}\n\n"

    # 添加对手的完整报告（包含所有历史轮次）
    if agent_type == "bull":
        opponent_report = state.get("bear_base_report", {}).get("content", "")
        opponent_role = "看跌研究员"
        own_role = "看涨研究员"
    else:
        opponent_report = state.get("bull_base_report", {}).get("content", "")
        opponent_role = "看涨研究员"
        own_role = "看跌研究员"

    if opponent_report:
        base_info += f"""
## {opponent_role}的完整报告

<opponent_report>
{opponent_report}
</opponent_report>

请针对以上{opponent_role}的完整报告进行反驳和回应。
"""

    section_title = f"## 第 {round_idx + 1} 轮辩论反驳" if agent_type == "bull" else f"## 第 {round_idx + 1} 轮风险提示"

    if agent_type == "bull":
        return f"""你是一位经验丰富的看涨研究员。

当前任务：针对{opponent_role}的完整报告进行反驳。

请：
1. 仔细阅读{opponent_role}的完整报告（包含初始观点和所有历史辩论轮次）
2. 识别其论证中的漏洞或不足
3. 提出更有力的看涨证据进行反驳
4. 强化你的看涨逻辑

{base_info}

输出格式：
**请只输出本轮辩论内容，内容将追加到你的看涨逻辑分析报告中。**

{section_title}

（在此处输出你的反驳内容，Markdown 格式）
- 针对{opponent_role}观点的反驳
- 补充更有力的看涨证据
- 强化看涨逻辑
- 给出本轮的看涨结论
"""

    else:  # bear
        return f"""你是一位经验丰富的看跌研究员。

当前任务：针对{opponent_role}的完整报告进行反驳和风险提示。

请：
1. 仔细阅读{opponent_role}的完整报告（包含初始观点和所有历史辩论轮次）
2. 识别其论证中的盲目乐观或风险忽视
3. 提出更有力的风险证据进行警示
4. 强化你的风险分析框架

{base_info}

输出格式：
**请只输出本轮辩论内容，内容将追加到你的看跌风险分析报告中。**

{section_title}

（在此处输出你的反驳内容，Markdown 格式）
- 针对{opponent_role}观点的反驳
- 补充更有力的风险证据
- 强化风险分析
- 给出本轮的风险提示或看跌建议
"""


# =============================================================================
# Phase 2: 辩论节点（结构固定，提示词可配置）
# =============================================================================


async def bull_initial_view_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    看涨分析师初始观点生成节点

    **必须执行**：无论 DEBATE_ROUNDS 是多少，此节点都必须执行
    **上下文**：Phase 1 所有分析师报告
    **输出**：创建看涨完整报告（初始观点）
    """
    logger.info(f"[看涨分析师] 开始生成初始观点")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "bull_initial", phase="phase2")
        tools = await _get_tools_for_agent(state, "bull_initial")

        # 构建提示词（包含 Phase 1 所有报告）
        prompt = _build_phase2_initial_prompt(state, "bull")

        # 记录 agent_messages
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bull_initial",
                agent_name="看涨分析师",
                message_type="system",
                content="你是一位经验丰富的看涨研究员。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug(f"[看涨分析师] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[看涨分析师] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bull_initial",
                agent_name="看涨分析师",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug(f"[看涨分析师] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[看涨分析师] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位经验丰富的看涨研究员。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages, tools=tools)

        # 构建完整报告（初始观点）
        bull_report = {
            "agent_slug": "bull_initial",
            "agent_name": "看涨分析师",
            "content": response.content,  # 完整报告内容
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"[看涨分析师] 初始观点生成完成，报告长度: {len(response.content)}")

        return {
            "bull_base_report": bull_report,  # 保存完整报告
            "bull_initial_completed": True,  # 标记完成
            "token_usage": [
                {
                    "phase": "phase2",
                    "agent": "bull_initial",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[看涨分析师] 初始观点生成失败: {e}", exc_info=True)
        return {
            "errors": [
                {
                    "phase": "phase2",
                    "agent": "bull_initial",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "bull_initial_completed": True,  # 即使失败也标记为完成，避免阻塞流程
        }


async def bear_initial_view_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    看跌分析师初始观点生成节点

    **必须执行**：无论 DEBATE_ROUNDS 是多少，此节点都必须执行
    **上下文**：Phase 1 所有分析师报告
    **输出**：创建看跌完整报告（初始观点）
    """
    logger.info(f"[看跌分析师] 开始生成初始观点")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "bear_initial", phase="phase2")
        tools = await _get_tools_for_agent(state, "bear_initial")

        # 构建提示词（包含 Phase 1 所有报告）
        prompt = _build_phase2_initial_prompt(state, "bear")

        # 记录 agent_messages
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bear_initial",
                agent_name="看跌分析师",
                message_type="system",
                content="你是一位经验丰富的看跌研究员。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug(f"[看跌分析师] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[看跌分析师] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bear_initial",
                agent_name="看跌分析师",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug(f"[看跌分析师] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[看跌分析师] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位经验丰富的看跌研究员。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages, tools=tools)

        # 构建完整报告（初始观点）
        bear_report = {
            "agent_slug": "bear_initial",
            "agent_name": "看跌分析师",
            "content": response.content,  # 完整报告内容
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"[看跌分析师] 初始观点生成完成，报告长度: {len(response.content)}")

        return {
            "bear_base_report": bear_report,  # 保存完整报告
            "bear_initial_completed": True,  # 标记完成
            "token_usage": [
                {
                    "phase": "phase2",
                    "agent": "bear_initial",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[看跌分析师] 初始观点生成失败: {e}", exc_info=True)
        return {
            "errors": [
                {
                    "phase": "phase2",
                    "agent": "bear_initial",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "bear_initial_completed": True,  # 即使失败也标记为完成
        }


async def bull_debate_rebuttal_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    看涨分析师辩论反驳节点

    **可选执行**：仅在 DEBATE_ROUNDS > 0 且进入辩论循环时执行
    **上下文**：Phase 1 报告 + 看跌完整报告（包含初始+所有历史轮次）
    **输出**：追加内容到看涨完整报告

    **重要说明**：
    由于与 bear_debate_rebuttal_node 并行执行，本节点读取的 bear_base_report
    是**上一轮**的值，不是本轮最新的。这是符合设计预期的，因为：
    1. 真实辩论中，每轮都是基于对手上一轮的论点进行反驳
    2. 最后一轮辩论是总结陈词，不会得到对方回应
    3. 并行执行能提升性能
    """
    current_round = state.get("current_debate_round", 0)
    logger.info(f"[看涨分析师] 开始第 {current_round + 1} 轮辩论反驳")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "bull_debate", phase="phase2")
        tools = await _get_tools_for_agent(state, "bull_debate")

        # 构建提示词（包含对手完整报告）
        prompt = _build_debate_rebuttal_prompt(state, "bull", current_round)

        # 记录 agent_messages
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bull_debate",
                agent_name="看涨分析师",
                message_type="system",
                content="你是一位经验丰富的看涨研究员。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug(f"[看涨分析师] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[看涨分析师] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bull_debate",
                agent_name="看涨分析师",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug(f"[看涨分析师] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[看涨分析师] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位经验丰富的看涨研究员。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages, tools=tools)

        # 获取当前看涨报告
        current_bull_report = state.get("bull_base_report", {})
        current_content = current_bull_report.get("content", "")

        # 追加本轮辩论内容
        new_content = f"{current_content}\n\n{response.content}"
        updated_bull_report = current_bull_report.copy()
        updated_bull_report["content"] = new_content
        updated_bull_report["timestamp"] = datetime.now().isoformat()

        logger.info(f"[看涨分析师] 第 {current_round + 1} 轮辩论完成，追加内容长度: {len(response.content)}")

        return {
            "bull_base_report": updated_bull_report,  # 更新完整报告
            # 不在这里记录 debate_turns，由 bear_debate_rebuttal_node 统一记录
            "token_usage": [
                {
                    "phase": "phase2",
                    "agent": "bull_debate",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[看涨分析师] 第 {current_round + 1} 轮辩论失败: {e}", exc_info=True)
        return {
            "errors": [
                {
                    "phase": "phase2",
                    "agent": "bull_debate",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


async def bear_debate_rebuttal_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    看跌分析师辩论反驳节点

    **可选执行**：仅在 DEBATE_ROUNDS > 0 且进入辩论循环时执行
    **上下文**：Phase 1 报告 + 看涨完整报告（包含初始+所有历史轮次）
    **输出**：追加内容到看跌完整报告

    **重要说明**：
    由于与 bull_debate_rebuttal_node 并行执行，本节点读取的 bull_base_report
    是**上一轮**的值，不是本轮最新的。这是符合设计预期的，因为：
    1. 真实辩论中，每轮都是基于对手上一轮的论点进行反驳
    2. 最后一轮辩论是总结陈词，不会得到对方回应
    3. 并行执行能提升性能
    """
    current_round = state.get("current_debate_round", 0)
    logger.info(f"[看跌分析师] 开始第 {current_round + 1} 轮辩论反驳")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "bear_debate", phase="phase2")
        tools = await _get_tools_for_agent(state, "bear_debate")

        # 构建提示词（包含对手完整报告）
        prompt = _build_debate_rebuttal_prompt(state, "bear", current_round)

        # 记录 agent_messages
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bear_debate",
                agent_name="看跌分析师",
                message_type="system",
                content="你是一位经验丰富的看跌研究员。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug(f"[看跌分析师] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[看跌分析师] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bear_debate",
                agent_name="看跌分析师",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug(f"[看跌分析师] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[看跌分析师] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位经验丰富的看跌研究员。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages, tools=tools)

        # 获取当前看跌报告
        current_bear_report = state.get("bear_base_report", {})
        current_content = current_bear_report.get("content", "")

        # 追加本轮辩论内容
        new_content = f"{current_content}\n\n{response.content}"
        updated_bear_report = current_bear_report.copy()
        updated_bear_report["content"] = new_content
        updated_bear_report["timestamp"] = datetime.now().isoformat()

        logger.info(f"[看跌分析师] 第 {current_round + 1} 轮辩论完成，追加内容长度: {len(response.content)}")

        # 获取本轮看涨反驳的内容（从 bull_base_report 中提取最新的辩论内容）
        # 注意：由于并行执行，bull_base_report 可能还未更新，所以我们需要等待下一轮
        # 因此，这里我们只记录 bear_argument，bull_argument 留空或在下一轮补全
        # 更好的方案：不在 debate_turns 中记录，只保留 bull_base_report 和 bear_base_report

        # 简化：只记录本轮的 bear_argument，不依赖 bull
        return {
            "bear_base_report": updated_bear_report,  # 更新完整报告
            # 暂时不记录 debate_turns，因为并行执行会导致数据不一致
            # 如果需要记录，应该在另一个串行节点中统一记录
            "token_usage": [
                {
                    "phase": "phase2",
                    "agent": "bear_debate",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[看跌分析师] 第 {current_round + 1} 轮辩论失败: {e}", exc_info=True)
        return {
            "errors": [
                {
                    "phase": "phase2",
                    "agent": "bear_debate",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


# =============================================================================
# 保留旧的节点函数（向后兼容，但标记为已弃用）
# =============================================================================


async def bull_debater_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    看涨辩手节点

    从累积的 debate_turns 中读取历史记录
    """
    logger.info(f"[看涨辩手] 开始辩论，轮次: {len(state.get('debate_turns', []))}")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "bull_debater", phase="phase2")
        tools = await _get_tools_for_agent(state, "bull_debater")

        # 构建提示词（包含历史记录）
        round_idx = len(state.get("debate_turns", []))
        prompt = _build_debate_prompt(state, "bull", round_idx)

        # ===== 新增：记录 agent_messages =====
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bull_debater",
                agent_name="看涨辩手",
                message_type="system",
                content="你是一位经验丰富的看涨研究员。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug(f"[看涨辩手] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[看涨辩手] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bull_debater",
                agent_name="看涨辩手",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug(f"[看涨辩手] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[看涨辩手] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位经验丰富的看涨研究员。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages, tools=tools)

        # 返回状态更新（自动累积）
        return {
            "debate_turns": [
                {
                    "round": round_idx,
                    "bull_argument": response.content,
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "token_usage": [
                {
                    "phase": "phase2",
                    "agent": "bull_debater",
                    "tokens": response.usage if response.usage else {},
                }
            ],
            "current_phase": "phase2",
        }

    except Exception as e:
        logger.error(f"[看涨辩手] 辩论失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase2",
                    "agent": "bull_debater",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


async def bear_debater_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """看跌辩手节点"""
    logger.info(f"[看跌辩手] 开始辩论，轮次: {len(state.get('debate_turns', []))}")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "bear_debater", phase="phase2")
        tools = await _get_tools_for_agent(state, "bear_debater")

        round_idx = len(state.get("debate_turns", []))
        prompt = _build_debate_prompt(state, "bear", round_idx)

        # ===== 新增：记录 agent_messages =====
        # 记录系统提示词
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bear_debater",
                agent_name="看跌辩手",
                message_type="system",
                content="你是一位经验丰富的看跌研究员。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug("[看跌辩手] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[看跌辩手] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bear_debater",
                agent_name="看跌辩手",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug("[看跌辩手] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[看跌辩手] 记录用户输入失败: {e}")

        # 记录思考消息
        try:
            ws_manager = get_websocket_manager()
            thinking_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="bear_debater",
                agent_name="看跌辩手",
                message_type="assistant",
                content="正在思考反驳论据..."
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), thinking_message)
            logger.debug("[看跌辩手] 已推送思考消息到 WebSocket")
        except Exception as e:
            logger.warning(f"[看跌辩手] 推送思考消息失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位经验丰富的看跌研究员。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages, tools=tools)

        # 获取上一轮的看涨观点（如果存在）
        last_turn = state.get("debate_turns", [])[-1] if state.get("debate_turns") else None
        bull_argument = last_turn.get("bull_argument", "") if last_turn else ""

        return {
            # 更新上一轮的 bear_argument
            "debate_turns": [
                {
                    "round": round_idx,
                    "bull_argument": bull_argument,  # 保留上一轮的看涨观点
                    "bear_argument": response.content,
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "token_usage": [
                {
                    "phase": "phase2",
                    "agent": "bear_debater",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[看跌辩手] 辩论失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase2",
                    "agent": "bear_debater",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


async def research_manager_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    研究经理节点（裁决辩论）

    **上下文**：读取看涨和看跌的完整报告（包含初始观点+所有辩论轮次）
    """
    logger.info(f"[研究经理] 开始裁决辩论")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "research_manager", phase="phase2")

        # 获取完整报告（包含初始观点和所有辩论轮次）
        bull_report = state.get("bull_base_report", {}).get("content", "")
        bear_report = state.get("bear_base_report", {}).get("content", "")

        # 如果没有完整报告，报错（不应该发生）
        if not bull_report or not bear_report:
            logger.error(f"[研究经理] 完整报告缺失！bull_report={bool(bull_report)}, bear_report={bool(bear_report)}")
            raise ValueError("研究经理需要完整的看涨和看跌报告才能进行裁决")

        prompt = f"""你是一位经验丰富的研究经理。

你的任务是评估看涨和看跌研究员的完整报告，并给出裁决。

## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}

## 看涨研究员的完整报告
{bull_report}

## 看跌研究员的完整报告
{bear_report}

## 你的任务
请综合评估双方的完整报告（包含初始观点和所有辩论轮次），并给出你的裁决：
1. 哪一方的论据更有说服力？为什么？
2. 双方的核心观点分别是什么？
3. 辩论过程中，双方的观点有哪些变化和演进？
4. 是否存在明显的风险或机会未被充分讨论？
5. 综合双方论据，你的裁决结论是什么？

请给出明确的裁决结论（Markdown 格式）。
"""

        # ===== 新增：记录 agent_messages =====
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="research_manager",
                agent_name="研究经理",
                message_type="system",
                content="你是一位经验丰富的研究经理。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug("[研究经理] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[研究经理] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="research_manager",
                agent_name="研究经理",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug("[研究经理] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[研究经理] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位经验丰富的研究经理。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "manager_decision": [
                {"content": response.content, "timestamp": datetime.now().isoformat()}
            ],
            "token_usage": [
                {
                    "phase": "phase2",
                    "agent": "research_manager",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[研究经理] 裁决失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase2",
                    "agent": "research_manager",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


async def trade_planner_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    交易计划节点

    **修改**：基于研究经理的裁决 + 两份完整报告制定交易计划
    """
    logger.info(f"[交易计划] 开始制定交易计划")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "trade_planner", phase="phase2")

        # 汇总所有信息
        manager_decision = (
            state.get("manager_decision", [])[-1].get("content", "")
            if state.get("manager_decision")
            else ""
        )

        # 获取完整报告（作为参考）
        bull_report = state.get("bull_base_report", {}).get("content", "")
        bear_report = state.get("bear_base_report", {}).get("content", "")

        # 构建提示词
        reports_section = ""
        if bull_report and bear_report:
            reports_section = f"""
## 看涨研究员的完整报告（参考）
{bull_report}

## 看跌研究员的完整报告（参考）
{bear_report}
"""

        prompt = f"""你是一位专业的交易计划制定者。

## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}

## 研究经理的裁决
{manager_decision}
{reports_section}
## 你的任务
基于研究经理的裁决，制定具体的交易计划，包括：
1. 入场时机和价格
2. 目标价位
3. 止损价位
4. 仓位管理建议
5. 持有周期建议

请给出明确的交易计划（Markdown 格式）。
"""

        # ===== 新增：记录 agent_messages =====
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="trade_planner",
                agent_name="交易计划",
                message_type="system",
                content="你是一位专业的交易计划制定者。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug("[交易计划] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[交易计划] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="trade_planner",
                agent_name="交易计划",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug("[交易计划] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[交易计划] 记录用户输入失败: {e}")

        # 记录思考消息
        try:
            ws_manager = get_websocket_manager()
            thinking_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="trade_planner",
                agent_name="交易计划",
                message_type="assistant",
                content="正在制定交易计划..."
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), thinking_message)
            logger.debug("[交易计划] 已推送思考消息到 WebSocket")
        except Exception as e:
            logger.warning(f"[交易计划] 推送思考消息失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位专业的交易计划制定者。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages)

        result = {
            "trade_plan": [
                {"content": response.content, "timestamp": datetime.now().isoformat()}
            ],
            "token_usage": [
                {
                    "phase": "phase2",
                    "agent": "trade_planner",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

        logger.info(f"[交易计划] 完成，准备返回状态更新")
        logger.info(f"[交易计划] 当前状态 enable_phase3: {state.get('enable_phase3')}")
        logger.info(f"[交易计划] 当前状态 enable_phase4: {state.get('enable_phase4')}")

        return result

    except Exception as e:
        logger.error(f"[交易计划] 制定失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase2",
                    "agent": "trade_planner",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


# =============================================================================
# Phase 3: 风险评估节点
# =============================================================================


async def aggressive_risk_analyst_node(
    state: TradingAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    激进派风险分析师节点

    **上下文**：Phase 1 分析师报告 + Phase 2 完整报告（看涨/看跌/研究经理/交易计划）
    """
    logger.info(f"[激进派风险分析师] 开始评估")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "aggressive_risk_analyst", phase="phase3")

        # ===== 构建完整的上下文 =====
        base_info = f"""
## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}
"""

        # 添加 Phase 1 分析师报告（强制上下文）
        if state.get("analyst_reports"):
            base_info += "\n## 第一阶段：分析师团队报告\n\n"
            for report in state["analyst_reports"]:
                base_info += f"### {report.get('agent_name', '分析师')}\n\n"
                base_info += f"{report.get('content', '')}\n\n"

        # 添加 Phase 2 看涨完整报告
        bull_report = state.get("bull_base_report", {}).get("content", "")
        if bull_report:
            base_info += "\n## 第二阶段：看涨分析师完整报告\n\n"
            base_info += f"{bull_report}\n\n"

        # 添加 Phase 2 看跌完整报告
        bear_report = state.get("bear_base_report", {}).get("content", "")
        if bear_report:
            base_info += "\n## 第二阶段：看跌分析师完整报告\n\n"
            base_info += f"{bear_report}\n\n"

        # 添加研究经理裁决
        if state.get("manager_decision"):
            manager_decision = state["manager_decision"][-1].get("content", "")
            if manager_decision:
                base_info += "\n## 第二阶段：研究经理裁决\n\n"
                base_info += f"{manager_decision}\n\n"

        # 添加交易计划
        trade_plan = (
            state.get("trade_plan", [])[-1].get("content", "")
            if state.get("trade_plan")
            else ""
        )
        if trade_plan:
            base_info += "\n## 第二阶段：交易计划\n\n"
            base_info += f"{trade_plan}\n\n"

        prompt = f"""你是一位激进派风险分析师，倾向于追求高收益。

{base_info}

## 你的任务
请从激进派角度评估上述所有信息（包含第一阶段分析、第二阶段辩论和交易计划），给出你的风险评估和建议：

1. 从激进角度看，当前投资机会的预期收益如何？
2. 风险是否在可接受范围内？哪些风险值得承担？
3. 对于看涨/看跌双方的观点，你更支持哪一方？为什么？
4. 交易计划是否合理？有无优化建议？
5. 请给出明确的风险评估结论和建议（激进派立场）

请给出清晰的评估结论（Markdown 格式）。
"""

        # ===== 新增：记录 agent_messages =====
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="aggressive_risk_analyst",
                agent_name="激进派风险分析师",
                message_type="system",
                content="你是一位激进派风险分析师，倾向于追求高收益。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug("[激进派风险分析师] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[激进派风险分析师] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="aggressive_risk_analyst",
                agent_name="激进派风险分析师",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug("[激进派风险分析师] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[激进派风险分析师] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位激进派风险分析师。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "risk_assessments": [
                {
                    "analyst": "aggressive",
                    "content": response.content,
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "token_usage": [
                {
                    "phase": "phase3",
                    "agent": "aggressive_risk_analyst",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[激进派风险分析师] 评估失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase3",
                    "agent": "aggressive_risk_analyst",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


async def conservative_risk_analyst_node(
    state: TradingAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    保守派风险分析师节点

    **上下文**：Phase 1 分析师报告 + Phase 2 完整报告（看涨/看跌/研究经理/交易计划）
    """
    logger.info(f"[保守派风险分析师] 开始评估")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "conservative_risk_analyst", phase="phase3")

        # ===== 构建完整的上下文 =====
        base_info = f"""
## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}
"""

        # 添加 Phase 1 分析师报告（强制上下文）
        if state.get("analyst_reports"):
            base_info += "\n## 第一阶段：分析师团队报告\n\n"
            for report in state["analyst_reports"]:
                base_info += f"### {report.get('agent_name', '分析师')}\n\n"
                base_info += f"{report.get('content', '')}\n\n"

        # 添加 Phase 2 看涨完整报告
        bull_report = state.get("bull_base_report", {}).get("content", "")
        if bull_report:
            base_info += "\n## 第二阶段：看涨分析师完整报告\n\n"
            base_info += f"{bull_report}\n\n"

        # 添加 Phase 2 看跌完整报告
        bear_report = state.get("bear_base_report", {}).get("content", "")
        if bear_report:
            base_info += "\n## 第二阶段：看跌分析师完整报告\n\n"
            base_info += f"{bear_report}\n\n"

        # 添加研究经理裁决
        if state.get("manager_decision"):
            manager_decision = state["manager_decision"][-1].get("content", "")
            if manager_decision:
                base_info += "\n## 第二阶段：研究经理裁决\n\n"
                base_info += f"{manager_decision}\n\n"

        # 添加交易计划
        trade_plan = (
            state.get("trade_plan", [])[-1].get("content", "")
            if state.get("trade_plan")
            else ""
        )
        if trade_plan:
            base_info += "\n## 第二阶段：交易计划\n\n"
            base_info += f"{trade_plan}\n\n"

        prompt = f"""你是一位保守派风险分析师，注重本金安全。

{base_info}

## 你的任务
请从保守派角度评估上述所有信息（包含第一阶段分析、第二阶段辩论和交易计划），给出你的风险评估和建议：

1. 从保守角度看，当前投资存在哪些主要风险？
2. 本金安全是否有保障？最大可能的亏损是多少？
3. 对于看涨/看跌双方的观点，你更支持哪一方？为什么？
4. 交易计划的风险控制措施是否充分？有无改进建议？
5. 请给出明确的风险评估结论和建议（保守派立场）

请给出清晰的评估结论（Markdown 格式）。
"""

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="conservative_risk_analyst",
                agent_name="保守派风险分析师",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug("[保守派风险分析师] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[保守派风险分析师] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位保守派风险分析师。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "risk_assessments": [
                {
                    "analyst": "conservative",
                    "content": response.content,
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "token_usage": [
                {
                    "phase": "phase3",
                    "agent": "conservative_risk_analyst",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[保守派风险分析师] 评估失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase3",
                    "agent": "conservative_risk_analyst",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


async def neutral_risk_analyst_node(
    state: TradingAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    中性派风险分析师节点

    **上下文**：Phase 1 分析师报告 + Phase 2 完整报告（看涨/看跌/研究经理/交易计划）
    """
    logger.info(f"[中性派风险分析师] 开始评估")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "neutral_risk_analyst", phase="phase3")

        # ===== 构建完整的上下文 =====
        base_info = f"""
## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}
"""

        # 添加 Phase 1 分析师报告（强制上下文）
        if state.get("analyst_reports"):
            base_info += "\n## 第一阶段：分析师团队报告\n\n"
            for report in state["analyst_reports"]:
                base_info += f"### {report.get('agent_name', '分析师')}\n\n"
                base_info += f"{report.get('content', '')}\n\n"

        # 添加 Phase 2 看涨完整报告
        bull_report = state.get("bull_base_report", {}).get("content", "")
        if bull_report:
            base_info += "\n## 第二阶段：看涨分析师完整报告\n\n"
            base_info += f"{bull_report}\n\n"

        # 添加 Phase 2 看跌完整报告
        bear_report = state.get("bear_base_report", {}).get("content", "")
        if bear_report:
            base_info += "\n## 第二阶段：看跌分析师完整报告\n\n"
            base_info += f"{bear_report}\n\n"

        # 添加研究经理裁决
        if state.get("manager_decision"):
            manager_decision = state["manager_decision"][-1].get("content", "")
            if manager_decision:
                base_info += "\n## 第二阶段：研究经理裁决\n\n"
                base_info += f"{manager_decision}\n\n"

        # 添加交易计划
        trade_plan = (
            state.get("trade_plan", [])[-1].get("content", "")
            if state.get("trade_plan")
            else ""
        )
        if trade_plan:
            base_info += "\n## 第二阶段：交易计划\n\n"
            base_info += f"{trade_plan}\n\n"

        prompt = f"""你是一位中性派风险分析师，追求风险和收益的平衡。

{base_info}

## 你的任务
请从中性派角度评估上述所有信息（包含第一阶段分析、第二阶段辩论和交易计划），给出你的风险评估和建议：

1. 从中性角度看，当前投资的风险收益比如何？
2. 激进和保守的观点各有哪些合理性和局限性？
3. 对于看涨/看跌双方的观点，你更支持哪一方？为什么？
4. 交易计划是否平衡了风险和收益？有无优化建议？
5. 请给出明确的风险评估结论和建议（中性派立场）

请给出清晰的评估结论（Markdown 格式）。
"""

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位中性派风险分析师。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "risk_assessments": [
                {
                    "analyst": "neutral",
                    "content": response.content,
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "token_usage": [
                {
                    "phase": "phase3",
                    "agent": "neutral_risk_analyst",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[中性派风险分析师] 评估失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase3",
                    "agent": "neutral_risk_analyst",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


async def chief_risk_officer_node(
    state: TradingAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    首席风控官节点（总结风险评估）

    **上下文**：Phase 1 分析师报告 + Phase 2 完整报告 + Phase 3 三派风险评估
    """
    logger.info(f"[首席风控官] 开始总结风险评估")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "chief_risk_officer", phase="phase3")

        # ===== 构建完整的上下文 =====
        base_info = f"""
## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}
"""

        # 添加 Phase 1 分析师报告摘要（强制上下文）
        if state.get("analyst_reports"):
            base_info += "\n## 第一阶段：分析师团队报告摘要\n\n"
            for report in state["analyst_reports"]:
                base_info += f"### {report.get('agent_name', '分析师')}\n\n"
                base_info += f"{report.get('content', '')}\n\n"

        # 添加 Phase 2 看涨完整报告摘要
        bull_report = state.get("bull_base_report", {}).get("content", "")
        if bull_report:
            # 只取前500字符作为摘要，避免内容过长
            bull_summary = bull_report[:500] + "..." if len(bull_report) > 500 else bull_report
            base_info += "\n## 第二阶段：看涨分析师报告摘要\n\n"
            base_info += f"{bull_summary}\n\n"

        # 添加 Phase 2 看跌完整报告摘要
        bear_report = state.get("bear_base_report", {}).get("content", "")
        if bear_report:
            # 只取前500字符作为摘要
            bear_summary = bear_report[:500] + "..." if len(bear_report) > 500 else bear_report
            base_info += "\n## 第二阶段：看跌分析师报告摘要\n\n"
            base_info += f"{bear_summary}\n\n"

        # 添加研究经理裁决摘要
        if state.get("manager_decision"):
            manager_decision = state["manager_decision"][-1].get("content", "")
            if manager_decision:
                # 只取前500字符作为摘要
                manager_summary = manager_decision[:500] + "..." if len(manager_decision) > 500 else manager_decision
                base_info += "\n## 第二阶段：研究经理裁决摘要\n\n"
                base_info += f"{manager_summary}\n\n"

        # 添加交易计划摘要
        trade_plan = (
            state.get("trade_plan", [])[-1].get("content", "")
            if state.get("trade_plan")
            else ""
        )
        if trade_plan:
            # 只取前500字符作为摘要
            plan_summary = trade_plan[:500] + "..." if len(trade_plan) > 500 else trade_plan
            base_info += "\n## 第二阶段：交易计划摘要\n\n"
            base_info += f"{plan_summary}\n\n"

        # 汇总三派评估（完整内容）
        assessments_summary = "\n\n".join(
            [
                f"### {assessment.get('analyst', '').title()}派\n\n{assessment.get('content', '')}"
                for assessment in state.get("risk_assessments", [])
            ]
        )

        prompt = f"""你是一位首席风控官（CRO）。

请综合以下所有信息（第一阶段分析、第二阶段辩论和交易计划、第三阶段三派风险评估），给出最终的风险评估结论。

{base_info}

## 第三阶段：三派风险评估（完整内容）

{assessments_summary}

## 你的任务
请综合所有阶段的信息，给出：
1. 风险等级（高/中/低）
2. 风险评分（0-100分）
3. 核心风险点
4. 风险控制建议
5. 综合投资建议（是否推荐投资）

请给出清晰的风险评估结论（Markdown 格式）。
"""

        # ===== 新增：记录 agent_messages =====
        try:
            ws_manager = get_websocket_manager()
            system_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="chief_risk_officer",
                agent_name="首席风控官",
                message_type="system",
                content="你是一位首席风控官（CRO）。"
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), system_message)
            logger.debug("[首席风控官] 已记录系统提示词到 WebSocket")
        except Exception as e:
            logger.warning(f"[首席风控官] 记录系统提示词失败: {e}")

        # 记录用户输入
        try:
            ws_manager = get_websocket_manager()
            user_message = create_agent_message_event(
                task_id=state.get("task_id", ""),
                agent_slug="chief_risk_officer",
                agent_name="首席风控官",
                message_type="user",
                content=prompt
            )
            await ws_manager.broadcast_event(state.get("task_id", ""), user_message)
            logger.debug("[首席风控官] 已记录用户输入到 WebSocket")
        except Exception as e:
            logger.warning(f"[首席风控官] 记录用户输入失败: {e}")

        from core.ai.llm.provider import Message

        messages = [
            Message(role="system", content="你是一位首席风控官。"),
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages)

        return {
            "cro_summary": [{"content": response.content, "timestamp": datetime.now().isoformat()}],
            "token_usage": [
                {
                    "phase": "phase3",
                    "agent": "chief_risk_officer",
                    "tokens": response.usage if response.usage else {},
                }
            ],
        }

    except Exception as e:
        logger.error(f"[首席风控官] 总结失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase3",
                    "agent": "chief_risk_officer",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }


# =============================================================================
# Phase 4: 总结节点
# =============================================================================


async def final_summarizer_node(state: TradingAgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    最终总结节点

    汇总所有阶段的信息，生成最终报告

    **上下文**：Phase 1 分析师报告 + Phase 2 完整报告 + Phase 3 风险评估
    """
    logger.info(f"[最终总结] 开始生成最终报告")

    try:
        # 获取 LLM（使用辩论模型）
        llm = await _get_llm_for_agent(state, "final_summarizer", phase="phase4")

        # ===== Phase 1: 分析师团队报告 =====
        all_reports = "\n\n".join(
            [
                f"## {report.get('agent_name', '分析师')}\n{report.get('content', '')}"
                for report in state.get("analyst_reports", [])
            ]
        )

        # ===== Phase 2: 完整辩论报告 =====
        bull_report = state.get("bull_base_report", {}).get("content", "")
        bear_report = state.get("bear_base_report", {}).get("content", "")

        manager_decision = (
            state.get("manager_decision", [])[-1].get("content", "")
            if state.get("manager_decision")
            else ""
        )
        trade_plan = (
            state.get("trade_plan", [])[-1].get("content", "") if state.get("trade_plan") else ""
        )

        # ===== Phase 3: 风险评估 =====
        cro_summary = (
            state.get("cro_summary", [])[-1].get("content", "") if state.get("cro_summary") else ""
        )

        prompt = f"""你是一位首席投资顾问。

请汇总所有分析阶段的信息，生成最终的投资分析报告。

## 股票信息
- 股票代码：{state["stock_code"]}
- 交易日期：{state["trade_date"]}
- 任务 ID：{state["task_id"]}

## 第一阶段：分析师团队报告
{all_reports}

## 第二阶段：辩论与交易计划
### 看涨分析师完整报告
{bull_report}

### 看跌分析师完整报告
{bear_report}

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
            Message(role="user", content=prompt),
        ]

        response = await llm.chat_completion(messages=messages)

        # 提取投资建议
        recommendation = _extract_recommendation(response.content)

        return {
            "final_report": {
                "content": response.content,
                "recommendation": recommendation,
                "timestamp": datetime.now().isoformat(),
            },
            "token_usage": [
                {
                    "phase": "phase4",
                    "agent": "final_summarizer",
                    "tokens": response.usage if response.usage else {},
                }
            ],
            "status": TaskStatus.COMPLETED.value,
            "end_time": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"[最终总结] 生成失败: {e}")
        return {
            "errors": [
                {
                    "phase": "phase4",
                    "agent": "final_summarizer",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "status": TaskStatus.FAILED.value,
            "end_time": datetime.now().isoformat(),
        }


# =============================================================================
# 辅助函数：获取智能体的工具列表（调用 MCP 工具）
# =============================================================================


async def _get_tools_for_agent(
    state: TradingAgentState,
    agent_slug: str,
    enabled_mcp_servers: list = None,
    enabled_local_tools: list = None,
) -> list:
    """
    获取智能体的工具列表（集成 MCP 工具）

    Args:
        state: 工作流状态
        agent_slug: 智能体标识符
        enabled_mcp_servers: 启用的 MCP 服务器列表
        enabled_local_tools: 启用的本地工具列表

    Returns:
        工具列表（LangChain 格式的 BaseTool 列表）
    """
    # 获取 MCP 工具过滤器实例
    from modules.trading_agents.tools.mcp_tool_filter import get_mcp_tool_filter
    from modules.trading_agents.tools.registry import get_tool_registry

    mcp_filter = get_mcp_tool_filter()
    tool_registry = get_tool_registry()
    all_tools = tool_registry.list_all_tools()

    # 构建临时的 AgentConfig 对象（用于 MCP 过滤器）
    enabled_mcp_servers = enabled_mcp_servers or []
    enabled_local_tools = enabled_local_tools or []

    # 转换 enabled_mcp_servers 为 MCPServerConfig 列表
    from modules.trading_agents.schemas import MCPServerConfig

    mcp_server_configs = []
    for server in enabled_mcp_servers:
        if isinstance(server, str):
            mcp_server_configs.append(MCPServerConfig(name=server))
        else:
            mcp_server_configs.append(server)

    # 创建临时的 AgentConfig 对象
    from modules.trading_agents.schemas import AgentConfig

    agent_config = AgentConfig(
        slug=agent_slug,
        name=f"Agent {agent_slug}",
        role_definition=None,  # 临时对象不需要 role_definition
        when_to_use="",
        enabled_mcp_servers=mcp_server_configs,
        enabled_local_tools=enabled_local_tools,
        enabled=True,
    )

    # 使用 MCP 过滤器获取工具
    try:
        mcp_tools = await mcp_filter.get_tools_for_agent(
            agent_config=agent_config,
            user_id=state.get("user_id", ""),
            task_id=state.get("task_id", ""),
            all_tools=all_tools,
        )

        logger.debug(
            f"[Tools] 获取 MCP 工具: agent={agent_slug}, "
            f"mcp_servers={len(enabled_mcp_servers)}, local_tools={len(enabled_local_tools)}, "
            f"result={len(mcp_tools)} tools"
        )
        return mcp_tools

    except Exception as e:
        logger.warning(f"[Tools] 获取 MCP 工具失败: agent={agent_slug}, error={e}")
        # 如果 MCP 工具获取失败，返回空列表，不影响任务执行
        return []


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
