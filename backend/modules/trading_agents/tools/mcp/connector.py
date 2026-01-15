"""
MCP 连接器

连接核心 MCP 模块，为 Phase 1 智能体提供工具调用能力。

**版本**: v1.0
**最后更新**: 2026-01-15
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.tools import BaseTool

from modules.mcp.pool.pool import mcp_pool
from modules.mcp.core.adapter import MCPAdapter

logger = logging.getLogger(__name__)


class MCPConnector:
    """
    MCP 连接器

    负责与核心 MCP 模块建立连接，并将 MCP 工具转换为 LangChain 可用的工具格式。
    """

    def __init__(
        self,
        user_id: str,
        server_names: Optional[List[str]] = None
    ):
        """
        初始化 MCP 连接器

        Args:
            user_id: 用户 ID（用于隔离）
            server_names: 要连接的 MCP 服务器名称列表，None 表示连接所有
        """
        self.user_id = user_id
        self.server_names = server_names
        self._adapters: Dict[str, MCPAdapter] = {}

    async def connect(self) -> None:
        """连接到所有配置的 MCP 服务器"""
        if self.server_names:
            for server_name in self.server_names:
                await self._connect_server(server_name)
        else:
            # 连接所有可用的服务器
            logger.info(f"[MCP Connector] 为用户 {self.user_id} 连接所有可用服务器")
            # TODO: 从配置获取所有服务器名称

    async def _connect_server(self, server_name: str) -> None:
        """
        连接到单个 MCP 服务器

        Args:
            server_name: 服务器名称
        """
        try:
            # 从 MCP 连接池获取适配器
            adapter = await mcp_pool.get_adapter(
                user_id=self.user_id,
                server_name=server_name
            )
            self._adapters[server_name] = adapter
            logger.info(f"[MCP Connector] 已连接到服务器: {server_name}")

        except Exception as e:
            logger.error(f"[MCP Connector] 连接服务器 {server_name} 失败: {e}")

    async def get_tools(self) -> List[BaseTool]:
        """
        获取所有可用的 MCP 工具（LangChain 格式）

        Returns:
            LangChain 工具列表
        """
        tools = []
        for server_name, adapter in self._adapters.items():
            try:
                server_tools = await adapter.get_langchain_tools()
                tools.extend(server_tools)
                logger.debug(
                    f"[MCP Connector] 从服务器 {server_name} 获取 {len(server_tools)} 个工具"
                )
            except Exception as e:
                logger.error(f"[MCP Connector] 获取工具失败 ({server_name}): {e}")

        logger.info(f"[MCP Connector] 总共获取 {len(tools)} 个工具")
        return tools

    async def disconnect(self) -> None:
        """断开所有 MCP 服务器连接"""
        for server_name in list(self._adapters.keys()):
            try:
                await mcp_pool.release_adapter(
                    user_id=self.user_id,
                    server_name=server_name
                )
                del self._adapters[server_name]
                logger.info(f"[MCP Connector] 已断开服务器: {server_name}")
            except Exception as e:
                logger.error(f"[MCP Connector] 断开服务器 {server_name} 失败: {e}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
