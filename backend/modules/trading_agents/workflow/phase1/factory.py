"""
Phase 1 智能体工厂

动态创建分析师智能体，使用 LangChain 0.3+ create_agent 接口。

**版本**: v6.0 (LangChain 0.3+ create_agent 重构版)
**最后更新**: 2025-01-19
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage

from core.ai.service import AIService
from modules.trading_agents.config import get_enabled_agents
from modules.trading_agents.models.state import (
    AgentExecution,
    TaskStatus,
    WorkflowState,
)
from modules.trading_agents.workflow.events import (
    EventType,
    create_event,
    create_phase_agents_event,
    create_agent_started_event,
    create_agent_completed_event,
    create_progress_update_event,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 1 智能体工厂
# =============================================================================

class Phase1AgentFactory:
    """
    Phase 1 智能体工厂

    动态创建分析师智能体，支持并发执行。
    """

    def __init__(
        self,
        ai_service: AIService,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化智能体工厂

        Args:
            ai_service: AI 服务
            config: 智能体配置
        """
        self.ai_service = ai_service
        self.config = config or {}

    def create_agent(
        self,
        agent_config: Dict[str, Any],
        tools: List[BaseTool],
        model_id: str
    ):
        """
        创建单个智能体 (LangChain 0.3+ create_agent API)

        Args:
            agent_config: 智能体配置
            tools: 工具列表
            model_id: 模型 ID

        Returns:
            AgentExecutor 实例
        """
        # 获取 LLM 模型
        model = self.ai_service.get_model(model_id)

        # 构建系统提示词
        system_prompt_str = self._build_system_prompt(agent_config)

        # 使用 LangChain 0.3+ 的 create_agent
        agent = create_agent(
            model,
            tools,
            system_prompt=system_prompt_str
        )

        logger.debug(
            f"创建智能体: {agent_config['slug']} "
            f"({agent_config['name']}), "
            f"工具数: {len(tools)}, "
            f"模型: {model_id}"
        )

        return agent

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
        agent,
        agent_config: Dict[str, Any],
        state: WorkflowState,
        user_prompt: str
    ) -> Dict[str, Any]:
        """
        执行智能体

        Args:
            agent: AgentExecutor 实例 (LangChain 0.3+ create_agent)
            agent_config: 智能体配置
            state: 工作流状态
            user_prompt: 用户提示词

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
            started_at=datetime.utcnow()
        )

        try:
            # 调用 agent (LangChain 0.3+ 使用 messages 格式)
            logger.info(f"[Phase 1] 执行智能体: {agent_slug} ({agent_name})")

            # LangChain 0.3+ 使用 messages 格式
            inputs = {
                "messages": [
                    HumanMessage(content=user_prompt)
                ]
            }

            result = await agent.ainvoke(inputs)

            # 提取输出
            output = self._extract_output(result)

            # 更新执行记录
            execution.completed_at = datetime.utcnow()
            execution.status = TaskStatus.COMPLETED
            execution.output = output

            # TODO: 提取 Token 使用量（从 LLM 响应中）
            # execution.token_usage = TokenUsage(...)

            logger.info(
                f"[Phase 1] 智能体完成: {agent_slug} ({agent_name}), "
                f"输出长度: {len(output) if output else 0}"
            )

            return {
                "slug": agent_slug,
                "name": agent_name,
                "output": output,
                "execution": execution,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 1] 智能体失败: {agent_slug} ({agent_name}), error={e}")

            execution.completed_at = datetime.utcnow()
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)

            return {
                "slug": agent_slug,
                "name": agent_name,
                "output": None,
                "execution": execution,
                "error": str(e)
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
                    return last_message.content
                # 处理字典格式
                elif isinstance(last_message, dict):
                    return last_message.get("content", "")

        # 直接返回字符串
        if isinstance(result, str):
            return result

        return str(result)


# =============================================================================
# 工具加载器
# =============================================================================

async def load_agent_tools(
    agent_config: Dict[str, Any],
    user_id: str,
    state: WorkflowState
) -> List:
    """
    为智能体加载工具（MCP + Local）

    Args:
        agent_config: 智能体配置
        user_id: 用户 ID
        state: 工作流状态

    Returns:
        工具列表
    """
    from langchain_core.tools import BaseTool

    tools: List[BaseTool] = []

    # 1. 加载 MCP 工具
    mcp_servers = agent_config.get("mcp_servers", [])
    if mcp_servers:
        try:
            from modules.trading_agents.tools.mcp.connector import MCPConnector

            logger.info(f"[Phase 1] 为智能体 {agent_config['slug']} 加载 MCP 工具: {mcp_servers}")

            async with MCPConnector(
                user_id=user_id,
                task_id=state.task_id,
                server_names=mcp_servers
            ) as connector:
                mcp_tools = await connector.get_tools()
                tools.extend(mcp_tools)
                logger.info(f"[Phase 1] 从 MCP 获取了 {len(mcp_tools)} 个工具")
        except Exception as e:
            logger.error(f"[Phase 1] 加载 MCP 工具失败: {e}")

    # 2. 加载 Local 工具
    local_tools = agent_config.get("local_tools", [])
    if local_tools:
        try:
            from core.market_data.managers.source_router import get_source_router
            from modules.trading_agents.tools.local_tools_adapter import create_local_tools

            logger.info(f"[Phase 1] 为智能体 {agent_config['slug']} 加载 Local 工具: {local_tools}")

            # 获取数据源路由器
            source_router = get_source_router()

            # 创建 Local 工具
            local_tool_instances = create_local_tools(
                user_id=user_id,
                source_router=source_router,
                tool_names=local_tools
            )
            tools.extend(local_tool_instances)
            logger.info(f"[Phase 1] 创建了 {len(local_tool_instances)} 个 Local 工具")
        except Exception as e:
            logger.error(f"[Phase 1] 加载 Local 工具失败: {e}")

    logger.info(f"[Phase 1] 智能体 {agent_config['slug']} 总共有 {len(tools)} 个工具")
    return tools


# =============================================================================
# 辅助函数
# =============================================================================

async def execute_phase1(
    state: WorkflowState,
    ai_service: AIService,
    config: Dict[str, Any],
    selected_agents: Optional[List[str]] = None,
    model_id: str = "claude-sonnet-4-20250514",
    max_concurrency: Optional[int] = None
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
    state.started_at = datetime.utcnow()

    # 获取已启用的智能体
    enabled_agents = get_enabled_agents(config, "phase1")

    # 如果用户指定了智能体，进行过滤
    if selected_agents:
        enabled_agents = [
            agent for agent in enabled_agents
            if agent["slug"] in selected_agents
        ]

    if not enabled_agents:
        logger.warning("[Phase 1] 没有启用的智能体")
        state.status = TaskStatus.COMPLETED
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
        agents=enabled_agents
    )
    await websocket_manager.broadcast_event(state.task_id, phase_agents_event)
    logger.info(f"[Phase 1] 已发送智能体列表事件, 智能体数量: {len(enabled_agents)}")

    # 创建智能体工厂
    factory = Phase1AgentFactory(ai_service, config)

    # 创建并发控制信号量
    semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency else None

    async def execute_single_agent(agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个智能体（带并发控制和事件发送）"""
        # 发送智能体开始事件
        agent_started_event = create_agent_started_event(
            task_id=state.task_id,
            agent_slug=agent_config["slug"],
            agent_name=agent_config["name"]
        )
        await websocket_manager.broadcast_event(state.task_id, agent_started_event)
        logger.info(f"[Phase 1] 智能体开始: {agent_config['slug']} ({agent_config['name']})")

        try:
            if semaphore:
                async with semaphore:
                    result = await _execute_agent_internal(factory, agent_config, state, model_id)
            else:
                result = await _execute_agent_internal(factory, agent_config, state, model_id)

            # 发送智能体完成事件
            if result and result.get("output"):
                agent_completed_event = create_agent_completed_event(
                    task_id=state.task_id,
                    agent_slug=agent_config["slug"],
                    agent_name=agent_config["name"],
                    token_usage={}  # 暂无 token 用量
                )
                await websocket_manager.broadcast_event(state.task_id, agent_completed_event)
                logger.info(f"[Phase 1] 智能体完成: {agent_config['slug']}")

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

        if not result:
            continue

        # 更新状态中的分析师报告
        if result.get("output"):
            state.analyst_reports.append({
                "slug": result["slug"],
                "name": result["name"],
                "content": result["output"],
                "timestamp": datetime.utcnow().isoformat()
            })

        # 更新执行记录
        if result.get("execution"):
            if not hasattr(state, 'phase_executions'):
                state.phase_executions = []

            # 查找或创建 Phase 1 执行记录
            phase1_execution = next(
                (pe for pe in state.phase_executions if pe.phase == 1),
                None
            )
            if phase1_execution is None:
                from modules.trading_agents.models.state import PhaseExecution
                phase1_execution = PhaseExecution(
                    phase=1,
                    phase_name="信息收集与基础分析",
                    execution_mode="concurrent",
                    max_concurrency=max_concurrency or len(enabled_agents)
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
    model_id: str
) -> Dict[str, Any]:
    """内部函数：执行单个智能体"""
    # 加载工具（MCP + Local）
    tools = await load_agent_tools(agent_config, state.user_id, state)

    # 创建智能体
    agent = factory.create_agent(
        agent_config,
        tools,
        model_id
    )

    # 构建用户提示词
    user_prompt = _build_user_prompt(state, agent_config)

    # 执行智能体
    result = await factory.execute_agent(
        agent,
        agent_config,
        state,
        user_prompt
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
