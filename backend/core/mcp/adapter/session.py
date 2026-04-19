"""
MCP 会话管理（官方标准实现）

基于 langchain-mcp-adapters 官方推荐的 Session 上下文管理器模式。

官方文档: https://docs.langchain.com/oss/python/langchain/mcp#stateful-sessions
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.tools import load_mcp_tools

logger = logging.getLogger(__name__)


# =============================================================================
# 官方推荐的 Session 上下文管理器
# =============================================================================


@asynccontextmanager
async def mcp_session_context(
    client: MultiServerMCPClient,
    server_name: str,
) -> AsyncGenerator[Any, None]:
    """
    MCP Session 上下文管理器（官方标准实现）

    使用官方的 client.session() 上下文管理器，提供：
    - 自动资源清理
    - 状态持久化
    - 多工具调用间保持状态

    Args:
        client: MultiServerMCPClient 实例
        server_name: MCP 服务器名称

    Yields:
        原始 Session 对象（可用于 load_mcp_tools 等）

    Example:
        ```python
        client = MultiServerMCPClient({...})

        async with mcp_session_context(client, "finance") as session:
            # 加载工具（带状态）
            tools = await load_mcp_tools(session)

            # 多个工具调用共享同一会话状态
            result1 = await session.call_tool("get_stock", {"symbol": "AAPL"})
            result2 = await session.call_tool("get_price", {"symbol": "AAPL"})
        ```
    """
    session = None
    try:
        logger.debug(f"[MCPSession] 创建会话: server={server_name}")

        # 使用官方的 session() 上下文管理器
        async with client.session(server_name) as session:
            logger.info(f"[MCPSession] 会话已创建: server={server_name}")
            yield session

    except Exception as e:
        logger.error(f"[MCPSession] 会话错误: server={server_name}, error={e}", exc_info=True)
        raise
    finally:
        if session:
            logger.debug(f"[MCPSession] 会话已清理: server={server_name}")


# =============================================================================
# 官方推荐的资源加载函数
# =============================================================================


async def load_tools_with_session(
    client: MultiServerMCPClient,
    server_name: str,
) -> List[BaseTool]:
    """
    使用有状态会话加载 MCP 工具（官方标准方式）

    Args:
        client: MultiServerMCPClient 实例
        server_name: MCP 服务器名称

    Returns:
        LangChain 工具列表

    Example:
        ```python
        client = create_mcp_client({...})
        tools = await load_tools_with_session(client, "finance")
        ```
    """
    async with mcp_session_context(client, server_name) as session:
        tools = await load_mcp_tools(session)
        logger.info(f"[MCPSession] 加载工具: server={server_name}, count={len(tools)}")
        return list(tools)


async def load_resources_with_session(
    client: MultiServerMCPClient,
    server_name: str,
    uris: Optional[List[str]] = None,
) -> List[Any]:
    """
    使用有状态会话加载 MCP 资源（官方标准方式）

    Args:
        client: MultiServerMCPClient 实例
        server_name: MCP 服务器名称
        uris: 可选，要加载的资源 URI 列表

    Returns:
        Blob 对象列表

    Example:
        ```python
        # 加载所有资源
        resources = await load_resources_with_session(client, "finance")

        # 加载特定资源
        resources = await load_resources_with_session(
            client, "finance",
            uris=["file:///data/stock_list.csv"]
        )
        ```
    """
    async with mcp_session_context(client, server_name) as session:
        if uris:
            resources = await load_mcp_resources(session, uris=uris)
        else:
            resources = await load_mcp_resources(session)

        logger.info(f"[MCPSession] 加载资源: server={server_name}, count={len(resources)}")
        return list(resources)


async def load_prompt_with_session(
    client: MultiServerMCPClient,
    server_name: str,
    prompt_name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> List[Any]:
    """
    使用有状态会话加载 MCP Prompt（官方标准方式）

    Args:
        client: MultiServerMCPClient 实例
        server_name: MCP 服务器名称
        prompt_name: Prompt 名称
        arguments: 可选，Prompt 参数

    Returns:
        Message 列表

    Example:
        ```python
        # 加载默认 prompt
        messages = await load_prompt_with_session(client, "finance", "summarize")

        # 加载带参数的 prompt
        messages = await load_prompt_with_session(
            client, "finance", "code_review",
            arguments={"language": "python", "focus": "security"}
        )
        ```
    """
    async with mcp_session_context(client, server_name) as session:
        if arguments:
            messages = await load_mcp_prompt(session, prompt_name, arguments=arguments)
        else:
            messages = await load_mcp_prompt(session, prompt_name)

        logger.info(f"[MCPSession] 加载 Prompt: server={server_name}, prompt={prompt_name}")
        return list(messages)


# =============================================================================
# MCP 会话管理器（全局单例）
# =============================================================================


class MCPSessionManager:
    """
    MCP 会话管理器

    负责管理 MCP 客户端会话的生命周期，提供会话清理等后台任务。
    """

    def __init__(self) -> None:
        """初始化会话管理器"""
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._running = False
        logger.info("MCP会话管理器已初始化")

    async def start_cleanup_task(self) -> None:
        """启动会话清理后台任务"""
        if self._cleanup_task is not None:
            logger.warning("会话清理任务已在运行")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("MCP会话管理器后台清理任务已启动")

    async def stop_cleanup_task(self) -> None:
        """停止会话清理后台任务"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("MCP会话管理器后台清理任务已停止")

    async def _cleanup_loop(self) -> None:
        """会话清理循环"""
        while self._running:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(300)  # 每5分钟清理一次
            except asyncio.CancelledError:
                logger.info("会话清理任务被取消")
                break
            except Exception as e:
                logger.error(f"会话清理任务错误: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _cleanup_expired_sessions(self) -> None:
        """清理过期会话"""
        logger.debug("检查并清理过期会话")


_mcp_session_manager: Optional[MCPSessionManager] = None


def get_mcp_session_manager() -> MCPSessionManager:
    """获取全局MCP会话管理器实例"""
    global _mcp_session_manager
    if _mcp_session_manager is None:
        _mcp_session_manager = MCPSessionManager()
    return _mcp_session_manager
