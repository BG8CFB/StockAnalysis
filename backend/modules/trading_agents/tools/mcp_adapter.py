"""
MCP (Model Context Protocol) 适配器

支持三种传输模式：stdio、SSE（旧版）和 HTTP（新版 Streamable HTTP）。

基于官方 Python MCP SDK 实现：
- https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
import subprocess
from contextlib import asynccontextmanager

import httpx
from httpx_sse import aconnect_sse, ServerSentEvent

from ..core.exceptions import MCPConnectionException

logger = logging.getLogger(__name__)


# =============================================================================
# MCP 适配器基类
# =============================================================================

class MCPAdapter(ABC):
    """
    MCP 适配器抽象基类

    所有 MCP 适配器必须实现此接口。
    """

    def __init__(
        self,
        name: str,
        transport: str,
        config: Dict[str, Any],
    ):
        """
        初始化 MCP 适配器

        Args:
            name: 服务器名称
            transport: 传输模式 (stdio/sse/http)
            config: 配置字典
        """
        self.name = name
        self.transport = transport
        self.config = config
        self._connected = False
        self._request_id = 0

    @abstractmethod
    async def connect(self) -> bool:
        """
        连接到 MCP 服务器

        Returns:
            连接是否成功
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表

        Returns:
            工具列表
        """
        pass

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具返回结果
        """
        pass

    @abstractmethod
    async def check_availability(self) -> bool:
        """
        检查服务器可用性

        Returns:
            是否可用
        """
        pass

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    def _get_request_id(self) -> int:
        """获取下一个请求 ID"""
        self._request_id += 1
        return self._request_id

    def _parse_tools_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析工具列表响应

        Args:
            response: JSON-RPC 响应

        Returns:
            工具列表
        """
        logger.info(
            f"MCP tools/list 原始响应: server={self.name}, "
            f"response_keys={list(response.keys())}, "
            f"response={json.dumps(response, ensure_ascii=False)[:500]}"
        )

        result = response.get("result", {})

        logger.info(
            f"MCP tools/list result: server={self.name}, "
            f"result_type={type(result).__name__}, "
            f"result_keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}"
        )

        # 如果 result 是字典且有 tools 键，提取 tools
        if isinstance(result, dict) and "tools" in result:
            tools = result["tools"]
            logger.info(
                f"MCP tools/list 成功解析: server={self.name}, "
                f"tool_count={len(tools) if isinstance(tools, list) else 0}"
            )
            return tools
        # 如果 result 直接是列表，返回它
        elif isinstance(result, list):
            logger.info(
                f"MCP tools/list 返回直接列表: server={self.name}, "
                f"count={len(result)}"
            )
            return result
        # 否则返回空列表
        else:
            logger.warning(
                f"MCP 服务器未返回工具列表: server={self.name}, "
                f"result_type={type(result).__name__}, "
                f"result_content={json.dumps(result, ensure_ascii=False)[:200] if result else 'empty'}"
            )
            return []


# =============================================================================
# stdio 模式适配器
# =============================================================================

class StdioMCPAdapter(MCPAdapter):
    """
    stdio 模式 MCP 适配器

    通过子进程与 MCP 服务器通信。
    """

    def __init__(
        self,
        name: str,
        transport: str,
        config: Dict[str, Any],
    ):
        super().__init__(name, transport, config)
        self._process: Optional[subprocess.Popen] = None

    async def connect(self) -> bool:
        """启动 MCP 服务器进程"""
        try:
            command = self.config.get("command")
            args = self.config.get("args", [])
            env = self.config.get("env", {})

            if not command:
                raise MCPConnectionException(
                    server_name=self.name,
                    reason="stdio 模式缺少 command 配置",
                )

            logger.info(f"启动 stdio MCP 服务器: {command} {' '.join(args)}")

            # 合并环境变量
            import os
            import platform
            process_env = os.environ.copy()
            process_env.update(env)

            # Windows 上需要特殊处理 npx 等命令
            if platform.system() == "Windows":
                # 对于 npx, npm 等命令，Windows 上需要使用 .cmd 或 .bat
                if command in ["npx", "npm", "node"]:
                    # 尝试找到命令的完整路径
                    import shutil
                    full_command = shutil.which(command)
                    if full_command:
                        command = full_command
                    else:
                        # 使用 cmd /c 来执行命令
                        args = [command] + args
                        command = "cmd"
                        args = ["/c"] + args
                elif command.endswith(".js") or command.endswith(".mjs"):
                    # 直接运行 JS 文件需要 node
                    args = [command] + args
                    command = "node"
                    full_command = shutil.which("node")
                    if full_command:
                        command = full_command

            # 构建完整命令列表
            full_cmd = [command] + args

            logger.info(f"执行命令: {' '.join(full_cmd)}")

            # 启动子进程
            self._process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=process_env,
                bufsize=0,  # 无缓冲，实时通信
            )

            # 等待进程启动
            await asyncio.sleep(1)

            # 检查进程是否仍在运行
            if self._process.poll() is not None:
                stderr_output = ""
                if self._process.stderr:
                    try:
                        stderr_output = self._process.stderr.read()
                    except:
                        pass
                raise MCPConnectionException(
                    server_name=self.name,
                    reason=f"进程启动失败，进程已退出: {stderr_output or '未知错误'}",
                )

            self._connected = True
            logger.info(f"stdio MCP 服务器连接成功: {self.name}, pid={self._process.pid}")
            return True

        except Exception as e:
            logger.error(f"stdio MCP 服务器连接失败: {self.name}, error={e}", exc_info=True)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """关闭 MCP 服务器进程"""
        if self._process:
            logger.info(f"关闭 stdio MCP 服务器: {self.name}")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            self._connected = False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/list",
        }

        response = await self._send_request(request)
        return self._parse_tools_response(response)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用工具"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        response = await self._send_request(request)

        if "error" in response:
            error = response["error"]
            raise MCPConnectionException(
                server_name=self.name,
                reason=f"工具调用失败: {error.get('message', '未知错误')}",
            )

        return response.get("result", {})

    async def check_availability(self) -> bool:
        """检查服务器可用性"""
        try:
            tools = await self.list_tools()
            return self._connected
        except Exception as e:
            logger.warning(f"stdio MCP 服务器不可用: {self.name}, error={e}")
            return False

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 JSON-RPC 请求

        Args:
            request: 请求字典

        Returns:
            响应字典
        """
        if not self._process or not self._connected:
            raise MCPConnectionException(
                server_name=self.name,
                reason="服务器未连接",
            )

        try:
            # 发送请求
            request_str = json.dumps(request) + "\n"
            logger.debug(f"发送 MCP 请求: {request_str.strip()}")

            self._process.stdin.write(request_str)
            self._process.stdin.flush()

            # 检查进程状态
            if self._process.poll() is not None:
                # 进程已退出
                stderr_output = ""
                if self._process.stderr:
                    try:
                        stderr_output = self._process.stderr.read()
                    except:
                        pass
                raise MCPConnectionException(
                    server_name=self.name,
                    reason=f"MCP 进程意外退出: {stderr_output or '无错误信息'}",
                )

            # 读取响应（带超时）
            response_str = await asyncio.wait_for(
                asyncio.to_thread(self._process.stdout.readline),
                timeout=5.0
            )

            if not response_str:
                raise MCPConnectionException(
                    server_name=self.name,
                    reason="服务器无响应",
                )

            logger.debug(f"收到 MCP 响应: {response_str.strip()}")

            response = json.loads(response_str.strip())

            if "error" in response:
                error = response["error"]
                raise MCPConnectionException(
                    server_name=self.name,
                    reason=f"JSON-RPC 错误: {error.get('message', '未知错误')}",
                )

            return response

        except asyncio.TimeoutError:
            raise MCPConnectionException(
                server_name=self.name,
                reason="响应超时（5秒）",
            )
        except json.JSONDecodeError as e:
            # 记录原始响应用于调试
            logger.error(
                f"MCP 响应解析失败: server={self.name}, "
                f"response={response_str if 'response_str' in locals() else 'N/A'}, "
                f"error={e}"
            )
            raise MCPConnectionException(
                server_name=self.name,
                reason=f"响应解析失败: {e}",
            )


