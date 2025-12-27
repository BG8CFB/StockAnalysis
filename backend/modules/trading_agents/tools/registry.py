"""
工具注册表

管理所有可用的工具，包括 MCP 工具和本地工具。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """工具状态枚举"""
    AVAILABLE = "available"     # 可用
    UNAVAILABLE = "unavailable" # 不可用
    DISABLED = "disabled"       # 已禁用（循环检测触发）


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str                           # 工具名称
    description: str                    # 工具描述
    parameters: Dict[str, Any]           # 参数模式（JSON Schema）
    tool_type: str = "local"            # 工具类型：local 或 mcp
    mcp_server: Optional[str] = None     # MCP 服务器名称（如果是 MCP 工具）
    status: ToolStatus = ToolStatus.AVAILABLE  # 工具状态
    handler: Optional[Callable] = None   # 处理函数（本地工具）
    call_count: int = 0                 # 调用计数
    error_count: int = 0                # 错误计数
    last_error: Optional[str] = None     # 最后一次错误


class ToolRegistry:
    """
    工具注册表（单例模式）

    管理所有可用的工具，支持工具的注册、查找、调用和状态管理。
    """

    _instance: Optional["ToolRegistry"] = None

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._tools: Dict[str, ToolDefinition] = {}
        self._mcp_tools: Dict[str, List[str]] = {}  # {server_name: [tool_names]}
        self._initialized = True

    def register_local_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
    ) -> None:
        """
        注册本地工具

        Args:
            name: 工具名称
            description: 工具描述
            parameters: 参数模式（JSON Schema 格式）
            handler: 处理函数
        """
        if name in self._tools:
            logger.warning(f"工具已存在，将覆盖: {name}")

        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            tool_type="local",
            handler=handler,
        )

        self._tools[name] = tool_def
        logger.info(f"注册本地工具: {name}")

    def register_mcp_tools(
        self,
        server_name: str,
        tools: List[Dict[str, Any]]
    ) -> None:
        """
        注册 MCP 工具

        Args:
            server_name: MCP 服务器名称
            tools: 工具列表（从 MCP 服务器获取）
        """
        # 先清除该服务器的旧工具
        if server_name in self._mcp_tools:
            for old_tool_name in self._mcp_tools[server_name]:
                if old_tool_name in self._tools:
                    del self._tools[old_tool_name]

        # 注册新工具
        tool_names = []
        for tool_data in tools:
            tool_name = tool_data.get("name")
            if not tool_name:
                continue

            tool_def = ToolDefinition(
                name=tool_name,
                description=tool_data.get("description", ""),
                parameters=tool_data.get("inputSchema", {}),
                tool_type="mcp",
                mcp_server=server_name,
            )

            self._tools[tool_name] = tool_def
            tool_names.append(tool_name)

        self._mcp_tools[server_name] = tool_names
        logger.info(f"注册 MCP 工具: server={server_name}, count={len(tool_names)}")

    def unregister_mcp_tools(self, server_name: str) -> None:
        """
        取消注册 MCP 工具

        Args:
            server_name: MCP 服务器名称
        """
        if server_name not in self._mcp_tools:
            return

        for tool_name in self._mcp_tools[server_name]:
            if tool_name in self._tools:
                del self._tools[tool_name]

        del self._mcp_tools[server_name]
        logger.info(f"取消注册 MCP 工具: server={server_name}")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        获取工具定义

        Args:
            name: 工具名称

        Returns:
            工具定义，如果不存在则返回 None
        """
        return self._tools.get(name)

    def get_tools_by_server(self, server_name: str) -> List[ToolDefinition]:
        """
        获取指定 MCP 服务器的所有工具

        Args:
            server_name: MCP 服务器名称

        Returns:
            工具定义列表
        """
        if server_name not in self._mcp_tools:
            return []

        return [
            self._tools[name]
            for name in self._mcp_tools[server_name]
            if name in self._tools
        ]

    def list_all_tools(self) -> List[ToolDefinition]:
        """
        列出所有工具

        Returns:
            所有工具定义列表
        """
        return list(self._tools.values())

    def list_available_tools(self) -> List[ToolDefinition]:
        """
        列出所有可用工具

        Returns:
            可用工具定义列表
        """
        return [
            tool for tool in self._tools.values()
            if tool.status == ToolStatus.AVAILABLE
        ]

    def list_tools_by_type(self, tool_type: str) -> List[ToolDefinition]:
        """
        按类型列出工具

        Args:
            tool_type: 工具类型（local 或 mcp）

        Returns:
            工具定义列表
        """
        return [
            tool for tool in self._tools.values()
            if tool.tool_type == tool_type
        ]

    def update_tool_status(
        self,
        name: str,
        status: ToolStatus,
        error: Optional[str] = None
    ) -> None:
        """
        更新工具状态

        Args:
            name: 工具名称
            status: 新状态
            error: 错误信息（如果有）
        """
        tool = self._tools.get(name)
        if not tool:
            logger.warning(f"工具不存在: {name}")
            return

        tool.status = status
        if error:
            tool.last_error = error
            tool.error_count += 1

        logger.info(f"更新工具状态: name={name}, status={status}, error={error}")

    def record_tool_call(self, name: str, success: bool) -> None:
        """
        记录工具调用

        Args:
            name: 工具名称
            success: 是否成功
        """
        tool = self._tools.get(name)
        if not tool:
            return

        tool.call_count += 1
        if not success:
            tool.error_count += 1

    def disable_tool(self, name: str, reason: str) -> None:
        """
        禁用工具

        Args:
            name: 工具名称
            reason: 禁用原因
        """
        self.update_tool_status(name, ToolStatus.DISABLED, reason)
        logger.warning(f"工具已禁用: name={name}, reason={reason}")

    def enable_tool(self, name: str) -> None:
        """
        启用工具

        Args:
            name: 工具名称
        """
        self.update_tool_status(name, ToolStatus.AVAILABLE)
        logger.info(f"工具已启用: {name}")

    def clear_all(self) -> None:
        """清除所有工具"""
        self._tools.clear()
        self._mcp_tools.clear()
        logger.info("已清除所有工具")

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout: float = 30.0
    ) -> Any:
        """
        调用工具（带超时处理）

        Args:
            name: 工具名称
            arguments: 工具参数
            timeout: 超时时间（秒），默认 30 秒

        Returns:
            工具执行结果

        Raises:
            ValueError: 工具不存在或不可用
            TimeoutError: 工具调用超时
        """
        import asyncio

        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"工具不存在: {name}")

        if tool.status != ToolStatus.AVAILABLE:
            raise ValueError(f"工具不可用: {name}, 状态={tool.status}")

        if tool.tool_type == "local" and tool.handler:
            # 调用本地工具（带超时）
            try:
                # 使用 asyncio.wait_for 实现超时
                result = await asyncio.wait_for(
                    self._execute_local_tool(tool.handler, arguments),
                    timeout=timeout
                )
                self.record_tool_call(name, success=True)
                return result
            except asyncio.TimeoutError:
                self.record_tool_call(name, success=False)
                logger.error(f"本地工具调用超时: {name}, 超时={timeout}秒")
                raise TimeoutError(f"工具调用超时: {name}")
            except Exception as e:
                self.record_tool_call(name, success=False)
                logger.error(f"本地工具调用失败: {name}, error={e}")
                raise
        else:
            # MCP 工具由 MCP 适配器处理
            raise ValueError(f"MCP 工具需要通过 MCP 适配器调用: {name}")

    async def _execute_local_tool(self, handler, arguments: Dict[str, Any]) -> Any:
        """
        执行本地工具

        Args:
            handler: 工具处理函数
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        result = handler(**arguments)
        # 如果是协程，await
        if asyncio.iscoroutine(result):
            result = await result
        return result


# =============================================================================
# 全局工具注册表实例
# =============================================================================

tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表实例"""
    return tool_registry


# =============================================================================
# 本地工具装饰器
# =============================================================================

def local_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any]
):
    """
    本地工具装饰器

    用法：
    ```python
    @local_tool(
        name="get_weather",
        description="获取天气信息",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"}
            },
            "required": ["city"]
        }
    )
    async def get_weather(city: str) -> str:
        return f"{city}今天天气晴"
    ```

    Args:
        name: 工具名称
        description: 工具描述
        parameters: 参数模式（JSON Schema 格式）
    """
    def decorator(func: Callable) -> Callable:
        tool_registry.register_local_tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
        )
        return func
    return decorator
