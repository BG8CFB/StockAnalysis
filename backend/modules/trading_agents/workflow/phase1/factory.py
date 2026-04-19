"""
Phase 1 智能体工厂

动态创建分析师智能体，使用 LangChain 0.3+ create_agent 接口。

**版本**: v6.0 (LangChain 0.3+ create_agent 重构版)
**最后更新**: 2025-01-19
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

from core.ai.service import AIService
from modules.trading_agents.config import get_enabled_agents
from modules.trading_agents.models.state import (
    TaskStatus,
    WorkflowState,
)
from modules.trading_agents.workflow.agent_helpers import (
    handle_agent_completed,
    handle_agent_started,
)
from modules.trading_agents.workflow.callbacks import WebSocketCallbackHandler
from modules.trading_agents.workflow.events import (
    create_phase_agents_event,
)
from modules.trading_agents.workflow.state import AgentExecution, TokenUsage

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 1 智能体工厂
# =============================================================================


class Phase1AgentFactory:
    """
    Phase 1 智能体工厂

    动态创建分析师智能体，支持并发执行。
    """

    def __init__(self, ai_service: AIService, config: Optional[Dict[str, Any]] = None) -> None:
        """
        初始化智能体工厂

        Args:
            ai_service: AI 服务
            config: 智能体配置
        """
        self.ai_service = ai_service
        self.config = config or {}

    async def create_agent(
        self,
        agent_config: Dict[str, Any],
        tools: List[BaseTool],
        model_id: str,
        user_id: str = "system",
        task_id: Optional[str] = None,
        websocket_manager: Any = None,
    ) -> Any:
        """
        创建单个智能体 (LangChain 0.3+ create_agent API)

        Args:
            agent_config: 智能体配置
            tools: 工具列表
            model_id: 模型 ID
            user_id: 用户 ID
            task_id: 任务 ID（用于回调推送）
            websocket_manager: WebSocket 管理器实例

        Returns:
            AgentExecutor 实例
        """
        # 获取 LLM 模型
        model = await self.ai_service.get_model_async(model_id, user_id)

        # 构建系统提示词
        system_prompt_str = self._build_system_prompt(agent_config)

        # 创建回调处理器（用于推送工具调用事件）
        callbacks = []
        if task_id and websocket_manager:
            callback_handler = WebSocketCallbackHandler(
                task_id=task_id,
                agent_slug=agent_config.get("slug", "unknown"),
                agent_name=agent_config.get("name", "unknown"),
                websocket_manager=websocket_manager,
            )
            callbacks.append(callback_handler)

        # 使用 LangChain 0.3+ 的 create_agent
        # 注意: callbacks 不能在这里传递，需要在 ainvoke 时通过 config 传递
        agent = create_agent(
            model,
            tools,
            system_prompt=system_prompt_str,
        )

        logger.debug(
            f"创建智能体: {agent_config['slug']} "
            f"({agent_config['name']}), "
            f"工具数: {len(tools)}, "
            f"模型: {model_id}, "
            f"用户: {user_id}"
        )

        return agent, callbacks

    def _build_system_prompt(self, agent_config: Dict[str, Any]) -> str:
        """
        构建系统提示词

        Args:
            agent_config: 智能体配置

        Returns:
            系统提示词
        """
        # 基础角色定义
        role_definition = agent_config.get("roleDefinition", "")

        # 添加上下文信息
        context = f"""
# 角色信息
- 名称: {agent_config.get('name', '分析师')}
- 描述: {agent_config.get('description', '')}

# 角色定义
{role_definition}

