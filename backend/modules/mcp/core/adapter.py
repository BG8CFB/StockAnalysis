"""
MCP 适配器 - 使用官方 langchain-mcp-adapters 框架

基于 LangChain/LangGraph 官方 MCP 适配器，支持所有传输模式：
- stdio: 标准输入输出
- sse: Server-Sent Events
- streamable_http: Streamable HTTP (推荐)
- websocket: WebSocket

官方文档: https://github.com/langchain-ai/langchain-mcp-adapters
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import timedelta

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool

from modules.mcp.core.exceptions import MCPConnectionError

logger = logging.getLogger(__name__)


# =============================================================================
# 连接配置构建函数
# =============================================================================

def build_stdio_connection(
    command: str,
    args: List[str],
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    构建 stdio 传输模式的连接配置

    Args:
        command: 启动命令（如 "python", "node", "npx"）
        args: 命令参数列表
        env: 环境变量（可选）
        cwd: 工作目录（可选）
        encoding: 字符编码（默认 utf-8）

    Returns:
        符合官方 StdioConnection 规范的配置字典
    """
    config: Dict[str, Any] = {
        "transport": "stdio",
        "command": command,
        "args": args,
    }

    if env:
        config["env"] = env
    if cwd:
        config["cwd"] = cwd
    if encoding != "utf-8":
        config["encoding"] = encoding

    return config


def build_sse_connection(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 5.0,
    sse_read_timeout: float = 300.0,
) -> Dict[str, Any]:
    """
    构建 SSE 传输模式的连接配置

    Args:
        url: SSE 端点 URL
        headers: HTTP 头（用于认证等）
        timeout: HTTP 超时时间（秒）
        sse_read_timeout: SSE 读取超时时间（秒）

    Returns:
        符合官方 SSEConnection 规范的配置字典
    """
    config: Dict[str, Any] = {
        "transport": "sse",
        "url": url,
    }

    if headers:
        config["headers"] = headers
    if timeout != 5.0:
        config["timeout"] = timeout
    if sse_read_timeout != 300.0:
        config["sse_read_timeout"] = sse_read_timeout

    return config


def build_streamable_http_connection(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[timedelta] = None,
    sse_read_timeout: Optional[timedelta] = None,
    terminate_on_close: bool = True,
) -> Dict[str, Any]:
    """
    构建 Streamable HTTP 传输模式的连接配置（推荐）

    Args:
        url: HTTP 端点 URL
        headers: HTTP 头（用于认证等）
        timeout: HTTP 超时时间
        sse_read_timeout: SSE 读取超时时间
        terminate_on_close: 是否在关闭时终止会话

    Returns:
        符合官方 StreamableHttpConnection 规范的配置字典
    """
    config: Dict[str, Any] = {
        "transport": "streamable_http",
        "url": url,
    }

    if headers:
        config["headers"] = headers
    if timeout:
        config["timeout"] = timeout
    if sse_read_timeout:
        config["sse_read_timeout"] = sse_read_timeout
    if not terminate_on_close:
        config["terminate_on_close"] = terminate_on_close

    return config


def build_websocket_connection(url: str) -> Dict[str, Any]:
    """
    构建 WebSocket 传输模式的连接配置

    Args:
        url: WebSocket 端点 URL

    Returns:
        符合官方 WebsocketConnection 规范的配置字典
    """
    return {
        "transport": "websocket",
        "url": url,
    }


# =============================================================================
# MCP 工具获取函数
# =============================================================================

async def get_mcp_tools(
    server_name: str,
    connection_config: Dict[str, Any],
) -> List[BaseTool]:
    """
    从 MCP 服务器获取 LangChain 工具列表

    这是推荐的用法，返回的工具可以直接用于 LangGraph 智能体。

    Args:
        server_name: 服务器名称
        connection_config: 连接配置（由 build_*_connection 函数构建）

    Returns:
        LangChain BaseTool 列表

    Raises:
        MCPConnectionError: 连接失败时抛出
    """
    try:
        logger.info(
            f"获取 MCP 工具: server_name={server_name}, "
            f"transport={connection_config.get('transport')}"
        )

        # 创建 MultiServerMCPClient
        client = MultiServerMCPClient({
            server_name: connection_config
        })

        # 获取工具（使用官方推荐的 client.get_tools() 方法）
        tools = await client.get_tools()

        logger.info(
            f"MCP 工具获取成功: server_name={server_name}, "
            f"tool_count={len(tools)}"
        )

        return tools

    except Exception as e:
        logger.error(
            f"MCP 工具获取失败: server_name={server_name}, error={e}",
            exc_info=True
        )
        raise MCPConnectionError(
            f"无法连接到 MCP 服务器 {server_name}: {e}"
        ) from e


# =============================================================================
# 辅助函数
# =============================================================================

def build_auth_headers(
    headers: Optional[Dict[str, str]] = None,
    auth_type: str = "none",
    auth_token: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """
    构建认证头

    支持两种配置方式：
    1. 直接配置 headers 字段（优先级更高）
    2. 使用 auth_type + auth_token 组合

    支持的认证类型：
    - bearer: Bearer Token 认证
    - basic: Basic Auth 认证
    - none: 无认证

    Args:
        headers: 直接配置的 headers
        auth_type: 认证类型
        auth_token: 认证令牌

    Returns:
        认证头字典或 None
    """
    # 方式1：优先使用直接配置的 headers 字段
    if headers and isinstance(headers, dict):
        logger.debug(f"使用直接配置的 headers: {list(headers.keys())}")
        return headers

    # 方式2：使用 auth_type + auth_token 组合
    if auth_type == "none" or not auth_token:
        logger.debug(f"未配置认证 (auth_type={auth_type})")
        return None

    if auth_type == "bearer":
        headers = {"Authorization": f"Bearer {auth_token}"}
        logger.debug(f"使用 Bearer 认证")
        return headers

    elif auth_type == "basic":
        # Basic Auth token 格式: "username:password"
        import base64
        encoded = base64.b64encode(auth_token.encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}
        logger.debug(f"使用 Basic 认证")
        return headers

    else:
        logger.warning(f"未知的认证类型: {auth_type}，忽略认证配置")
        return None


def map_transport_mode(transport: str) -> str:
    """
    映射传输模式到官方框架格式

    支持的映射：
    - stdio -> stdio
    - sse -> sse
    - http -> streamable_http (推荐)
    - streamable_http -> streamable_http
    - websocket -> websocket

    Args:
        transport: 传输模式

    Returns:
        映射后的传输模式

    Raises:
        ValueError: 不支持的传输模式
    """
    mapping = {
        "stdio": "stdio",
        "sse": "sse",
        "http": "streamable_http",  # HTTP 映射到 streamable_http
        "streamable_http": "streamable_http",
        "websocket": "websocket",
    }
    result = mapping.get(transport.lower())
    if not result:
        raise ValueError(
            f"不支持的传输模式: {transport}，"
            f"支持的模式: {list(mapping.keys())}"
        )
    return result
