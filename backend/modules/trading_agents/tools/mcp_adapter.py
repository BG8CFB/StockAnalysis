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
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import timedelta

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


# =============================================================================
# 连接配置类型定义（对应官方 TypedDict）
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
# MCP 适配器抽象基类
# =============================================================================

class MCPAdapter(ABC):
    """MCP 适配器抽象基类"""

    def __init__(self, name: str, transport: str, config: Dict[str, Any]):
        """
        初始化适配器

        Args:
            name: 服务器名称
            transport: 传输模式 (stdio/sse/streamable_http/websocket)
            config: 服务器配置
        """
        self.name = name
        self.transport = transport
        self.config = config
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """连接到 MCP 服务器"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        pass

    @abstractmethod
    async def check_availability(self) -> bool:
        """检查服务器可用性"""
        pass

    @abstractmethod
    async def get_langchain_tools(self) -> List[BaseTool]:
        """获取 LangChain 工具列表"""
        pass

    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected


# =============================================================================
# 官方 MCP 适配器实现
# =============================================================================

class OfficialMCPAdapter(MCPAdapter):
    """
    官方 MCP 适配器（基于 langchain-mcp-adapters）

    使用 LangChain/LangGraph 官方 MCP 适配器框架，支持所有传输模式。

    特点：
    1. 完全兼容官方 MCP SDK
    2. 支持 stdio、sse、streamable_http、websocket 四种传输模式
    3. 自动会话管理（每次工具调用创建新会话）
    4. 支持自定义 headers 和认证
    5. 支持 LangGraph 集成

    用法示例：
        adapter = OfficialMCPAdapter(
            name="my-server",
            transport="stdio",
            config={"command": "python", "args": ["server.py"]}
        )
        await adapter.connect()
        tools = await adapter.get_langchain_tools()  # 获取 LangChain 工具
    """

    def __init__(self, name: str, transport: str, config: Dict[str, Any]):
        super().__init__(name, transport, config)

        # 构建连接配置
        self._connection_config = self._build_connection_config()

        # 创建 MultiServerMCPClient 实例
        # 注意：官方框架设计为每次调用创建新会话，不需要显式连接/断开
        self._client = MultiServerMCPClient({
            name: self._connection_config
        })

        # 缓存工具列表
        self._tools: List[BaseTool] = []

    def _build_connection_config(self) -> Dict[str, Any]:
        """
        构建连接配置（符合官方 TypedDict 规范）

        根据传输模式，构建对应的连接配置：
        - stdio: StdioConnection
        - sse: SSEConnection
        - streamable_http: StreamableHttpConnection
        - websocket: WebsocketConnection
        """
        transport = self._map_transport_mode(self.transport)

        if transport == "stdio":
            return build_stdio_connection(
                command=self.config.get("command", ""),
                args=self.config.get("args", []),
                env=self.config.get("env"),
                cwd=self.config.get("cwd"),
            )

        elif transport == "sse":
            return build_sse_connection(
                url=self.config.get("url", ""),
                headers=self._build_auth_headers(),
                timeout=self.config.get("timeout", 5.0),
                sse_read_timeout=self.config.get("sse_read_timeout", 300.0),
            )

        elif transport == "streamable_http":
            return build_streamable_http_connection(
                url=self.config.get("url", ""),
                headers=self._build_auth_headers(),
                timeout=timedelta(seconds=self.config.get("timeout", 30)) if self.config.get("timeout") else None,
                sse_read_timeout=timedelta(seconds=self.config.get("sse_read_timeout", 300)) if self.config.get("sse_read_timeout") else None,
            )

        elif transport == "websocket":
            return build_websocket_connection(
                url=self.config.get("url", ""),
            )

        else:
            raise ValueError(f"不支持的传输模式: {transport}")

    def _map_transport_mode(self, transport: str) -> str:
        """
        映射传输模式到官方框架格式

        支持的映射：
        - stdio -> stdio
        - sse -> sse
        - http -> streamable_http (推荐)
        - streamable_http -> streamable_http
        - websocket -> websocket
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

    def _build_auth_headers(self) -> Optional[Dict[str, str]]:
        """
        构建认证头

        支持两种配置方式：
        1. 直接配置 headers 字段（优先级更高）
        2. 使用 auth_type + auth_token 组合

        支持的认证类型：
        - bearer: Bearer Token 认证
        - basic: Basic Auth 认证
        - none: 无认证
        """
        # 方式1：优先使用直接配置的 headers 字段
        headers = self.config.get("headers")
        if headers and isinstance(headers, dict):
            logger.debug(f"使用直接配置的 headers: {list(headers.keys())}")
            return headers

        # 方式2：使用 auth_type + auth_token 组合
        auth_type = self.config.get("auth_type", "none")
        auth_token = self.config.get("auth_token")

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

    async def connect(self) -> bool:
        """
        连接到 MCP 服务器并验证连接

        通过尝试获取工具列表来验证连接是否成功。
        """
        try:
            logger.info(
                f"连接 MCP 服务器: name={self.name}, "
                f"transport={self.transport}"
            )

            # 尝试获取工具列表以验证连接
            self._tools = await self._client.get_tools(server_name=self.name)

            self._connected = True
            logger.info(
                f"MCP 服务器连接成功: name={self.name}, "
                f"tool_count={len(self._tools)}"
            )
            return True

        except Exception as e:
            logger.error(
                f"MCP 服务器连接失败: name={self.name}, error={e}",
                exc_info=True
            )
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """
        断开连接

        注意：官方框架的 MultiServerMCPClient 不需要显式断开连接，
        它会在每次工具调用后自动关闭会话。这里只是清理本地状态。
        """
        logger.info(f"断开 MCP 服务器: {self.name}")
        self._client = None
        self._tools = []
        self._connected = False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取工具列表（原始 MCP 格式）

        Returns:
            工具列表，每个工具包含 name, description, inputSchema 等字段
        """
        if not self._connected:
            raise RuntimeError(f"MCP 服务器未连接: {self.name}")

        # 如果缓存为空，重新获取
        if not self._tools:
            self._tools = await self._client.get_tools(server_name=self.name)

        # 转换为原始 MCP 格式
        tools = []
        for tool in self._tools:
            tool_dict = {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": self._get_tool_schema(tool),
            }
            tools.append(tool_dict)

        logger.debug(
            f"MCP 工具列表获取成功: server={self.name}, "
            f"count={len(tools)}"
        )

        return tools

    def _get_tool_schema(self, tool: BaseTool) -> Dict[str, Any]:
        """获取工具的输入 schema"""
        if hasattr(tool, 'args_schema') and tool.args_schema:
            if hasattr(tool.args_schema, 'model_json_schema'):
                return tool.args_schema.model_json_schema()
            elif hasattr(tool.args_schema, 'schema'):
                return tool.args_schema.schema()
        return {}

    async def get_langchain_tools(self) -> List[BaseTool]:
        """
        获取 LangChain 工具列表

        这是推荐的使用方式，返回的工具可以直接用于 LangGraph 智能体。

        Returns:
            LangChain BaseTool 列表
        """
        if not self._connected:
            raise RuntimeError(f"MCP 服务器未连接: {self.name}")

        # 如果缓存为空，重新获取
        if not self._tools:
            self._tools = await self._client.get_tools(server_name=self.name)

        return self._tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用工具

        使用官方框架的 session 上下文管理器调用工具。
        每次调用会创建新的 MCP 会话。

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果（MCP 格式）
        """
        if not self._connected:
            raise RuntimeError(f"MCP 服务器未连接: {self.name}")

        try:
            # 使用官方框架的 session 上下文管理器
            async with self._client.session(self.name) as session:
                # 调用工具
                result = await session.call_tool(tool_name, arguments)

                logger.debug(
                    f"MCP 工具调用成功: server={self.name}, "
                    f"tool={tool_name}"
                )

                # 返回 MCP 格式的结果
                return self._format_tool_result(result)

        except Exception as e:
            logger.error(
                f"MCP 工具调用失败: server={self.name}, "
                f"tool={tool_name}, error={e}",
                exc_info=True
            )
            return {
                "content": [{"type": "text", "text": str(e)}],
                "isError": True,
            }

    def _format_tool_result(self, result) -> Dict[str, Any]:
        """
        格式化工具执行结果为 MCP 格式

        Args:
            result: MCP 客户端返回的 CallToolResult

        Returns:
            MCP 格式的结果字典
        """
        # MCP SDK 返回的 CallToolResult 对象
        if hasattr(result, 'content'):
            # 将 content 转换为可序列化的格式
            content = []
            for item in result.content:
                if hasattr(item, 'model_dump'):
                    content.append(item.model_dump())
                elif hasattr(item, '__dict__'):
                    content.append(dict(item.__dict__))
                else:
                    content.append({"type": "text", "text": str(item)})

            return {
                "content": content,
                "isError": getattr(result, 'isError', False),
            }
        else:
            # 兼容其他返回格式
            return {
                "content": [{"type": "text", "text": str(result)}],
                "isError": False,
            }

    async def check_availability(self) -> bool:
        """检查服务器可用性"""
        try:
            # 重新创建客户端并尝试连接
            self._client = MultiServerMCPClient({
                self.name: self._connection_config
            })
            return await self.connect()
        except Exception as e:
            logger.warning(
                f"MCP 服务器不可用: {self.name}, error={e}"
            )
            return False

    @asynccontextmanager
    async def session(self):
        """
        获取 MCP 会话上下文管理器

        这是一个便捷方法，允许直接访问底层的 MCP 会话。

        用法：
            async with adapter.session() as session:
                result = await session.call_tool("tool_name", {...})
        """
        if not self._connected:
            raise RuntimeError(f"MCP 服务器未连接: {self.name}")

        async with self._client.session(self.name) as session:
            yield session


