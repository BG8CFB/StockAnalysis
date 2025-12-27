"""
MCP 会话管理器

基于官方 langchain-mcp-adapters 框架的会话管理。
提供 MCP 服务器的会话隔离和连接池管理。

核心功能：
1. 会话隔离 - 每个用户/任务拥有独立的 MCP 会话
2. 连接复用 - 使用官方框架的自动会话管理
3. 并发控制 - 限制单个服务器的最大并发数
4. 自动清理 - 清理过期和空闲的会话
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from langchain_core.tools import BaseTool

from modules.trading_agents.schemas import MCPServerConfigResponse
from ..tools.mcp_adapter import MCPAdapterFactory

logger = logging.getLogger(__name__)


class MCPSession:
    """
    MCP 会话实例

    封装官方 MultiServerMCPClient，提供会话级别的隔离。
    每个会话对应一个 MCP 服务器的连接实例。
    """

    def __init__(
        self,
        session_id: str,
        server: MCPServerConfigResponse,
        user_id: str,
        task_id: Optional[str] = None
    ):
        self.session_id = session_id
        self.server = server
        self.user_id = user_id
        self.task_id = task_id
        self.created_at = datetime.utcnow()
        self.last_used_at = datetime.utcnow()
        self.is_active = True

        # 使用官方 MCP 适配器
        self._adapter = MCPAdapterFactory.create_adapter(
            name=server.name,
            transport=server.transport.value,
            config={
                "command": server.command,
                "args": server.args,
                "env": server.env,
                "url": server.url,
                "auth_type": server.auth_type.value,
                "auth_token": server.auth_token,
            }
        )

        # 连接状态
        self._connected = False
        # 缓存的 LangChain 工具
        self._langchain_tools: List[BaseTool] = []

    async def _ensure_connected(self):
        """确保适配器已连接"""
        if not self._connected:
            success = await self._adapter.connect()
            if success:
                self._connected = True
                logger.debug(f"MCP 会话已连接: session_id={self.session_id}")
            else:
                raise RuntimeError(f"MCP 会话连接失败: session_id={self.session_id}")

    async def cleanup(self):
        """清理会话资源"""
        self.is_active = False
        if self._adapter:
            try:
                await self._adapter.disconnect()
                logger.debug(f"MCP 会话已清理: session_id={self.session_id}")
            except Exception as e:
                logger.error(f"MCP 会话清理失败: session_id={self.session_id}, error={e}")

    async def refresh(self):
        """刷新会话的最后使用时间"""
        self.last_used_at = datetime.utcnow()

    async def get_langchain_tools(self) -> List[BaseTool]:
        """
        获取 LangChain 工具列表

        Returns:
            LangChain BaseTool 列表，可直接用于 LangGraph 智能体
        """
        await self.refresh()
        await self._ensure_connected()

        if not self._langchain_tools:
            self._langchain_tools = await self._adapter.get_langchain_tools()

        return self._langchain_tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        await self.refresh()
        await self._ensure_connected()

        try:
            result = await self._adapter.call_tool(tool_name, arguments)
            return {
                "success": not result.get("isError", False),
                "data": result.get("content", []),
                "session_id": self.session_id,
            }
        except Exception as e:
            logger.error(
                f"MCP 工具调用失败: session_id={self.session_id}, "
                f"tool={tool_name}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "data": [{"type": "text", "text": str(e)}],
                "session_id": self.session_id,
            }

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取工具列表（原始 MCP 格式）

        Returns:
            工具列表
        """
        await self.refresh()
        await self._ensure_connected()
        return await self._adapter.list_tools()


