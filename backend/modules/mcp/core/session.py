"""
MCP 会话管理（官方标准实现）

基于 langchain-mcp-adapters 官方推荐的 Session 上下文管理器模式。

官方文档: https://docs.langchain.com/oss/python/langchain/mcp#stateful-sessions
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


# =============================================================================
# 官方推荐的 Session 上下文管理器
# =============================================================================

@asynccontextmanager
async def mcp_session_context(
    client: MultiServerMCPClient,
    server_name: str,
):
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
        logger.error(
            f"[MCPSession] 会话错误: server={server_name}, error={e}",
            exc_info=True
        )
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
        logger.info(
            f"[MCPSession] 加载工具: server={server_name}, count={len(tools)}"
        )
        return tools


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

        logger.info(
            f"[MCPSession] 加载资源: server={server_name}, count={len(resources)}"
        )
        return resources


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

        logger.info(
            f"[MCPSession] 加载 Prompt: server={server_name}, prompt={prompt_name}"
        )
        return messages

