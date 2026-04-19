"""
MCP 连接器

连接核心 MCP 模块，为 Phase 1 智能体提供工具调用能力。

**版本**: v2.0 (修复版 - 正确使用 MCP 连接池)
**最后更新**: 2026-01-16

修复说明：
- 移除不存在的 MCPAdapter 类引用
- 使用正确的 MCP 连接池 API
- 直接访问连接对象的 tools 属性
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool

from core.db.mongodb import mongodb
from core.mcp.pool.pool import get_mcp_connection_pool

logger = logging.getLogger(__name__)


class MCPConnector:
    """
    MCP 连接器（修复版）

    负责与核心 MCP 模块建立连接，并将 MCP 工具转换为 LangChain 可用的工具格式。

    正确使用方式：
    1. 通过 server_name 查找 MCP 服务器配置
    2. 使用连接池获取连接
    3. 直接访问连接的 tools 属性
    4. 使用后释放连接
    """

    def __init__(self, user_id: str, task_id: str, server_names: Optional[List[str]] = None):
        """
        初始化 MCP 连接器

        Args:
            user_id: 用户 ID（用于隔离）
            task_id: 任务 ID（用于连接管理）
            server_names: 要连接的 MCP 服务器名称列表，None 表示连接所有可用服务器
        """
        self.user_id = user_id
        self.task_id = task_id
        self.server_names = server_names
        self._connections: Dict[str, Any] = {}  # server_name -> MCPConnection
        self._pool = get_mcp_connection_pool()

    async def connect(self) -> None:
        """连接到所有配置的 MCP 服务器"""
        if self.server_names:
            # 连接指定的服务器
            for server_name in self.server_names:
                await self._connect_server_by_name(server_name)
        else:
            # 连接所有启用的服务器
            logger.info(f"[MCP Connector] 为任务 {self.task_id} 连接所有可用服务器")
            await self._connect_all_enabled_servers()

    async def _connect_all_enabled_servers(self) -> None:
        """连接所有启用的 MCP 服务器"""
        try:
            # 从数据库查询所有启用的服务器
            collection = mongodb.get_collection("mcp_servers")
            cursor = collection.find({"enabled": True, "status": "available"})

            async for server_doc in cursor:
                server_id = str(server_doc["_id"])
                server_name = server_doc.get("name")

                if server_name:
                    await self._connect_server_by_id(server_id, server_name)

        except Exception as e:
            logger.error(f"[MCP Connector] 查询可用服务器失败: {e}")

    async def _connect_server_by_name(self, server_name: str) -> None:
        """
        通过服务器名称连接

        Args:
            server_name: 服务器名称
        """
        try:
            # 从数据库查找服务器配置
            collection = mongodb.get_collection("mcp_servers")
            server_doc = await collection.find_one({"name": server_name, "enabled": True})

            if not server_doc:
                logger.warning(f"[MCP Connector] 服务器不存在或未启用: {server_name}")
                return

            server_id = str(server_doc["_id"])
            await self._connect_server_by_id(server_id, server_name)

        except Exception as e:
            logger.error(f"[MCP Connector] 连接服务器 {server_name} 失败: {e}")

    async def _connect_server_by_id(self, server_id: str, server_name: str) -> None:
        """
        通过服务器 ID 连接

        Args:
            server_id: 服务器 ID
            server_name: 服务器名称
        """
        try:
            # 使用连接池获取连接
            conn = await self._pool.acquire_connection(
                server_id=server_id, task_id=self.task_id, user_id=self.user_id
            )

            self._connections[server_name] = conn
            logger.info(
                f"[MCP Connector] 已连接到服务器: {server_name} "
                f"(连接ID: {conn.connection_id}, 工具数: {len(conn.tools)})"
            )

        except Exception as e:
            logger.error(f"[MCP Connector] 连接服务器 {server_name} (ID: {server_id}) 失败: {e}")

    async def get_tools(self) -> List[BaseTool]:
        """
        获取所有可用的 MCP 工具（LangChain 格式）

        Returns:
            LangChain 工具列表
        """
        tools = []

        for server_name, conn in self._connections.items():
            try:
                # 直接访问连接对象的 tools 属性（不是方法！）
                server_tools = conn.tools
                tools.extend(server_tools)

                logger.debug(
                    f"[MCP Connector] 从服务器 {server_name} 获取 {len(server_tools)} 个工具"
                )

            except Exception as e:
                logger.error(f"[MCP Connector] 获取工具失败 ({server_name}): {e}")

        logger.info(f"[MCP Connector] 总共获取 {len(tools)} 个 MCP 工具")
        return tools

    async def disconnect(self) -> None:
        """断开所有 MCP 服务器连接"""
        for server_name, conn in list(self._connections.items()):
            try:
                # 使用连接池释放连接
                await self._pool.release_connection(conn.connection_id)

                del self._connections[server_name]
                logger.info(f"[MCP Connector] 已断开服务器: {server_name}")

            except Exception as e:
                logger.error(f"[MCP Connector] 断开服务器 {server_name} 失败: {e}")

    async def __aenter__(self) -> "MCPConnector":
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """异步上下文管理器出口"""
        await self.disconnect()
