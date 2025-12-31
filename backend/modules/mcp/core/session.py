"""
MCP 会话管理

提供 MCP 会话的创建、管理和清理功能。
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from langchain_mcp_adapters.client import MultiServerMCPClient
from modules.mcp.config.loader import (
    get_session_timeout,
    get_session_idle_timeout,
)

logger = logging.getLogger(__name__)


class MCPSession:
    """
    MCP 会话封装

    包装 langchain-mcp-adapters 的会话对象，提供额外的生命周期管理。
    """

    def __init__(
        self,
        server_name: str,
        client: MultiServerMCPClient,
        session: Any,
    ):
        """
        初始化会话

        Args:
            server_name: 服务器名称
            client: MultiServerMCPClient 实例
            session: 原始会话对象
        """
        self.server_name = server_name
        self._client = client
        self._session = session
        self.created_at = datetime.utcnow()
        self.last_used_at = datetime.utcnow()

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        调用工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        self.last_used_at = datetime.utcnow()
        return await self._session.call_tool(tool_name, arguments)

    async def close(self) -> None:
        """关闭会话"""
        if hasattr(self._session, 'close'):
            await self._session.close()
        logger.debug(f"[MCPSession] 会话已关闭: {self.server_name}")

    @property
    def idle_time(self) -> float:
        """获取空闲时长（秒）"""
        return (datetime.utcnow() - self.last_used_at).total_seconds()

    @property
    def age(self) -> float:
        """获取会话年龄（秒）"""
        return (datetime.utcnow() - self.created_at).total_seconds()


class MCPSessionManager:
    """
    MCP 会话管理器

    管理多个 MCP 会话的生命周期，提供会话复用和自动清理功能。

    注意：langchain-mcp-adapters 已经内置了会话管理，
    这个管理器主要用于高级场景（如会话复用、预热等）。
    """

    # 会话配置（从配置文件加载）
    SESSION_TIMEOUT = get_session_timeout()
    IDLE_TIMEOUT = get_session_idle_timeout()

    def __init__(self):
        """初始化会话管理器"""
        self._sessions: Dict[str, MCPSession] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self, interval: int = 60) -> None:
        """
        启动定期清理任务

        Args:
            interval: 清理间隔（秒）
        """
        if self._cleanup_task and not self._cleanup_task.done():
            logger.warning("[MCPSessionManager] 清理任务已在运行")
            return

        self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval))
        logger.info(f"[MCPSessionManager] 启动清理任务，间隔: {interval}秒")

    async def stop_cleanup_task(self) -> None:
        """停止清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("[MCPSessionManager] 清理任务已停止")

    async def _cleanup_loop(self, interval: int) -> None:
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(interval)
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MCPSessionManager] 清理任务出错: {e}", exc_info=True)

    async def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        async with self._lock:
            now = datetime.utcnow()
            to_remove = []

            for session_id, session in self._sessions.items():
                # 检查会话超时
                if session.age > self.SESSION_TIMEOUT:
                    to_remove.append(session_id)
                    logger.info(
                        f"[MCPSessionManager] 会话超时: {session_id}, "
                        f"age={session.age:.0f}s"
                    )
                # 检查空闲超时
                elif session.idle_time > self.IDLE_TIMEOUT:
                    to_remove.append(session_id)
                    logger.info(
                        f"[MCPSessionManager] 会话空闲超时: {session_id}, "
                        f"idle={session.idle_time:.0f}s"
                    )

            for session_id in to_remove:
                session = self._sessions.pop(session_id)
                await session.close()

            if to_remove:
                logger.info(f"[MCPSessionManager] 清理过期会话: {len(to_remove)} 个")

            return len(to_remove)

    async def get_or_create_session(
        self,
        server_name: str,
        connection_config: Dict[str, Any],
    ) -> MCPSession:
        """
        获取或创建会话

        Args:
            server_name: 服务器名称
            connection_config: 连接配置

        Returns:
            MCPSession 对象
        """
        async with self._lock:
            # 检查是否有可用会话
            session_id = f"{server_name}"
            existing_session = self._sessions.get(session_id)

            if existing_session and existing_session.idle_time < self.IDLE_TIMEOUT:
                logger.debug(f"[MCPSessionManager] 复用现有会话: {session_id}")
                existing_session.last_used_at = datetime.utcnow()
                return existing_session

            # 创建新会话
            client = MultiServerMCPClient({
                server_name: connection_config
            })

            # 获取会话对象
            async with client.session(server_name) as session:
                # 创建包装对象
                wrapped_session = MCPSession(server_name, client, session)
                self._sessions[session_id] = wrapped_session

                logger.info(f"[MCPSessionManager] 创建新会话: {session_id}")
                return wrapped_session

    async def close_session(self, server_name: str) -> None:
        """
        关闭指定服务器的会话

        Args:
            server_name: 服务器名称
        """
        async with self._lock:
            session_id = f"{server_name}"
            session = self._sessions.pop(session_id, None)
            if session:
                await session.close()
                logger.info(f"[MCPSessionManager] 关闭会话: {session_id}")

    async def close_all_sessions(self) -> None:
        """关闭所有会话"""
        async with self._lock:
            for session_id, session in self._sessions.items():
                try:
                    await session.close()
                except Exception as e:
                    logger.error(
                        f"[MCPSessionManager] 关闭会话出错: {session_id}, error={e}",
                        exc_info=True
                    )

            self._sessions.clear()
            logger.info("[MCPSessionManager] 所有会话已关闭")

    def get_session_count(self) -> int:
        """获取活跃会话数量"""
        return len(self._sessions)

    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        sessions = list(self._sessions.values())
        return {
            "total": len(sessions),
            "sessions": [
                {
                    "server_name": s.server_name,
                    "age": s.age,
                    "idle_time": s.idle_time,
                    "created_at": s.created_at.isoformat(),
                    "last_used_at": s.last_used_at.isoformat(),
                }
                for s in sessions
            ],
        }


# 全局会话管理器实例
_mcp_session_manager: Optional[MCPSessionManager] = None


def get_mcp_session_manager() -> MCPSessionManager:
    """获取全局 MCP 会话管理器实例"""
    global _mcp_session_manager
    if _mcp_session_manager is None:
        _mcp_session_manager = MCPSessionManager()
    return _mcp_session_manager
