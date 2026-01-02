"""
阶段1智能体实现 - 工厂模式

分析师团队智能体，负责从不同角度分析股票。
采用工厂模式动态创建，支持自定义配置。
"""

import logging
from typing import List, Dict, Any, Optional, Union

from langchain_core.tools import BaseTool

from modules.trading_agents.agents.base import AnalystAgent
from core.ai.llm.provider import LLMProvider
from modules.trading_agents.tools.registry import ToolRegistry, ToolDefinition
from modules.trading_agents.schemas import Phase1Config, AgentConfig
from modules.trading_agents.tools.mcp_tool_filter import filter_tools_for_agent

logger = logging.getLogger(__name__)


# =============================================================================
# 通用分析师模板
# =============================================================================

class GenericAnalystTemplate(AnalystAgent):
    """
    通用分析师模板
    
    所有第一阶段分析师都使用此模板实例化，通过配置区分角色。
    """

    def __init__(
        self,
        slug: str,
        name: str,
        role_definition: str,
        llm: LLMProvider,
        tools: Optional[List[Any]] = None  # 改为 Any，支持 BaseTool
    ):
        """
        初始化通用分析师

        Args:
            slug: 唯一标识
            name: 显示名称
            role_definition: 角色定义 (Prompt)
            llm: LLM Provider
            tools: 工具列表（LangChain BaseTool）
        """
        super().__init__(
            slug=slug,
            name=name,
            role_definition=role_definition,
            llm=llm,
            tools=tools,
        )


# =============================================================================
# 分析师工厂
# =============================================================================

class AnalystFactory:
    """
    分析师工厂

    负责根据配置动态创建分析师智能体实例。
    """

    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry):
        self.llm = llm_provider
        self.tool_registry = tool_registry
        # 注入 MCP 工具过滤器
        from modules.trading_agents.tools.mcp_tool_filter import get_mcp_tool_filter
        self.mcp_filter = get_mcp_tool_filter()

    async def create_analysts(
        self,
        config: Phase1Config,
        user_id: str,
        task_id: str,
    ) -> List[AnalystAgent]:
        """
        根据配置创建分析师列表（异步方法）

        Args:
            config: 第一阶段配置
            user_id: 用户 ID（用于 MCP 连接池）
            task_id: 任务 ID（用于 MCP 连接池）

        Returns:
            分析师实例列表
        """
        analysts = []

        if not config.enabled:
            return []

        if not user_id or not task_id:
            raise ValueError("user_id 和 task_id 是必需的")

        for agent_cfg in config.agents:
            if not agent_cfg.enabled:
                continue

            # 获取可执行的 LangChain 工具（通过 MCP 过滤器）
            langchain_tools = await self._get_tools_for_agent(
                agent_cfg=agent_cfg,
                user_id=user_id,
                task_id=task_id,
            )

            # 创建实例（传递 BaseTool 列表，不是 ToolDefinition）
            analyst = GenericAnalystTemplate(
                slug=agent_cfg.slug,
                name=agent_cfg.name,
                role_definition=agent_cfg.role_definition,
                llm=self.llm,
                tools=langchain_tools,  # 类型：List[BaseTool]
            )

            analysts.append(analyst)
            logger.info(
                f"创建分析师智能体: {analyst.name} ({analyst.slug}), "
                f"MCP服务器: {agent_cfg.enabled_mcp_servers}, 工具数: {len(langchain_tools)}"
            )

        return analysts

    async def _get_tools_for_agent(
        self,
        agent_cfg: AgentConfig,
        user_id: str,
        task_id: str,
    ) -> List[Any]:
        """
        根据智能体配置获取可执行的 LangChain 工具

        Args:
            agent_cfg: 智能体配置
            user_id: 用户 ID
            task_id: 任务 ID

        Returns:
            LangChain BaseTool 列表（可执行）
        """
        tools: List[Any] = []

        # 1. 通过 MCP 工具过滤器获取可执行的工具（带连接）
        # 注意：即使 enabled_mcp_servers 为空，也会使用所有可用服务器（默认全开）
        try:
            langchain_tools = await self.mcp_filter.get_tools_for_agent(
                agent_config=agent_cfg,
                user_id=user_id,
                task_id=task_id,
                all_tools=self.tool_registry.list_all_tools(),
            )

            tools.extend(langchain_tools)
            logger.info(
                f"智能体 {agent_cfg.slug} 获取到 {len(langchain_tools)} 个 MCP 工具 "
                f"(配置服务器: {agent_cfg.enabled_mcp_servers if agent_cfg.enabled_mcp_servers else '默认全部'})"
            )
        except Exception as e:
            logger.error(
                f"获取 MCP 工具失败: agent={agent_cfg.slug}, error={e}",
                exc_info=True
            )
            # 继续执行，不中断整个流程

        # 2. 获取本地工具（如果有）
        if agent_cfg.enabled_local_tools:
            from langchain_core.tools import StructuredTool

            for tool_name in agent_cfg.enabled_local_tools:
                tool_def = self.tool_registry.get_tool(tool_name)
                if tool_def and tool_def.handler:
                    # 将本地工具包装为 LangChain BaseTool
                    langchain_tool = StructuredTool.from_function(
                        func=tool_def.handler,
                        name=tool_def.name,
                        description=tool_def.description,
                    )
                    tools.append(langchain_tool)
                elif tool_def:
                    logger.warning(
                        f"智能体 {agent_cfg.slug} 配置的本地工具没有处理器: {tool_name}"
                    )
                else:
                    logger.warning(
                        f"智能体 {agent_cfg.slug} 配置的本地工具不存在: {tool_name}"
                    )

        return tools