# =============================================================================
# MCP 适配器工厂
# =============================================================================

class MCPAdapterFactory:
    """
    MCP 适配器工厂

    根据配置创建对应的 MCP 适配器实例。
    """

    @staticmethod
    def create_adapter(
        name: str,
        transport: str,
        config: Dict[str, Any]
    ) -> MCPAdapter:
        """
        创建 MCP 适配器

        Args:
            name: 服务器名称
            transport: 传输模式 (stdio/sse/http/streamable_http/websocket)
            config: 服务器配置

        Returns:
            MCP 适配器实例
        """
        # 统一使用官方适配器
        return OfficialMCPAdapter(name, transport, config)

    @staticmethod
    def create_multi_server_client(
        connections: Dict[str, Dict[str, Any]]
    ) -> MultiServerMCPClient:
        """
        创建多服务器客户端

        这是一个便捷方法，直接创建官方的 MultiServerMCPClient。

        Args:
            connections: 服务器连接配置字典
                格式: {"server_name": {...connection_config...}}

        Returns:
            MultiServerMCPClient 实例

        用法示例：
            client = MCPAdapterFactory.create_multi_server_client({
                "math": {
                    "transport": "stdio",
                    "command": "python",
                    "args": ["math_server.py"],
                },
                "weather": {
                    "transport": "streamable_http",
                    "url": "http://localhost:8000/mcp",
                }
            })
            tools = await client.get_tools()
        """
        return MultiServerMCPClient(connections)


