"""
MCP (Model Context Protocol) 适配器

支持三种传输模式：stdio、SSE 和 HTTP。
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import subprocess

import httpx

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
        self._request_id = 0

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

            logger.info(f"启动 stdio MCP 服务器: {command}")

            # 合并环境变量
            import os
            process_env = os.environ.copy()
            process_env.update(env)

            # 启动子进程
            self._process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=process_env,
            )

            # 等待进程启动
            await asyncio.sleep(1)

            # 检查进程是否仍在运行
            if self._process.poll() is not None:
                error = self._process.stderr.read() if self._process.stderr else "未知错误"
                raise MCPConnectionException(
                    server_name=self.name,
                    reason=f"进程启动失败: {error}",
                )

            self._connected = True
            logger.info(f"stdio MCP 服务器连接成功: {self.name}")
            return True

        except Exception as e:
            logger.error(f"stdio MCP 服务器连接失败: {self.name}, error={e}")
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
        return response.get("result", [])

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

    def _get_request_id(self) -> int:
        """获取下一个请求 ID"""
        self._request_id += 1
        return self._request_id

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
            self._process.stdin.write(request_str)
            self._process.stdin.flush()

            # 读取响应
            response_str = self._process.stdout.readline()
            if not response_str:
                raise MCPConnectionException(
                    server_name=self.name,
                    reason="服务器无响应",
                )

            response = json.loads(response_str.strip())

            if "error" in response:
                error = response["error"]
                raise MCPConnectionException(
                    server_name=self.name,
                    reason=f"JSON-RPC 错误: {error.get('message', '未知错误')}",
                )

            return response

        except json.JSONDecodeError as e:
            raise MCPConnectionException(
                server_name=self.name,
                reason=f"响应解析失败: {e}",
            )


# =============================================================================
# SSE 模式适配器
# =============================================================================

class SSEMCPAdapter(MCPAdapter):
    """
    SSE 模式 MCP 适配器

    通过 Server-Sent Events 与 MCP 服务器通信。
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
        self._request_id = 0

    async def connect(self) -> bool:
        """建立 SSE 连接"""
        try:
            if not self._url:
                raise MCPConnectionException(
                    server_name=self.name,
                    reason="SSE 模式缺少 URL 配置",
                )

            logger.info(f"连接 SSE MCP 服务器: {self._url}")

            self._client = httpx.AsyncClient(timeout=30.0)

            # 先设置连接标志，以便 list_tools 可以正常工作
            self._connected = True

            # 测试连接
            tools = await self.list_tools()

            logger.info(f"SSE MCP 服务器连接成功: {self.name}")
            return True

        except Exception as e:
            logger.error(f"SSE MCP 服务器连接失败: {self.name}, error={e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """断开 SSE 连接"""
        if self._client:
            logger.info(f"断开 SSE MCP 服务器: {self.name}")
            await self._client.aclose()
            self._client = None
            self._connected = False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/list",
        }

        response = await self._send_http_request(request)
        return response.get("result", [])

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

        response = await self._send_http_request(request)

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
            logger.warning(f"SSE MCP 服务器不可用: {self.name}, error={e}")
            return False

    def _get_request_id(self) -> int:
        """获取下一个请求 ID"""
        self._request_id += 1
        return self._request_id

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}

        if self._auth_type == "bearer" and self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        elif self._auth_type == "basic" and self._auth_token:
            headers["Authorization"] = f"Basic {self._auth_token}"

        return headers

    async def _send_http_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            request: 请求字典

        Returns:
            响应字典
        """
        if not self._client or not self._connected:
            raise MCPConnectionException(
                server_name=self.name,
                reason="服务器未连接",
            )

        try:
            response = await self._client.post(
                self._url,
                json=request,
                headers=self._get_headers(),
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

        except json.JSONDecodeError as e:
            raise MCPConnectionException(
                server_name=self.name,
                reason=f"响应解析失败: {e}",
            )


# =============================================================================
# HTTP 模式适配器
# =============================================================================

class HTTPMCPAdapter(MCPAdapter):
    """
    HTTP 模式 MCP 适配器

    通过 REST API 与 MCP 服务器通信。
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
        self._request_id = 0

    async def connect(self) -> bool:
        """建立 HTTP 连接"""
        try:
            if not self._url:
                raise MCPConnectionException(
                    server_name=self.name,
                    reason="HTTP 模式缺少 URL 配置",
                )

            logger.info(f"连接 HTTP MCP 服务器: {self._url}")

            self._client = httpx.AsyncClient(timeout=30.0)

            # 先设置连接标志，以便 list_tools 可以正常工作
            self._connected = True

            # 测试连接
            tools = await self.list_tools()

            logger.info(f"HTTP MCP 服务器连接成功: {self.name}")
            return True

        except Exception as e:
            logger.error(f"HTTP MCP 服务器连接失败: {self.name}, error={e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """断开 HTTP 连接"""
        if self._client:
            logger.info(f"断开 HTTP MCP 服务器: {self.name}")
            await self._client.aclose()
            self._client = None
            self._connected = False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/list",
        }

        response = await self._send_http_request(request)
        return response.get("result", [])

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

        response = await self._send_http_request(request)

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

    def _get_request_id(self) -> int:
        """获取下一个请求 ID"""
        self._request_id += 1
        return self._request_id

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}

        if self._auth_type == "bearer" and self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        elif self._auth_type == "basic" and self._auth_token:
            headers["Authorization"] = f"Basic {self._auth_token}"

        return headers

    async def _send_http_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            request: 请求字典

        Returns:
            响应字典
        """
        if not self._client or not self._connected:
            raise MCPConnectionException(
                server_name=self.name,
                reason="服务器未连接",
            )

        try:
            response = await self._client.post(
                self._url,
                json=request,
                headers=self._get_headers(),
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