# =============================================================================
# SSE 模式适配器（旧版双端点模式）
# =============================================================================

class SSEMCPAdapter(MCPAdapter):
    """
    SSE 模式 MCP 适配器（旧版双端点模式）

    通过 SSE 接收响应，通过 POST 发送请求。

    连接流程：
    1. GET 请求建立 SSE 连接
    2. 接收 'endpoint' 事件获取 POST URL
    3. POST 到该 URL 发送 JSON-RPC 消息
    4. 通过 'message' 事件接收响应

    注意：此适配器每次操作时都会建立新连接获取 endpoint，
    然后发送 POST 请求并等待响应。
    """

    def __init__(
        self,
        name: str,
        transport: str,
        config: Dict[str, Any],
    ):
        super().__init__(name, transport, config)
        self._base_url = config.get("url", "")
        self._auth_token = config.get("auth_token")
        self._auth_type = config.get("auth_type", "none")

    async def connect(self) -> bool:
        """
        测试连接：尝试获取 endpoint URL

        注意：此方法仅用于验证服务器可达性，
        实际请求会在每次调用时重新建立连接。
        """
        try:
            if not self._base_url:
                raise MCPConnectionException(
                    server_name=self.name,
                    reason="SSE 模式缺少 URL 配置",
                )

            logger.info(f"测试 SSE MCP 服务器连接: {self._base_url}")

            # 尝试获取 endpoint
            endpoint_url = await self._get_endpoint()

            if endpoint_url:
                logger.info(f"SSE MCP 服务器连接成功: {self.name}")
                self._connected = True
                return True
            else:
                logger.error(f"SSE MCP 服务器未返回 endpoint: {self.name}")
                return False

        except Exception as e:
            logger.error(f"SSE MCP 服务器连接失败: {self.name}, error={e}", exc_info=True)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """断开连接（无需操作，每次请求都是新连接）"""
        self._connected = False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/list",
        }

        response = await self._execute_request(request)
        return self._parse_tools_response(response)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用工具"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        response = await self._execute_request(request)

        if "error" in response:
            error = response["error"]
            raise MCPConnectionException(
                server_name=self.name,
                reason=f"工具调用失败: {error.get('message', '未知错误')}",
            )

        return response.get("result", {})

    async def check_availability(self) -> bool:
        """检查服务器可用性"""
        return await self.connect()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {}

        if self._auth_type == "bearer" and self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        elif self._auth_type == "basic" and self._auth_token:
            headers["Authorization"] = f"Basic {self._auth_token}"

        return headers

    async def _get_endpoint(self) -> Optional[str]:
        """
        获取 POST endpoint URL

        Returns:
            endpoint URL 或 None
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = self._get_headers()

            async with aconnect_sse(
                client,
                "GET",
                self._base_url,
                headers=headers,
            ) as event_source:
                event_source.response.raise_for_status()

                # 等待 endpoint 事件
                async for sse in event_source.aiter_sse():
                    if sse.event == "endpoint":
                        endpoint_url = urljoin(self._base_url, sse.data)

                        # 验证 origin 匹配
                        base_parsed = urlparse(self._base_url)
                        endpoint_parsed = urlparse(endpoint_url)
                        if (base_parsed.netloc != endpoint_parsed.netloc or
                            base_parsed.scheme != endpoint_parsed.scheme):
                            raise MCPConnectionException(
                                server_name=self.name,
                                reason=f"Endpoint origin 不匹配: {endpoint_url}",
                            )

                        logger.info(f"获取到 endpoint URL: {endpoint_url}")
                        return endpoint_url

        return None

    async def _execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行请求：获取 endpoint，POST 请求，等待响应

        Args:
            request: JSON-RPC 请求

        Returns:
            JSON-RPC 响应
        """
        # 获取 endpoint
        endpoint_url = await self._get_endpoint()
        if not endpoint_url:
            raise MCPConnectionException(
                server_name=self.name,
                reason="无法获取 endpoint URL",
            )

        # 发送 POST 请求
        post_headers = {
            "Content-Type": "application/json",
            **self._get_headers(),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint_url,
                json=request,
                headers=post_headers,
            )

            if response.status_code != 200:
                raise MCPConnectionException(
                    server_name=self.name,
                    reason=f"HTTP {response.status_code}: {response.text}",
                )

            data = response.json()

            if "error" in data:
                error = data["error"]
                raise MCPConnectionException(
                    server_name=self.name,
                    reason=f"JSON-RPC 错误: {error.get('message', '未知错误')}",
                )

            return data