# =============================================================================
# 辅助函数
# =============================================================================

def create_connection_config(
    transport: str,
    **kwargs
) -> Dict[str, Any]:
    """
    创建连接配置的便捷函数

    Args:
        transport: 传输模式
        **kwargs: 传输模式特定的配置参数

    Returns:
        连接配置字典
    """
    transport = transport.lower()

    if transport == "stdio":
        return build_stdio_connection(
            command=kwargs.get("command", ""),
            args=kwargs.get("args", []),
            env=kwargs.get("env"),
            cwd=kwargs.get("cwd"),
        )

    elif transport == "sse":
        return build_sse_connection(
            url=kwargs.get("url", ""),
            headers=kwargs.get("headers"),
            timeout=kwargs.get("timeout", 5.0),
            sse_read_timeout=kwargs.get("sse_read_timeout", 300.0),
        )

    elif transport in ["http", "streamable_http"]:
        return build_streamable_http_connection(
            url=kwargs.get("url", ""),
            headers=kwargs.get("headers"),
            timeout=timedelta(seconds=kwargs["timeout"]) if kwargs.get("timeout") else None,
            sse_read_timeout=timedelta(seconds=kwargs["sse_read_timeout"]) if kwargs.get("sse_read_timeout") else None,
        )

    elif transport == "websocket":
        return build_websocket_connection(
            url=kwargs.get("url", ""),
        )

    else:
        raise ValueError(f"不支持的传输模式: {transport}")