# 输出要求
1. 所有报告必须使用 Markdown 格式
2. 报告必须包含时间戳和数据来源
3. 结论必须基于数据和逻辑，禁止主观臆测
4. 如果数据缺失，必须明确说明而非编造
"""

        return context.strip()

    async def execute_agent(
        self,
        agent: Any,
        agent_config: Dict[str, Any],
        state: WorkflowState,
        user_prompt: str,
        callbacks: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行智能体

        Args:
            agent: AgentExecutor 实例 (LangChain 0.3+ create_agent)
            agent_config: 智能体配置
            state: 工作流状态
            user_prompt: 用户提示词
            callbacks: 回调处理器列表

        Returns:
            执行结果
        """
        agent_slug = agent_config["slug"]
        agent_name = agent_config["name"]

        # 创建执行记录
        execution = AgentExecution(
            slug=agent_slug,
            name=agent_name,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # 调用 agent (LangChain 0.3+ 使用 messages 格式)
            logger.info(f"[Phase 1] 执行智能体: {agent_slug} ({agent_name})")

            # LangChain 0.3+ 使用 messages 格式
            inputs = {"messages": [HumanMessage(content=user_prompt)]}

            # LangChain 0.3+ 正确传递 callbacks 的方式：直接放在 config 顶层，不是 configurable 下
            if callbacks:
                from langchain_core.callbacks import CallbackManager

                run_config = {"callbacks": CallbackManager(handlers=callbacks)}
                result = await agent.ainvoke(inputs, config=run_config)
            else:
                result = await agent.ainvoke(inputs)

            # 提取输出
            output = self._extract_output(result)

            # 提取 Token 使用量
            token_usage = self._extract_token_usage(result)

            # 更新执行记录
            execution.completed_at = datetime.now(timezone.utc)
            execution.status = TaskStatus.COMPLETED
            execution.output = output
            execution.token_usage = token_usage

            logger.info(
                f"[Phase 1] 智能体完成: {agent_slug} ({agent_name}), "
                f"输出长度: {len(output) if output else 0}, "
                f"tokens: {token_usage.total_tokens if token_usage else 'N/A'}"
            )

            return {
                "slug": agent_slug,
                "name": agent_name,
                "output": output,
                "execution": execution,
                "error": None,
            }

        except Exception as e:
            logger.error(f"[Phase 1] 智能体失败: {agent_slug} ({agent_name}), error={e}")

            execution.completed_at = datetime.now(timezone.utc)
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)

            return {
                "slug": agent_slug,
                "name": agent_name,
                "output": None,
                "execution": execution,
                "error": str(e),
            }

    def _extract_output(self, result: Any) -> Optional[str]:
        """
        从 agent 结果中提取输出

        Args:
            result: agent 返回结果

        Returns:
            输出文本
        """
        if isinstance(result, dict):
            # LangChain 0.3+ 返回格式: {"messages": [...]}
            messages = result.get("messages", [])
            if messages:
                # 获取最后一条消息
                last_message = messages[-1]
                # 处理消息对象
                if hasattr(last_message, "content"):
                    return str(last_message.content)
                # 处理字典格式
                elif isinstance(last_message, dict):
                    return str(last_message.get("content", ""))

        # 直接返回字符串
        if isinstance(result, str):
            return result

        return str(result)

    def _extract_token_usage(self, result: Any) -> Optional[TokenUsage]:
        """
        从 agent 结果中提取 Token 使用量

        Args:
            result: agent 返回结果

        Returns:
            TokenUsage 对象或 None
        """
        try:
            if isinstance(result, dict):
                messages = result.get("messages", [])
                if messages:
                    # 遍历消息查找 usage_metadata
                    total_prompt = 0
                    total_completion = 0
                    found_usage = False

                    for msg in messages:
                        # 尝试获取 usage_metadata
                        usage_metadata = None
                        if hasattr(msg, "usage_metadata"):
                            usage_metadata = msg.usage_metadata
                        elif isinstance(msg, dict):
                            usage_metadata = msg.get("usage_metadata")

                        if usage_metadata:
                            found_usage = True
                            # 提取 token 数量
                            if isinstance(usage_metadata, dict):
                                total_prompt += usage_metadata.get("input_tokens", 0)
                                total_completion += usage_metadata.get("output_tokens", 0)
                            elif hasattr(usage_metadata, "input_tokens"):
                                total_prompt += usage_metadata.input_tokens or 0
                                total_completion += usage_metadata.output_tokens or 0

                    if found_usage:
                        return TokenUsage(
                            prompt_tokens=total_prompt,
                            completion_tokens=total_completion,
                            total_tokens=total_prompt + total_completion,
                        )
        except Exception as e:
            logger.debug(f"提取 Token 使用量失败: {e}")

        return None


# =============================================================================
# 工具加载器
# =============================================================================


async def load_local_tools(
    agent_config: Dict[str, Any],
    user_id: str,
    state: WorkflowState,
    tools: List,
) -> None:
    """加载 Local 工具（无需连接管理，直接附加到 tools 列表）"""
    local_tools = agent_config.get("local_tools", [])
    if not local_tools:
        return
    try:
        from core.market_data.managers.source_router import get_source_router
        from modules.trading_agents.tools.local_tools_adapter import create_local_tools

        logger.info(f"[Phase 1] 为智能体 {agent_config['slug']} 加载 Local 工具: {local_tools}")
        source_router = get_source_router()
        local_tool_instances = create_local_tools(
            user_id=user_id,
            source_router=source_router,
            tool_names=local_tools,
            market=state.market,
        )
        tools.extend(local_tool_instances)
        logger.info(f"[Phase 1] 创建了 {len(local_tool_instances)} 个 Local 工具")
    except Exception as e:
        logger.error(f"[Phase 1] 加载 Local 工具失败: {e}")


