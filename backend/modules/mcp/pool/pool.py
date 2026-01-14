"""
MCP 统一连接池

提供任务级长连接管理和统一并发控制。
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from core.db.mongodb import mongodb
from modules.mcp.pool.connection import MCPConnection, ConnectionState
from modules.mcp.schemas import MCPServerConfigResponse
from modules.mcp.config.loader import (
    get_pool_personal_max_concurrency,
    get_pool_public_per_user_max,
    get_pool_personal_queue_size,
    get_pool_public_queue_size,
)

logger = logging.getLogger(__name__)


class MCPConnectionPool:
    """
    统一 MCP 连接池

    功能：
    - 管理所有活跃的 MCP 长连接
    - 实现并发控制（从配置文件加载）
    - 支持连接复用
    - MCP 关闭后不影响进行中的任务
    """

    # 并发参数配置（从配置文件加载）
    PERSONAL_MAX_CONCURRENCY = get_pool_personal_max_concurrency()
    PUBLIC_PER_USER_MAX = get_pool_public_per_user_max()

    def __init__(self):
        """初始化连接池"""
        # 服务器配置注册表（从数据库加载）
        self._servers: Dict[str, Dict[str, Any]] = {}

        # 活跃连接
        self._connections: Dict[str, MCPConnection] = {}

        # 并发控制（每 server_id 独立）
        # 结构: _semaphores[server_id][user_id] = Semaphore
        self._semaphores: Dict[str, Dict[str, asyncio.Semaphore]] = {}

        # 请求队列（每 server_id 独立）
        # 结构: _queues[server_id] = Queue
        self._queues: Dict[str, asyncio.Queue] = {}

        # 任务-连接映射
        self._task_connections: Dict[str, str] = {}  # task_id -> connection_id

        # 锁
        self._server_lock = asyncio.Lock()
        self._connection_lock = asyncio.Lock()

        logger.info("[MCPConnectionPool] 连接池初始化完成")

    # ========================================================================
    # 服务器配置管理
    # ========================================================================

    async def register_server(self, server_config: MCPServerConfigResponse) -> None:
        """
        注册服务器到池子

        Args:
            server_config: 服务器配置
        """
        async with self._server_lock:
            server_id = server_config.id

            if server_id in self._servers:
                logger.warning(f"[MCPConnectionPool] 服务器已注册: {server_id}")
                return

            # 初始化该服务器的并发控制和队列
            self._servers[server_id] = {
                "id": server_id,
                "name": server_config.name,
                "is_system": server_config.is_system,
                "enabled": server_config.enabled,
                "config": server_config,
            }

            # 初始化用户级信号量
            self._semaphores[server_id] = {}

            # 初始化请求队列（根据服务器类型使用不同队列大小）
            if server_config.is_system:
                queue_size = get_pool_public_queue_size()
            else:
                queue_size = get_pool_personal_queue_size()
            self._queues[server_id] = asyncio.Queue(maxsize=queue_size)

            logger.info(f"[MCPConnectionPool] 注册服务器: {server_id} ({server_config.name})")

    async def unregister_server(self, server_id: str) -> None:
        """
        从池子注销服务器

        Args:
            server_id: 服务器 ID
        """
        async with self._server_lock:
            if server_id not in self._servers:
                logger.warning(f"[MCPConnectionPool] 服务器未注册: {server_id}")
                return

            # 禁用服务器（内部版本，避免死锁）
            await self._disable_server_no_lock(server_id)

            # 清理资源
            del self._servers[server_id]
            del self._semaphores[server_id]
            del self._queues[server_id]

            logger.info(f"[MCPConnectionPool] 注销服务器: {server_id}")

    async def disable_server(self, server_id: str) -> None:
        """
        禁用服务器（不影响进行中的任务）

        Args:
            server_id: 服务器 ID
        """
        async with self._server_lock:
            await self._disable_server_no_lock(server_id)

    async def _disable_server_no_lock(self, server_id: str) -> None:
        """
        禁用服务器（内部版本，不获取锁，假设已获取）

        Args:
            server_id: 服务器 ID
        """
        if server_id not in self._servers:
            return

        # 标记为禁用
        self._servers[server_id]["enabled"] = False

        # 遍历活跃连接，标记为关闭状态
        # 注意：不立即断开，让任务自然完成
        connections_to_close = []
        for conn_id, conn in self._connections.items():
            if conn.server_id == server_id and conn.is_active:
                connections_to_close.append(conn)

        for conn in connections_to_close:
            logger.info(
                f"[MCPConnectionPool] 服务器 {server_id} 被禁用，"
                f"连接 {conn_id} 将在任务完成后关闭"
            )
            # 标记为关闭（但不强制断开）
            await conn.mark_complete()

        logger.info(f"[MCPConnectionPool] 禁用服务器: {server_id}")

    async def reload_server_config(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        从数据库重新加载服务器配置

        Args:
            server_id: 服务器 ID

        Returns:
            服务器配置字典或 None
        """
        collection = mongodb.get_collection("mcp_servers")
        from bson import ObjectId

        try:
            object_id = ObjectId(server_id)
        except Exception:
            return None

        doc = await collection.find_one({"_id": object_id})
        if not doc:
            return None

        config = MCPServerConfigResponse.from_db(doc)

        # 更新内部配置
        async with self._server_lock:
            if server_id in self._servers:
                self._servers[server_id]["config"] = config
                self._servers[server_id]["enabled"] = config.enabled

        return {
            "id": config.id,
            "name": config.name,
            "is_system": config.is_system,
            "enabled": config.enabled,
            "config": config,
        }

    # ========================================================================
    # 连接获取与释放
    # ========================================================================

    async def acquire_connection(
        self,
        server_id: str,
        task_id: str,
        user_id: str,
    ) -> MCPConnection:
        """
        获取或创建长连接

        Args:
            server_id: MCP 服务器 ID
            task_id: 任务 ID
            user_id: 用户 ID

        Returns:
            MCPConnection 对象

        Raises:
            RuntimeError: 服务器不存在或已禁用
            MCPConnectionError: 连接失败时抛出
        """
        # 检查服务器配置
        server_info = self._servers.get(server_id)
        if not server_info:
            # 尝试从数据库加载
            server_info = await self.reload_server_config(server_id)
            if not server_info:
                raise RuntimeError(f"MCP 服务器不存在: {server_id}")

        if not server_info["enabled"]:
            raise RuntimeError(f"MCP 服务器已禁用: {server_id}")

        # 检查是否已有该任务的连接
        existing_conn_id = self._task_connections.get(task_id)
        if existing_conn_id:
            conn = self._connections.get(existing_conn_id)
            if conn and conn.is_usable:
                logger.debug(
                    f"[MCPConnectionPool] 复用现有连接: {existing_conn_id} for task {task_id}"
                )
                conn.last_used_at = datetime.utcnow()
                return conn
            else:
                # 连接不可用，从映射中移除
                logger.warning(
                    f"[MCPConnectionPool] 现有连接不可用: {existing_conn_id}，将创建新连接"
                )
                if task_id in self._task_connections:
                    del self._task_connections[task_id]

        # 获取用户级信号量（并发控制）
        semaphore = self._get_user_semaphore(server_id, user_id)

        # 等待获取信号量（或队列中有空位）
        await semaphore.acquire()

        try:
            # 创建新连接
            async with self._connection_lock:
                # 构建连接配置
                connection_config = self._build_connection_config(server_info["config"])

                # 创建连接对象
                conn = MCPConnection(
                    server_id=server_id,
                    server_name=server_info["name"],
                    task_id=task_id,
                    user_id=user_id,
                    connection_config=connection_config,
                )

                # 初始化连接
                await conn.initialize()

                # 注册到连接池
                self._connections[conn.connection_id] = conn
                self._task_connections[task_id] = conn.connection_id

                logger.info(
                    f"[MCPConnectionPool] 创建新连接: {conn.connection_id} "
                    f"(server={server_id}, task={task_id}, user={user_id})"
                )

                return conn

        except Exception as e:
            semaphore.release()
            logger.error(
                f"[MCPConnectionPool] 创建连接失败: server_id={server_id}, error={e}",
                exc_info=True
            )
            raise

    async def release_connection(self, connection_id: str) -> None:
        """
        释放连接（标记完成）

        Args:
            connection_id: 连接 ID
        """
        conn = self._connections.get(connection_id)
        if not conn:
            logger.warning(f"[MCPConnectionPool] 连接不存在: {connection_id}")
            return

        # 标记连接为完成（启动 10 秒倒计时）
        await conn.mark_complete()

        # 从任务-连接映射中移除
        if conn.task_id in self._task_connections:
            del self._task_connections[conn.task_id]

        # 释放信号量
        server_id = conn.server_id
        user_id = conn.user_id
        semaphore = self._get_user_semaphore(server_id, user_id)
        semaphore.release()

        logger.info(
            f"[MCPConnectionPool] 释放连接: {connection_id} "
            f"(server={server_id}, user={user_id})"
        )

    async def mark_task_complete(self, task_id: str) -> None:
        """
        标记任务完成（便捷方法）

        Args:
            task_id: 任务 ID
        """
        connection_id = self._task_connections.get(task_id)
        if connection_id:
            await self.release_connection(connection_id)

    async def mark_task_failed(self, task_id: str) -> None:
        """
        标记任务失败（便捷方法）

        Args:
            task_id: 任务 ID
        """
        connection_id = self._task_connections.get(task_id)
        if connection_id:
            conn = self._connections.get(connection_id)
            if conn:
                await conn.mark_failed()
                # 从任务-连接映射中移除
                del self._task_connections[task_id]
                # 释放信号量
                semaphore = self._get_user_semaphore(conn.server_id, conn.user_id)
                semaphore.release()

    async def mark_task_cancelled(self, task_id: str) -> None:
        """
        标记任务取消（便捷方法）

        Args:
            task_id: 任务 ID
        """
        connection_id = self._task_connections.get(task_id)
        if connection_id:
            conn = self._connections.get(connection_id)
            if conn:
                # 标记连接为完成（而不是失败）
                await conn.mark_complete()
                # 从任务-连接映射中移除
                del self._task_connections[task_id]
                # 释放信号量
                semaphore = self._get_user_semaphore(conn.server_id, conn.user_id)
                semaphore.release()
                logger.info(
                    f"[MCPConnectionPool] 任务取消，释放连接: {connection_id} "
                    f"(server={conn.server_id}, task={task_id})"
                )

    # ========================================================================
    # 连接查询与统计
    # ========================================================================

    async def get_connection_stats(self, server_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取连接统计

        Args:
            server_id: 服务器 ID（可选，不指定则返回所有服务器的统计）

        Returns:
            统计信息字典
        """
        if server_id:
            server_conns = [
                conn for conn in self._connections.values()
                if conn.server_id == server_id
            ]
        else:
            server_conns = list(self._connections.values())

        active = len([c for c in server_conns if c.state == ConnectionState.ACTIVE])
        closing = len([c for c in server_conns if c.state == ConnectionState.CLOSING])
        failed_cleanup = len([c for c in server_conns if c.state == ConnectionState.FAILED_CLEANUP])
        closed = len([c for c in server_conns if c.state == ConnectionState.CLOSED])

        return {
            "total": len(server_conns),
            "active": active,
            "closing": closing,
            "failed_cleanup": failed_cleanup,
            "closed": closed,
            "connections": [
                {
                    "connection_id": c.connection_id,
                    "server_id": c.server_id,
                    "server_name": c.server_name,
                    "task_id": c.task_id,
                    "user_id": c.user_id,
                    "state": c.state.value,
                    "created_at": c.created_at.isoformat(),
                    "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
                }
                for c in server_conns
            ],
        }

    # ========================================================================
    # 内部辅助方法
    # ========================================================================

    def _get_user_semaphore(self, server_id: str, user_id: str) -> asyncio.Semaphore:
        """
        获取用户级信号量

        Args:
            server_id: 服务器 ID
            user_id: 用户 ID

        Returns:
            asyncio.Semaphore 对象
        """
        if server_id not in self._semaphores:
            self._semaphores[server_id] = {}

        if user_id not in self._semaphores[server_id]:
            # 根据服务器类型选择并发限制
            server_info = self._servers.get(server_id, {})
            is_system = server_info.get("is_system", False)

            if is_system:
                # 公共 MCP：每用户 10 并发
                limit = self.PUBLIC_PER_USER_MAX
            else:
                # 个人 MCP：每用户 100 并发
                limit = self.PERSONAL_MAX_CONCURRENCY

            self._semaphores[server_id][user_id] = asyncio.Semaphore(limit)
            logger.info(
                f"[MCPConnectionPool] 创建用户信号量: "
                f"server={server_id}, user={user_id}, limit={limit}"
            )

        return self._semaphores[server_id][user_id]

    def _build_connection_config(self, server_config: MCPServerConfigResponse) -> Dict[str, Any]:
        """
        构建 MCP 连接配置

        Args:
            server_config: 服务器配置

        Returns:
            连接配置字典
        """
        from modules.mcp.core.adapter import (
            build_stdio_connection,
            build_sse_connection,
            build_streamable_http_connection,
            build_websocket_connection,
        )

        transport = server_config.transport

        if transport.value == "stdio":
            return build_stdio_connection(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env,
            )
        elif transport.value == "sse":
            return build_sse_connection(
                url=server_config.url,
                headers=server_config.headers,
            )
        elif transport.value in ("http", "streamable_http"):
            return build_streamable_http_connection(
                url=server_config.url,
                headers=server_config.headers,
            )
        elif transport.value == "websocket":
            return build_websocket_connection(
                url=server_config.url,
            )
        else:
            raise ValueError(f"不支持的传输模式: {transport}")

    async def cleanup_closed_connections(self) -> int:
        """
        清理已关闭的连接

        Returns:
            清理的连接数量
        """
        async with self._connection_lock:
            to_remove = [
                conn_id for conn_id, conn in self._connections.items()
                if conn.state == ConnectionState.CLOSED
            ]

            for conn_id in to_remove:
                del self._connections[conn_id]

            if to_remove:
                logger.info(f"[MCPConnectionPool] 清理已关闭连接: {len(to_remove)} 个")

            return len(to_remove)

    async def cleanup_idle_semaphores(
        self,
        idle_threshold_seconds: int = 3600
    ) -> int:
        """
        清理空闲的用户信号量（释放内存）

        Args:
            idle_threshold_seconds: 空闲阈值（秒），默认1小时

        Returns:
            清理的信号量数量
        """
        cleaned_count = 0

        async with self._server_lock:
            for server_id, user_semaphores in list(self._semaphores.items()):
                # 检查该服务器下的每个用户信号量
                idle_users = []

                for user_id in list(user_semaphores.keys()):
                    # 检查该用户是否有活跃的连接
                    has_active_connection = any(
                        conn.user_id == user_id and conn.server_id == server_id and conn.is_active
                        for conn in self._connections.values()
                    )

                    # 如果没有活跃连接，则标记为空闲
                    if not has_active_connection:
                        idle_users.append(user_id)

                # 删除空闲用户的信号量
                for user_id in idle_users:
                    del self._semaphores[server_id][user_id]
                    cleaned_count += 1
                    logger.debug(
                        f"[MCPConnectionPool] 清理空闲信号量: "
                        f"server={server_id}, user={user_id}"
                    )

                # 如果某个服务器的所有信号量都被清理了，删除该服务器的条目
                if not self._semaphores[server_id]:
                    del self._semaphores[server_id]

        if cleaned_count > 0:
            logger.info(f"[MCPConnectionPool] 清理空闲信号量: {cleaned_count} 个")

        return cleaned_count

    async def cleanup_all(self, idle_threshold_seconds: int = 3600) -> Dict[str, int]:
        """
        执行完整的清理操作（连接 + 信号量）

        Args:
            idle_threshold_seconds: 空闲阈值（秒）

        Returns:
            清理统计
        """
        connections_cleaned = await self.cleanup_closed_connections()
        semaphores_cleaned = await self.cleanup_idle_semaphores(idle_threshold_seconds)

        return {
            "connections_cleaned": connections_cleaned,
            "semaphores_cleaned": semaphores_cleaned,
        }


# 全局连接池实例
_mcp_connection_pool: Optional[MCPConnectionPool] = None


def get_mcp_connection_pool() -> MCPConnectionPool:
    """获取全局 MCP 连接池实例"""
    global _mcp_connection_pool
    if _mcp_connection_pool is None:
        _mcp_connection_pool = MCPConnectionPool()
    return _mcp_connection_pool