# =============================================================================
# HTTP 模式适配器（新版 Streamable HTTP）
# =============================================================================

class HTTPMCPAdapter(MCPAdapter):
    """
    HTTP 模式 MCP 适配器（新版 Streamable HTTP）

    支持单端点模式，响应可以是 JSON 或 SSE 流。

    特性：
    - 单端点（通常 /mcp）
    - 支持 JSON 和 SSE 响应
    - 会话管理（mcp-session-id）
    - 支持可恢复操作
    """

    def __init__(
        self,
        name: str,
        transport: str,
        config: Dict[str, Any],
    ):
        super().__init__(name, transport, config)
        self._client: Optional[httpx.AsyncClient] = None
        self._url = config.get("url", "")
        self._auth_token = config.get("auth_token")
        self._auth_type = config.get("auth_type", "none")
        self._session_id: Optional[str] = None
        self._protocol_version: Optional[str] = None

    async def connect(self) -> bool:
        """建立 HTTP 连接并初始化会话"""
        try:
            if not self._url:
                raise MCPConnectionException(
                    server_name=self.name,
                    reason="HTTP 模式缺少 URL 配置",
                )

            logger.info(f"连接 HTTP MCP 服务器: {self._url}")

            self._client = httpx.AsyncClient(timeout=30.0)

            # 发送初始化请求（跳过连接状态检查，因为此时还未建立连接）
            init_request = {
                "jsonrpc": "2.0",
                "id": self._get_request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "stock-analysis-backend",
                        "version": "1.0.0"
                    }
                },
            }

            response = await self._send_request(init_request, skip_connection_check=True)

            # 提取会话信息
            if "result" in response:
                result = response["result"]
                if isinstance(result, dict):
                    self._protocol_version = result.get("protocolVersion")
                    logger.info(f"协议版本: {self._protocol_version}")

            self._connected = True
            logger.info(f"HTTP MCP 服务器连接成功: {self.name}")
            return True

        except Exception as e:
            logger.error(f"HTTP MCP 服务器连接失败: {self.name}, error={e}", exc_info=True)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """断开 HTTP 连接"""
        if self._client:
            logger.info(f"断开 HTTP MCP 服务器: {self.name}")

            # 发送关闭通知
            try:
                notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
                await self._send_request(notification)
            except:
                pass  # 忽略关闭时的错误

            await self._client.aclose()
            self._client = None
            self._session_id = None
            self._connected = False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/list",
        }

        response = await self._send_request(request)
        return self._parse_tools_response(response)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用工具"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        response = await self._send_request(request)

        if "error" in response:
            error = response["error"]
            raise MCPConnectionException(
                server_name=self.name,
                reason=f"工具调用失败: {error.get('message', '未知错误')}",
            )

        return response.get("result", {})

    async def check_availability(self) -> bool:
        """检查服务器可用性"""
        try:
            tools = await self.list_tools()
            return self._connected
        except Exception as e:
            logger.warning(f"HTTP MCP 服务器不可用: {self.name}, error={e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        if self._session_id:
            headers["mcp-session-id"] = self._session_id

        if self._auth_type == "bearer" and self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        elif self._auth_type == "basic" and self._auth_token:
            headers["Authorization"] = f"Basic {self._auth_token}"

        return headers

    async def _send_request(self, request: Dict[str, Any], skip_connection_check: bool = False) -> Dict[str, Any]:
        """
        发送 HTTP 请求，处理 JSON 或 SSE 响应

        Args:
            request: 请求字典
            skip_connection_check: 是否跳过连接状态检查（用于初始化请求）

        Returns:
            响应字典
        """
        if not skip_connection_check and not self._client:
            raise MCPConnectionException(
                server_name=self.name,
                reason="HTTP 客户端未初始化",
            )

        try:
            headers = self._get_headers()

            # 发送 POST 请求
            async with self._client.stream(
                "POST",
                self._url,
                json=request,
                headers=headers,
            ) as response:
                # 检查状态码
                if response.status_code == 404:
                    raise MCPConnectionException(
                        server_name=self.name,
                        reason="会话不存在或已过期",
                    )

                response.raise_for_status()

                # 提取会话 ID
                new_session_id = response.headers.get("mcp-session-id")
                if new_session_id:
                    self._session_id = new_session_id
                    logger.info(f"收到会话 ID: {self._session_id}")

                # 检查响应类型
                content_type = response.headers.get("content-type", "").lower()

                if content_type.startswith("application/json"):
                    # JSON 响应
                    content = await response.aread()
                    data = json.loads(content.decode())

                    if "error" in data:
                        error = data["error"]
                        raise MCPConnectionException(
                            server_name=self.name,
                            reason=f"JSON-RPC 错误: {error.get('message', '未知错误')}",
                        )

                    return data

                elif content_type.startswith("text/event-stream"):
                    # SSE 流式响应 - 需要使用 aconnect_sse
                    # 由于我们已经在 stream 上下文中，需要特殊处理
                    # 先读取所有内容，然后解析
                    content = await response.aread()
                    lines = content.decode().split('\n')

                    message = None
                    for i, line in enumerate(lines):
                        if line.startswith('data:'):
                            data = line[5:].strip()
                            if data:
                                try:
                                    message = json.loads(data)
                                    break
                                except json.JSONDecodeError:
                                    continue

                    if message:
                        if "error" in message:
                            error = message["error"]
                            raise MCPConnectionException(
                                server_name=self.name,
                                reason=f"JSON-RPC 错误: {error.get('message', '未知错误')}",
                            )
                        return message
                    else:
                        raise MCPConnectionException(
                            server_name=self.name,
                            reason="SSE 流未收到有效响应",
                        )

                else:
                    raise MCPConnectionException(
                        server_name=self.name,
                        reason=f"不支持的响应类型: {content_type}",
                    )

        except httpx.HTTPStatusError as e:
            raise MCPConnectionException(
                server_name=self.name,
                reason=f"HTTP 错误: {e.response.status_code}",
            )
        except json.JSONDecodeError as e:
            raise MCPConnectionException(
                server_name=self.name,
                reason=f"响应解析失败: {e}",
            )


# =============================================================================
# 适配器工厂
# =============================================================================

class MCPAdapterFactory:
    """MCP 适配器工厂"""

    @staticmethod
    def create_adapter(
        name: str,
        transport: str,
        config: Dict[str, Any],
    ) -> MCPAdapter:
        """
        创建 MCP 适配器实例

        Args:
            name: 服务器名称
            transport: 传输模式 (stdio/sse/http)
            config: 配置字典

        Returns:
            MCP 适配器实例

        Raises:
            ValueError: 不支持的传输模式
        """
        if transport == "stdio":
            return StdioMCPAdapter(name, transport, config)
        elif transport == "sse":
            return SSEMCPAdapter(name, transport, config)
        elif transport == "http":
            return HTTPMCPAdapter(name, transport, config)
        else:
            raise ValueError(f"不支持的传输模式: {transport}")
