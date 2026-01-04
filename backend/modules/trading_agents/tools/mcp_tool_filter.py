"""
MCP 工具过滤模块

根据智能体配置过滤 MCP 工具，管理连接获取和释放。
实现连接缓存机制，确保同一任务、同一服务器只创建一个连接。
"""

import logging
from typing import List, Dict, Any, Optional, Set

from langchain_core.tools import BaseTool

from modules.mcp.pool.pool import get_mcp_connection_pool, MCPConnectionPool
from modules.mcp.pool.connection import MCPConnection
from modules.mcp.service.mcp_service import get_mcp_service, MCPService
from modules.trading_agents.schemas import AgentConfig
from modules.trading_agents.tools.registry import ToolDefinition, ToolStatus

logger = logging.getLogger(__name__)


class MCPToolFilter:
    """
    MCP 工具过滤器（带连接缓存）

    根据智能体配置的 `enabled_mcp_servers` 过滤可用的 MCP 工具，
    并管理连接的获取和释放。

    连接缓存机制：
    - 确保同一任务、同一服务器只创建一个连接
    - 多个智能体可以复用同一连接
    - 任务完成时统一释放所有连接
    """

    def __init__(self):
        """初始化工具过滤器"""
        self._pool: MCPConnectionPool = get_mcp_connection_pool()
        self._mcp_service: MCPService = get_mcp_service()

        # 连接缓存：{task_id: {server_id: connection}}
        # 确保同一任务、同一服务器只创建一个连接
        self._connection_cache: Dict[str, Dict[str, MCPConnection]] = {}

        # 连接引用计数：{task_id: {server_id: ref_count}}
        # 记录每个连接被多少智能体使用
        self._connection_refs: Dict[str, Dict[str, int]] = {}

    async def get_tools_for_agent(
        self,
        agent_config: AgentConfig,
        user_id: str,
        task_id: str,
        all_tools: List[ToolDefinition],
    ) -> List[BaseTool]:
        """
        获取智能体可用的 MCP 工具（支持容错配置 + 连接缓存）

        连接缓存机制：
        - 检查缓存中是否已有该服务器的连接
        - 如果有，复用连接并增加引用计数
        - 如果没有，从连接池获取新连接并缓存

        Args:
            agent_config: 智能体配置（enabled_mcp_servers 支持必需性标记）
            user_id: 用户 ID
            task_id: 任务 ID
            all_tools: 所有已注册的工具定义

        Returns:
            过滤后的 LangChain 工具列表

        Raises:
            RuntimeError: 当必需 MCP 服务器不可用时
        """
        # 获取用户可用的 MCP 服务器（已启用且可用状态）
        available_servers = await self._get_available_servers(user_id)

        # 智能体启用的 MCP 服务器配置（新格式：支持 required 标记）
        enabled_server_configs = agent_config.enabled_mcp_servers

        # 向后兼容：如果是旧格式（List[str]），转换为 MCPServerConfig
        if enabled_server_configs and isinstance(enabled_server_configs[0], str):
            from modules.trading_agents.schemas import MCPServerConfig
            enabled_server_configs = MCPServerConfig.from_list(enabled_server_configs)

        # 提取服务器名称和必需性标记
        enabled_server_names = set()
        required_server_names = set()

        if enabled_server_configs:
            for config in enabled_server_configs:
                if isinstance(config, str):
                    enabled_server_names.add(config)
                else:
                    enabled_server_names.add(config.name)
                    if config.required:
                        required_server_names.add(config.name)

        # 区分三种情况（修复空配置处理）
        if enabled_server_configs is None:
            # 情况1：未配置（None），使用所有可用服务器（向后兼容）
            valid_server_names = set(available_servers.keys())
            logger.info(
                f"智能体 {agent_config.slug} 未配置 MCP 服务器，"
                f"使用所有可用服务器: {valid_server_names}"
            )

        elif len(enabled_server_names) == 0:
            # 情况2：明确配置为空列表，不使用任何服务器
            valid_server_names = set()
            logger.info(f"智能体 {agent_config.slug} 明确配置不使用任何 MCP 服务器")

        else:
            # 情况3：明确配置了服务器列表
            valid_server_names = enabled_server_names & available_servers.keys()
            logger.info(
                f"智能体 {agent_config.slug} 使用配置的 MCP 服务器: {valid_server_names}"
            )

        # 检查必需服务器是否可用（必须在返回之前检查）
        missing_required = required_server_names - valid_server_names
        if missing_required:
            # 用户要求：如果管理员关闭了MCP，智能体应忽略该缺失，继续运行
            # 原逻辑会抛出 RuntimeError，现改为记录警告并忽略
            logger.warning(
                f"智能体 {agent_config.slug} 的部分必需 MCP 服务器全局不可用（已忽略）: {missing_required}。"
                f"将仅使用可用的服务器: {valid_server_names}"
            )

        if not valid_server_names:
            logger.info(
                f"智能体 {agent_config.slug} 没有可用的 MCP 服务器。"
                f"用户可用: {list(available_servers.keys())}, "
                f"智能体配置: {enabled_server_names if enabled_server_names else '未配置（默认全开）'}"
            )
            return []

        # 获取这些服务器的连接并转换为 LangChain 工具
        langchain_tools = []

        for server_name in valid_server_names:
            server_id = available_servers[server_name]

            try:
                # 🔑 连接缓存：检查是否已有连接
                connection = await self._get_or_create_connection(
                    task_id=task_id,
                    server_id=server_id,
                    user_id=user_id
                )

                # 获取 LangChain 工具列表
                connection_tools = connection.tools

                # 过滤出属于此服务器的工具
                for tool in connection_tools:
                    # 确保工具来自正确的服务器
                    tool_def = self._find_tool_definition(all_tools, tool.name)
                    if tool_def and tool_def.mcp_server == server_name:
                        langchain_tools.append(tool)

                logger.debug(
                    f"为智能体 {agent_config.slug} 获取了 {len(connection_tools)} 个工具 "
                    f"from MCP 服务器: {server_name} (连接ID: {connection.connection_id[:8]}...)"
                )

            except Exception as e:
                # 检查此服务器是否是必需的
                is_required = any(
                    config.name == server_name and config.required
                    for config in enabled_server_configs
                )

                if is_required:
                    # 必需服务器失败，抛出异常
                    raise RuntimeError(
                        f"智能体 {agent_config.slug} 的必需 MCP 服务器 '{server_name}' 连接失败: {e}"
                    ) from e
                else:
                    # 可选服务器失败，记录警告并继续
                    logger.warning(
                        f"智能体 {agent_config.slug} 的可选 MCP 服务器 '{server_name}' 连接失败（已跳过）: {e}"
                    )
                    continue

        logger.info(
            f"智能体 {agent_config.slug} 总共获取了 {len(langchain_tools)} 个 MCP 工具"
        )
        return langchain_tools

    async def _get_or_create_connection(
        self,
        task_id: str,
        server_id: str,
        user_id: str
    ) -> MCPConnection:
        """
        获取或创建连接（带缓存）

        连接生命周期：连接由任务管理，任务结束时统一释放。

        Args:
            task_id: 任务 ID
            server_id: 服务器 ID
            user_id: 用户 ID

        Returns:
            MCP 连接对象
        """
        # 初始化任务缓存
        if task_id not in self._connection_cache:
            self._connection_cache[task_id] = {}
            self._connection_refs[task_id] = {}

        # 检查缓存中是否已有连接
        if server_id in self._connection_cache[task_id]:
            connection = self._connection_cache[task_id][server_id]
            # 增加引用计数（跟踪任务内复用次数）
            self._connection_refs[task_id][server_id] += 1
            logger.debug(
                f"复用 MCP 连接: task_id={task_id}, server_id={server_id}, "
                f"connection_id={connection.connection_id[:8]}..., "
                f"ref_count={self._connection_refs[task_id][server_id]}"
            )
            return connection

        # 从连接池获取新连接
        connection = await self._pool.acquire_connection(
            server_id=server_id,
            task_id=task_id,
            user_id=user_id
        )

        # 缓存连接
        self._connection_cache[task_id][server_id] = connection
        self._connection_refs[task_id][server_id] = 1

        logger.info(
            f"创建新 MCP 连接: task_id={task_id}, server_id={server_id}, "
            f"connection_id={connection.connection_id[:8]}..."
        )

        return connection

    async def release_connection_for_task(self, task_id: str) -> None:
        """
        释放任务的所有 MCP 连接

        连接生命周期由任务管理，任务结束时统一释放所有连接。
        引用计数用于跟踪任务内连接复用情况。

        Args:
            task_id: 任务 ID
        """
        if task_id not in self._connection_cache:
            return

        logger.info(f"开始释放任务 {task_id} 的 MCP 连接")

        for server_id, connection in self._connection_cache[task_id].items():
            try:
                await self._pool.release_connection(connection.connection_id)
                logger.debug(
                    f"已释放 MCP 连接: connection_id={connection.connection_id[:8]}..., "
                    f"server_id={server_id}"
                )
            except Exception as e:
                logger.warning(
                    f"释放 MCP 连接失败: connection_id={connection.connection_id[:8]}..., error={e}"
                )

        # 清理缓存
        del self._connection_cache[task_id]
        del self._connection_refs[task_id]

        logger.info(f"任务 {task_id} 的 MCP 连接已全部释放")

    async def mark_task_complete(self, task_id: str) -> None:
        """
        标记任务完成，触发连接的延迟销毁（10秒）

        Args:
            task_id: 任务 ID
        """
        if task_id not in self._connection_cache:
            return

        logger.info(f"标记任务 {task_id} 完成，延迟释放 MCP 连接")

        for server_id, connection in self._connection_cache[task_id].items():
            try:
                await self._pool.mark_task_complete(task_id)
                logger.debug(
                    f"标记连接完成: connection_id={connection.connection_id[:8]}..., "
                    f"server_id={server_id}"
                )
            except Exception as e:
                logger.warning(
                    f"标记连接完成失败: connection_id={connection.connection_id[:8]}..., error={e}"
                )

    async def mark_task_failed(self, task_id: str) -> None:
        """
        标记任务失败，触发连接的延迟销毁（30秒）

        Args:
            task_id: 任务 ID
        """
        if task_id not in self._connection_cache:
            return

        logger.info(f"标记任务 {task_id} 失败，延迟释放 MCP 连接")

        for server_id, connection in self._connection_cache[task_id].items():
            try:
                await self._pool.mark_task_failed(task_id)
                logger.debug(
                    f"标记连接失败: connection_id={connection.connection_id[:8]}..., "
                    f"server_id={server_id}"
                )
            except Exception as e:
                logger.warning(
                    f"标记连接失败失败: connection_id={connection.connection_id[:8]}..., error={e}"
                )

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