class MCPSessionManager:
    """
    MCP 会话管理器

    管理：
    - 活跃会话池
    - 会话过期清理
    - 并发限制
    """

    # 会话配置
    SESSION_TIMEOUT = timedelta(minutes=30)  # 会话超时时间
    IDLE_TIMEOUT = timedelta(minutes=10)     # 空闲超时时间
    MAX_SESSIONS_PER_SERVER = 10             # 单个服务器最大会话数

    # 清理配置
    CLEANUP_INTERVAL = 300                   # 清理间隔（秒）

    def __init__(self):
        """初始化会话管理器"""
        # {server_id: {session_id: MCPSession}}
        self._active_sessions: Dict[str, Dict[str, MCPSession]] = {}

        # {session_id: server_id} - 用于快速查找会话所属服务器
        self._session_index: Dict[str, str] = {}

        # 后台清理任务
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info("MCP 会话管理器已初始化")

    async def start(self):
        """启动会话管理器（启动后台清理任务）"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("MCP 会话管理器后台清理任务已启动")

    async def stop(self):
        """停止会话管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # 清理所有会话
        for server_id in list(self._active_sessions.keys()):
            await self._cleanup_server_sessions(server_id)

        logger.info("MCP 会话管理器已停止")

    @asynccontextmanager
    async def get_session(
        self,
        server: MCPServerConfigResponse,
        user_id: str,
        task_id: Optional[str] = None
    ):
        """
        获取 MCP 会话（上下文管理器）

        用法：
            async with session_manager.get_session(server, user_id, task_id) as session:
                tools = await session.get_langchain_tools()
                result = await session.call_tool("tool_name", {...})

        Args:
            server: MCP 服务器配置
            user_id: 用户 ID
            task_id: 任务 ID（可选）

        Yields:
            MCPSession 实例
        """
        session = await self._acquire_session(server, user_id, task_id)

        try:
            yield session
        finally:
            # 不立即释放会话，而是标记为可复用
            # 后台清理任务会在会话过期时清理
            pass

    async def get_langchain_tools(
        self,
        server: MCPServerConfigResponse,
        user_id: str,
        task_id: Optional[str] = None
    ) -> List[BaseTool]:
        """
        获取 LangChain 工具列表（便捷方法）

        Args:
            server: MCP 服务器配置
            user_id: 用户 ID
            task_id: 任务 ID（可选）

        Returns:
            LangChain BaseTool 列表
        """
        async with self.get_session(server, user_id, task_id) as session:
            return await session.get_langchain_tools()

    async def _acquire_session(
        self,
        server: MCPServerConfigResponse,
        user_id: str,
        task_id: Optional[str] = None
    ) -> MCPSession:
        """
        获取或创建会话

        优先复用该用户/任务的现有会话，否则创建新会话。
        """
        server_id = server.id

        # 检查并发限制
        await self._ensure_concurrency_limit(server_id)

        # 查找现有会话（同一用户+任务的会话可复用）
        if task_id:
            existing_session = await self._find_task_session(server_id, user_id, task_id)
            if existing_session:
                logger.debug(f"复用现有任务会话: session_id={existing_session.session_id}")
                return existing_session

        # 查找该用户的空闲会话
        existing_session = await self._find_user_session(server_id, user_id)
        if existing_session:
            logger.debug(f"复用现有用户会话: session_id={existing_session.session_id}")
            return existing_session

        # 创建新会话
        session_id = f"{server_id}_{user_id}_{datetime.utcnow().timestamp()}"
        session = MCPSession(session_id, server, user_id, task_id)

        if server_id not in self._active_sessions:
            self._active_sessions[server_id] = {}

        self._active_sessions[server_id][session_id] = session
        self._session_index[session_id] = server_id

        logger.info(
            f"创建新 MCP 会话: session_id={session_id}, "
            f"server={server.name}, user={user_id}, task={task_id}"
        )

        return session

    async def _find_task_session(
        self,
        server_id: str,
        user_id: str,
        task_id: str
    ) -> Optional[MCPSession]:
        """查找同一任务的会话"""
        if server_id not in self._active_sessions:
            return None

        for session in self._active_sessions[server_id].values():
            if session.user_id == user_id and session.task_id == task_id and session.is_active:
                return session
        return None

    async def _find_user_session(
        self,
        server_id: str,
        user_id: str
    ) -> Optional[MCPSession]:
        """查找该用户的会话"""
        if server_id not in self._active_sessions:
            return None

        for session in self._active_sessions[server_id].values():
            if session.user_id == user_id and session.is_active:
                return session
        return None

    async def _ensure_concurrency_limit(self, server_id: str):
        """
        确保并发限制

        如果会话数达到上限，等待或清理空闲会话
        """
        if server_id not in self._active_sessions:
            return

        sessions = self._active_sessions[server_id]
        active_count = sum(1 for s in sessions.values() if s.is_active)

        if active_count >= self.MAX_SESSIONS_PER_SERVER:
            # 尝试清理空闲会话
            await self._cleanup_idle_sessions(server_id)

            # 再次检查
            active_count = sum(1 for s in sessions.values() if s.is_active)
            if active_count >= self.MAX_SESSIONS_PER_SERVER:
                logger.warning(
                    f"MCP 服务器会话数已达上限: server_id={server_id}, "
                    f"max={self.MAX_SESSIONS_PER_SERVER}"
                )
                await asyncio.sleep(0.1)  # 简单的退避策略

    async def _cleanup_idle_sessions(self, server_id: str):
        """清理空闲会话"""
        if server_id not in self._active_sessions:
            return

        now = datetime.utcnow()
        sessions_to_remove = []

        for session_id, session in self._active_sessions[server_id].items():
            if not session.is_active:
                continue

            idle_time = now - session.last_used_at
            if idle_time > self.IDLE_TIMEOUT:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            await self._remove_session(session_id)

        if sessions_to_remove:
            logger.info(
                f"清理空闲会话: server_id={server_id}, "
                f"count={len(sessions_to_remove)}"
            )

    async def _cleanup_server_sessions(self, server_id: str):
        """清理服务器的所有会话"""
        if server_id not in self._active_sessions:
            return

        session_ids = list(self._active_sessions[server_id].keys())
        for session_id in session_ids:
            await self._remove_session(session_id)

        logger.info(f"清理服务器所有会话: server_id={server_id}, count={len(session_ids)}")

    async def _remove_session(self, session_id: str):
        """移除会话"""
        if session_id not in self._session_index:
            return

        server_id = self._session_index[session_id]
        if server_id in self._active_sessions and session_id in self._active_sessions[server_id]:
            session = self._active_sessions[server_id][session_id]
            await session.cleanup()
            del self._active_sessions[server_id][session_id]

            # 如果该服务器没有会话了，删除服务器条目
            if not self._active_sessions[server_id]:
                del self._active_sessions[server_id]

        del self._session_index[session_id]

    async def _cleanup_loop(self):
        """后台清理循环"""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"后台清理任务错误: {e}")

    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.utcnow()
        cleaned_count = 0

        for server_id, sessions in list(self._active_sessions.items()):
            sessions_to_remove = []

            for session_id, session in sessions.items():
                # 清理非活跃会话
                if not session.is_active:
                    sessions_to_remove.append(session_id)
                    continue

                # 清理超时会话
                age = now - session.created_at
                if age > self.SESSION_TIMEOUT:
                    sessions_to_remove.append(session_id)
                    continue

                # 清理空闲超时会话
                idle_time = now - session.last_used_at
                if idle_time > self.IDLE_TIMEOUT:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                await self._remove_session(session_id)
                cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"定期清理过期会话: count={cleaned_count}")

    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        total_sessions = sum(len(sessions) for sessions in self._active_sessions.values())
        active_sessions = sum(
            sum(1 for s in sessions.values() if s.is_active)
            for sessions in self._active_sessions.values()
        )

        server_stats = {}
        for server_id, sessions in self._active_sessions.items():
            server_stats[server_id] = {
                "total": len(sessions),
                "active": sum(1 for s in sessions.values() if s.is_active),
            }

        return {
            "total_servers": len(self._active_sessions),
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "server_stats": server_stats,
        }


# =============================================================================
# 全局会话管理器实例
# =============================================================================

_mcp_session_manager: Optional[MCPSessionManager] = None


def get_mcp_session_manager() -> MCPSessionManager:
    """获取全局 MCP 会话管理器实例"""
    global _mcp_session_manager
    if _mcp_session_manager is None:
        _mcp_session_manager = MCPSessionManager()
    return _mcp_session_manager
