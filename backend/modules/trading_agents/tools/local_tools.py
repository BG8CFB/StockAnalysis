"""
本地工具接口（预留）

为本地工具提供统一的接口定义和示例实现。
"""

import logging
from typing import Dict, Any, Callable, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LocalTool(ABC):
    """
    本地工具抽象基类

    所有本地工具都应继承此类并实现 execute 方法。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        工具参数模式（JSON Schema 格式）

        示例：
        ```python
        {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                }
            },
            "required": ["city"]
        }
        ```
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            执行结果，格式：{"success": bool, "result": Any, "error": Optional[str]}
        """
        pass


# =============================================================================
# 示例工具实现
# =============================================================================

class ExampleLocalTool(LocalTool):
    """示例本地工具"""

    @property
    def name(self) -> str:
        return "example_tool"

    @property
    def description(self) -> str:
        return "这是一个示例工具，返回输入的参数"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "输入的消息"
                }
            },
            "required": ["message"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        message = kwargs.get("message", "")
        logger.info(f"执行示例工具: message={message}")
        return {
            "success": True,
            "result": f"收到消息: {message}",
            "error": None
        }


# =============================================================================
# 工具执行器
# =============================================================================

class LocalToolExecutor:
    """本地工具执行器"""

    def __init__(self):
        self._tools: Dict[str, LocalTool] = {}

    def register_tool(self, tool: LocalTool) -> None:
        """
        注册本地工具

        Args:
            tool: 工具实例
        """
        self._tools[tool.name] = tool
        logger.info(f"注册本地工具: {tool.name}")

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行本地工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            执行结果
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return {
                "success": False,
                "result": None,
                "error": f"工具不存在: {tool_name}"
            }

        try:
            logger.info(f"执行本地工具: {tool_name}, parameters={parameters}")
            result = await tool.execute(**parameters)
            return result
        except Exception as e:
            logger.error(f"工具执行失败: {tool_name}, error={e}")
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }

    def list_tools(self) -> list[str]:
        """
        列出所有已注册的工具

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())


# =============================================================================
# 全局本地工具执行器实例
# =============================================================================

local_tool_executor = LocalToolExecutor()


def get_local_tool_executor() -> LocalToolExecutor:
    """获取全局本地工具执行器实例"""
    return local_tool_executor