# =============================================================================
# 辅助函数
# =============================================================================


async def execute_phase1(
    state: WorkflowState,
    ai_service: AIService,
    config: Dict[str, Any],
    selected_agents: Optional[List[str]] = None,
    model_id: str = "claude-sonnet-4-20250514",
    max_concurrency: Optional[int] = None,
) -> WorkflowState:
    """
    执行 Phase 1: 信息收集与基础分析

    所有分析师智能体并行执行，并发数由模型配置的 task_concurrency 控制。

    Args:
        state: 工作流状态
        ai_service: AI 服务
        config: 智能体配置
        selected_agents: 用户选择的智能体 slug 列表
        model_id: 模型 ID
        max_concurrency: 最大并发数（从模型配置的 task_concurrency 获取）

    Returns:
        更新后的工作流状态
    """
    import asyncio

    # 获取 WebSocket 管理器
    from modules.trading_agents.api.websocket_manager import websocket_manager

    logger.info(f"[Phase 1] 开始执行, 任务ID: {state.task_id}")

    # 更新状态
    state.current_phase = 1
    state.status = TaskStatus.RUNNING
    state.started_at = datetime.now(timezone.utc).isoformat()

    # 获取已启用的智能体
    enabled_agents = get_enabled_agents(config, "phase1")

    # 如果用户指定了智能体，进行过滤
    if selected_agents:
        enabled_agents = [agent for agent in enabled_agents if agent["slug"] in selected_agents]

    if not enabled_agents:
        logger.warning("[Phase 1] 没有启用的智能体，跳过 Phase 1")
        # 注意：不修改 state.status，让调度器继续执行后续阶段
        return state

    concurrency_str = str(max_concurrency) if max_concurrency else "无限制"
    logger.info(f"[Phase 1] 启用 {len(enabled_agents)} 个智能体, 并发数: {concurrency_str}")

    # 发送阶段智能体列表事件
    phase_agents_event = create_phase_agents_event(
        task_id=state.task_id,
        phase=1,
        phase_name="信息收集与基础分析",
        execution_mode="concurrent",
        max_concurrency=max_concurrency or 0,
        agents=enabled_agents,
        total_executions=state.phase_agent_counts.get(1, len(enabled_agents)),
        phase_progress_weight=(
            (
                state.phase_agent_counts.get(1, len(enabled_agents))
                / state.total_agent_executions
                * 100
            )
            if state.total_agent_executions > 0
            else 0
        ),
    )
    await websocket_manager.broadcast_event(state.task_id, phase_agents_event)
    logger.info(f"[Phase 1] 已发送智能体列表事件, 智能体数量: {len(enabled_agents)}")

    # 创建智能体工厂
    factory = Phase1AgentFactory(ai_service, config)

    # 创建并发控制信号量
    semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency else None

    async def execute_single_agent(agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个智能体（带并发控制和事件发送）"""
        # 处理智能体开始
        await handle_agent_started(
            state=state,
            agent_slug=agent_config["slug"],
            agent_name=agent_config["name"],
            websocket_manager=websocket_manager,
        )

        try:
            if semaphore:
                async with semaphore:
                    result = await _execute_agent_internal(
                        factory, agent_config, state, model_id, websocket_manager
                    )
            else:
                result = await _execute_agent_internal(
                    factory, agent_config, state, model_id, websocket_manager
                )

            # 处理智能体完成
            if result and result.get("output"):
                await handle_agent_completed(
                    state=state,
                    agent_slug=agent_config["slug"],
                    agent_name=agent_config["name"],
                    output=result["output"],
                    websocket_manager=websocket_manager,
                    save_report=True,
                )

            return result
        except Exception as e:
            logger.error(f"[Phase 1] 智能体执行失败: {agent_config['slug']}, error={e}")
            return {"slug": agent_config["slug"], "error": str(e)}

    # 并发执行所有智能体
    tasks = [execute_single_agent(agent_config) for agent_config in enabled_agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"[Phase 1] 智能体执行异常: {result}")
            continue

        if not result or not isinstance(result, dict):
            continue

        # 更新状态中的分析师报告
        if result.get("output"):
            state.analyst_reports.append(
                {
                    "slug": result["slug"],
                    "name": result["name"],
                    "content": result["output"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # 更新执行记录
        if result.get("execution"):
            if not hasattr(state, "phase_executions"):
                state.phase_executions = []

            # 查找或创建 Phase 1 执行记录
            phase1_execution = next((pe for pe in state.phase_executions if pe.phase == 1), None)
            if phase1_execution is None:
                from modules.trading_agents.workflow.state import PhaseExecution

                phase1_execution = PhaseExecution(
                    phase=1,
                    phase_name="信息收集与基础分析",
                    execution_mode="concurrent",
                    max_concurrency=max_concurrency or len(enabled_agents),
                )
                state.phase_executions.append(phase1_execution)

            phase1_execution.agents.append(result["execution"])

    # 更新进度
    state.progress = 25.0  # Phase 1 完成后进度 25%

    logger.info(f"[Phase 1] 完成, 完成 {len(state.analyst_reports)} 个智能体")

    return state


async def _execute_agent_internal(
    factory: "Phase1AgentFactory",
    agent_config: Dict[str, Any],
    state: WorkflowState,
    model_id: str,
    websocket_manager: Any = None,
) -> Dict[str, Any]:
    """内部函数：执行单个智能体（MCP 连接在整个执行期间保持打开）"""
    from langchain_core.tools import BaseTool

    tools: List[BaseTool] = []

    mcp_servers = agent_config.get("mcp_servers", [])

    # MCP 工具需要在连接存活期间执行智能体，因此使用 async with 包裹整个执行过程
    if mcp_servers:
        try:
            from modules.trading_agents.tools.mcp.connector import MCPConnector

            logger.info(f"[Phase 1] 为智能体 {agent_config['slug']} 加载 MCP 工具: {mcp_servers}")

            async with MCPConnector(
                user_id=state.user_id,
                task_id=state.task_id,
                server_names=mcp_servers,
            ) as connector:
                # 连接存活期间加载工具
                mcp_tools = await connector.get_tools()
                tools.extend(mcp_tools)
                logger.info(f"[Phase 1] 从 MCP 获取了 {len(mcp_tools)} 个工具")

                # Local 工具也在此加载（与 MCP 工具合并）
                await load_local_tools(agent_config, state.user_id, state, tools)
                logger.info(f"[Phase 1] 智能体 {agent_config['slug']} 总共有 {len(tools)} 个工具")

                # 创建智能体并执行（MCP 连接在此期间保持打开）
                agent, callbacks = await factory.create_agent(
                    agent_config,
                    tools,
                    model_id,
                    user_id=state.user_id,
                    task_id=state.task_id,
                    websocket_manager=websocket_manager,
                )
                user_prompt = _build_user_prompt(state, agent_config)
                return await factory.execute_agent(
                    agent,
                    agent_config,
                    state,
                    user_prompt=user_prompt,
                    callbacks=callbacks,
                )
        except Exception as e:
            logger.error(f"[Phase 1] MCP 工具加载/执行失败: {agent_config['slug']}, error={e}")
            raise

    # 没有 MCP 工具时，直接加载 Local 工具并执行
    await load_local_tools(agent_config, state.user_id, state, tools)
    logger.info(f"[Phase 1] 智能体 {agent_config['slug']} 总共有 {len(tools)} 个工具")

    # 创建智能体（传入回调处理器用于推送工具调用事件）
    agent, callbacks = await factory.create_agent(
        agent_config,
        tools,
        model_id,
        user_id=state.user_id,
        task_id=state.task_id,
        websocket_manager=websocket_manager,
    )

    # 构建用户提示词
    user_prompt = _build_user_prompt(state, agent_config)

    # 执行智能体（传递 callbacks 以便在 ainvoke 时使用）
    result = await factory.execute_agent(
        agent,
        agent_config,
        state,
        user_prompt,
        callbacks=callbacks,
    )

    return result


def _build_user_prompt(state: WorkflowState, agent_config: Dict[str, Any]) -> str:
    """
    构建用户提示词

    Args:
        state: 工作流状态
        agent_config: 智能体配置

    Returns:
        用户提示词
    """
    prompt = f"""
请分析以下股票：

**股票代码**: {state.stock_code}
**股票名称**: {state.stock_name or '未知'}
**市场**: {state.market}
**交易日期**: {state.trade_date}

请根据你的专业领域进行分析，生成详细的分析报告。

报告要求：
1. 使用 Markdown 格式
2. 包含数据来源和时间戳
3. 基于数据和逻辑得出结论
4. 如果数据缺失，明确说明
"""

    return prompt.strip()
