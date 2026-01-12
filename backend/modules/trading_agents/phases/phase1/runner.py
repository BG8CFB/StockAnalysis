"""
Phase 1: 分析师团队运行器

动态加载分析师配置，并发执行所有启用的分析师。
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from modules.trading_agents.scheduler.state import WorkflowState


logger = logging.getLogger(__name__)


async def run_phase1(state: WorkflowState) -> WorkflowState:
    """
    运行 Phase 1: 分析师团队（并发执行）

    Args:
        state: 工作流状态

    Returns:
        更新后的工作流状态
    """
    # 获取启用的智能体列表
    agents = state.get_phase1_agents()
    logger.info(f"[Phase 1] 启用 {len(agents)} 个分析师")

    if not agents:
        logger.warning("[Phase 1] 没有启用的分析师，跳过 Phase 1")
        return state

    # 并发执行所有分析师
    tasks = [_run_single_analyst(state, agent) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"[Phase 1] 分析师 {agents[i].get('slug')} 失败: {result}")
            state.add_error("phase1", str(result), {"agent": agents[i].get('slug')})
        elif result:
            # 添加报告到状态
            state.analyst_reports.append(result)
            state.completed_analysts += 1
            logger.info(f"[Phase 1] 分析师 {result['agent_slug']} 完成")

    logger.info(f"[Phase 1] 完成，共 {len(state.analyst_reports)} 份报告")
    return state


async def _run_single_analyst(
    state: WorkflowState,
    agent_config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    运行单个分析师

    Args:
        state: 工作流状态
        agent_config: 智能体配置

    Returns:
        分析报告或 None
    """
    from core.ai import get_ai_service, AIMessage

    agent_slug = agent_config.get("slug")
    agent_name = agent_config.get("name")
    role_definition = agent_config.get("role_definition", "")
    enabled_mcp_servers = agent_config.get("enabled_mcp_servers", [])
    enabled_tools = agent_config.get("enabled_tools", [])

    logger.info(f"[{agent_name}] 开始分析 {state.stock_code}")

    try:
        # 获取工具列表
        tools = await _get_tools_for_agent(
            state,
            agent_slug,
            enabled_mcp_servers,
            enabled_tools
        )

        # 构建提示词
        prompt = _build_prompt(agent_name, role_definition, state)

        # 构建消息
        messages = [
            AIMessage(role="system", content=f"你是{agent_name}。"),
            AIMessage(role="user", content=prompt),
        ]

        # 获取模型 ID
        model_id = state.get_model_id("phase1")

        # 调用 AI 服务
        logger.info(f"[{agent_name}] 调用 AI 服务: model={model_id}")
        ai_service = get_ai_service()
        response = await ai_service.chat_completion(
            user_id=state.user_id,
            messages=messages,
            model_id=model_id,
            tools=tools if tools else None,
        )

        # 记录 Token 使用
        if response.usage:
            state.add_token_usage(
                "phase1",
                model_id,
                {
                    "prompt_tokens": response.usage.get("prompt_tokens", 0),
                    "completion_tokens": response.usage.get("completion_tokens", 0),
                    "total_tokens": response.usage.get("total_tokens", 0),
                }
            )

        # 记录工具调用
        if response.tool_calls:
            for tool_call in response.tool_calls:
                state.add_tool_call(
                    "phase1",
                    agent_slug,
                    tool_call.name if hasattr(tool_call, 'name') else str(tool_call),
                    "success"
                )

        # 构建报告
        report = {
            "agent_slug": agent_slug,
            "agent_name": agent_name,
            "content": response.content,
            "model_id": model_id,
            "timestamp": datetime.now().isoformat(),
            "tool_calls_made": len(response.tool_calls) if response.tool_calls else 0,
        }

        logger.info(f"[{agent_name}] 分析完成，Token: {response.usage.get('total_tokens', 0) if response.usage else 0}")
        return report

    except Exception as e:
        logger.error(f"[{agent_name}] 分析失败: {e}", exc_info=True)
        raise


async def _get_tools_for_agent(
    state: WorkflowState,
    agent_slug: str,
    enabled_mcp_servers: List[str],
    enabled_tools: List[str]
) -> List[Any]:
    """
    获取智能体的工具列表

    Args:
        state: 工作流状态
        agent_slug: 智能体标识
        enabled_mcp_servers: 启用的 MCP 服务器
        enabled_tools: 启用的工具列表

    Returns:
        工具列表
    """
    if not enabled_mcp_servers and not enabled_tools:
        return []

    # TODO: 从 MCP 模块获取工具
    # 目前返回空列表，后续集成 MCP 工具

    logger.debug(
        f"[Phase 1] agent={agent_slug}, "
        f"mcp_servers={len(enabled_mcp_servers)}, "
        f"tools={len(enabled_tools)}"
    )
    return []


def _build_prompt(
    agent_name: str,
    role_definition: str,
    state: WorkflowState
) -> str:
    """
    构建分析师提示词

    Args:
        agent_name: 分析师名称
        role_definition: 角色定义（从配置加载）
        state: 工作流状态

    Returns:
        提示词字符串
    """
    base_info = f"""
## 股票信息
- 股票代码：{state.stock_code}
- 交易日期：{state.trade_date}
- 任务 ID：{state.task_id}
"""

    prompt = f"""{role_definition}

{base_info}

请严格按照你的角色定义，生成专业的分析报告（Markdown 格式）。
"""
    return prompt
