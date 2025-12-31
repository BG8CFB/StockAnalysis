"""
MCP 工具过滤模块

根据智能体配置过滤 MCP 工具，管理连接获取和释放。
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.tools import BaseTool

from modules.mcp.pool.pool import get_mcp_connection_pool, MCPConnectionPool
from modules.mcp.service.mcp_service import get_mcp_service, MCPService
from modules.trading_agents.schemas import AgentConfig
from modules.trading_agents.tools.registry import ToolDefinition, ToolStatus

logger = logging.getLogger(__name__)


class MCPToolFilter:
    """
    MCP 工具过滤器

    根据智能体配置的 `enabled_mcp_servers` 过滤可用的 MCP 工具，
    并管理连接的获取和释放。
    """

    def __init__(self):
        """初始化工具过滤器"""
        self._pool: MCPConnectionPool = get_mcp_connection_pool()
        self._mcp_service: MCPService = get_mcp_service()
        self._active_connections: Dict[str, str] = {}  # {task_id: connection_id}

    async def get_tools_for_agent(
        self,
        agent_config: AgentConfig,
        user_id: str,
        task_id: str,
        all_tools: List[ToolDefinition],
    ) -> List[BaseTool]:
        """
        获取智能体可用的 MCP 工具

        Args:
            agent_config: 智能体配置
            user_id: 用户 ID
            task_id: 任务 ID
            all_tools: 所有已注册的工具定义

        Returns:
            过滤后的 LangChain 工具列表
        """
        # 获取用户可用的 MCP 服务器（已启用且可用状态）
        available_servers = await self._get_available_servers(user_id)

        # 智能体启用的 MCP 服务器（按名称）
        enabled_server_names = set(agent_config.enabled_mcp_servers)

        # 取交集：用户可用 AND 智能体启用
        valid_server_names = enabled_server_names & available_servers.keys()

        if not valid_server_names:
            logger.info(
                f"智能体 {agent_config.slug} 没有可用的 MCP 服务器。"
                f"用户可用: {list(available_servers.keys())}, "
                f"智能体启用: {enabled_server_names}"
            )
            return []

        # 获取这些服务器的连接并转换为 LangChain 工具
        langchain_tools = []

        for server_name in valid_server_names:
            server_id = available_servers[server_name]

            try:
                # 从连接池获取连接
                connection = await self._pool.acquire_connection(
                    server_id=server_id,
                    task_id=task_id,
                    user_id=user_id
                )

                # 记录活跃连接
                self._active_connections[task_id] = connection.connection_id

                # 获取 LangChain 工具列表
                connection_tools = connection.tools

                # 过滤出属于此服务器的工具
                for tool in connection_tools:
                    # 确保工具来自正确的服务器
                    tool_def = self._find_tool_definition(all_tools, tool.name)
                    if tool_def and tool_def.mcp_server == server_name:
                        langchain_tools.append(tool)

                logger.info(
                    f"为智能体 {agent_config.slug} 获取了 {len(connection_tools)} 个工具 "
                    f"from MCP 服务器: {server_name}"
                )

            except Exception as e:
                logger.error(
                    f"获取 MCP 服务器工具失败: server={server_name}, error={e}",
                    exc_info=True
                )
                # 继续尝试其他服务器

        return langchain_tools

    async def release_connection_for_task(self, task_id: str) -> None:
        """
        释放任务的 MCP 连接

        Args:
            task_id: 任务 ID
        """
        connection_id = self._active_connections.pop(task_id, None)
        if connection_id:
            await self._pool.release_connection(connection_id)
            logger.info(f"已释放任务 {task_id} 的 MCP 连接: {connection_id}")

    async def mark_task_complete(self, task_id: str) -> None:
        """
        标记任务完成，触发连接的延迟销毁（10秒）

        Args:
            task_id: 任务 ID
        """
        connection_id = self._active_connections.get(task_id)
        if connection_id:
            connection = self._pool._connections.get(connection_id)
            if connection:
                await connection.mark_complete()
                logger.info(f"任务 {task_id} 完成，连接将在 10 秒后销毁")

    async def mark_task_failed(self, task_id: str) -> None:
        """
        标记任务失败，触发连接的延迟销毁（30秒）

        Args:
            task_id: 任务 ID
        """
        connection_id = self._active_connections.get(task_id)
        if connection_id:
            connection = self._pool._connections.get(connection_id)
            if connection:
                await connection.mark_failed()
                logger.info(f"任务 {task_id} 失败，连接将在 30 秒后销毁")

    async def _get_available_servers(self, user_id: str) -> Dict[str, str]:
        """
        获取用户可用的 MCP 服务器

        Args:
            user_id: 用户 ID

        Returns:
            {server_name: server_id} 字典
        """
        is_admin = False  # TODO: 从上下文获取用户角色
        servers_response = await self._mcp_service.list_servers(user_id, is_admin)

        available_servers = {}

        # 系统级服务器 + 用户自己的服务器
        for server in servers_response.get("system", []):
            if server.enabled and server.status.value == "available":
                available_servers[server.name] = server.id

        for server in servers_response.get("user", []):
            if server.enabled and server.status.value == "available":
                available_servers[server.name] = server.id

        return available_servers

    def _find_tool_definition(
        self,
        all_tools: List[ToolDefinition],
        tool_name: str
    ) -> Optional[ToolDefinition]:
        """
        查找工具定义

        Args:
            all_tools: 所有工具定义
            tool_name: 工具名称

        Returns:
            工具定义或 None
        """
        for tool in all_tools:
            if tool.name == tool_name:
                return tool
        return None


# =============================================================================
# 全局工具过滤器实例
# =============================================================================

_mcp_tool_filter: Optional[MCPToolFilter] = None


def get_mcp_tool_filter() -> MCPToolFilter:
    """获取全局 MCP 工具过滤器实例"""
    global _mcp_tool_filter
    if _mcp_tool_filter is None:
        _mcp_tool_filter = MCPToolFilter()
    return _mcp_tool_filter


# =============================================================================
# 便捷函数
# =============================================================================

async def filter_tools_for_agent(
    agent_config: AgentConfig,
    user_id: str,
    task_id: str,
    all_tools: List[ToolDefinition],
) -> List[BaseTool]:
    """
    为智能体过滤 MCP 工具（便捷函数）

    Args:
        agent_config: 智能体配置
        user_id: 用户 ID
        task_id: 任务 ID
        all_tools: 所有已注册的工具定义

    Returns:
        过滤后的 LangChain 工具列表
    """
    filter_instance = get_mcp_tool_filter()
    return await filter_instance.get_tools_for_agent(
        agent_config=agent_config,
        user_id=user_id,
        task_id=task_id,
        all_tools=all_tools,
    )


async def release_task_connection(task_id: str) -> None:
    """
    释放任务的 MCP 连接（便捷函数）

    Args:
        task_id: 任务 ID
    """
    filter_instance = get_mcp_tool_filter()
    await filter_instance.release_connection_for_task(task_id)


async def complete_task_connection(task_id: str) -> None:
    """
    标记任务完成，触发连接延迟销毁（便捷函数）

    Args:
        task_id: 任务 ID
    """
    filter_instance = get_mcp_tool_filter()
    await filter_instance.mark_task_complete(task_id)


async def fail_task_connection(task_id: str) -> None:
    """
    标记任务失败，触发连接延迟销毁（便捷函数）

    Args:
        task_id: 任务 ID
    """
    filter_instance = get_mcp_tool_filter()
    await filter_instance.mark_task_failed(task_id)


# 函数别名（复数形式，用于与任务管理器接口一致）
release_task_connections = release_task_connection
complete_task_connections = complete_task_connection
fail_task_connections = fail_task_connection
