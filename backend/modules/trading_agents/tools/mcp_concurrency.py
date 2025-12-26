"""
MCP 服务器并发控制

实现 MCP 服务器的连接池管理：
- stdio 模式：进程池管理（默认池大小 = 3）
- stdio 模式：进程空闲超时回收（5 分钟）
- HTTP/SSE 模式：使用 httpx 连接池（max_connections = 10）
- 连接池状态查询接口
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# 配置常量
# =============================================================================

STDIO_PROCESS_POOL_SIZE = 3  # stdio 模式进程池大小
STDIO_PROCESS_IDLE_TIMEOUT = 300  # stdio 模式进程空闲超时（秒）5 分钟
HTTP_CONNECTION_POOL_SIZE = 10  # HTTP/SSE 模式连接池大小


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class ConnectionPoolStats:
    """连接池统计信息"""
    server_name: str
    transport_mode: str  # stdio, sse, http
    total_connections: int
    active_connections: int
    idle_connections: int
    max_pool_size: int


@dataclass
class StdioProcessInfo:
    """stdio 进程信息"""
    server_name: str
    process: Any  # asyncio.subprocess.Process
    adapter: Any  # MCPAdapter 实例
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    is_active: bool = True


@dataclass
class HttpConnectionInfo:
    """HTTP 连接信息"""
    server_name: str
    client: Any  # httpx.AsyncClient
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    is_active: bool = True


# =============================================================================
# MCP 并发控制器
# =============================================================================

class MCPConcurrencyManager:
    """
    MCP 并发控制器

    管理 MCP 服务器的连接池，支持 stdio、SSE、HTTP 三种模式。
    """

    def __init__(self):
        """初始化 MCP 并发控制器"""
        # stdio 模式：进程池
        self._stdio_processes: Dict[str, List[StdioProcessInfo]] = {}
        # HTTP/SSE 模式：连接池
        self._http_connections: Dict[str, HttpConnectionInfo] = {}

        # 后台清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """启动并发控制器（启动后台清理任务）"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("MCP 并发控制器已启动")

    async def stop(self) -> None:
        """停止并发控制器"""
        if not self._running:
            return

        self._running = False

        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 清理所有连接
        await self._cleanup_all()

        logger.info("MCP 并发控制器已停止")

    # ========================================================================
    # stdio 模式：进程池管理
    # ========================================================================

    async def acquire_stdio_process(
        self,
        server_name: str,
        adapter_factory
    ) -> Any:
        """
        获取 stdio 进程（进程池模式）

        Args:
            server_name: MCP 服务器名称
            adapter_factory: 适配器工厂函数

        Returns:
            MCPAdapter 实例
        """
        if server_name not in self._stdio_processes:
            self._stdio_processes[server_name] = []
        processes = self._stdio_processes[server_name]

        # 查找空闲进程
        for proc_info in processes:
            if not proc_info.is_active:
                proc_info.is_active = True
                proc_info.last_used_at = time.time()
                logger.info(f"复用 stdio 进程: server={server_name}")
                return proc_info.adapter

        # 检查是否超过池大小
        if len(processes) >= STDIO_PROCESS_POOL_SIZE:
            # 等待空闲进程
            logger.warning(f"stdio 进程池已满: server={server_name}, 等待空闲进程")
            await asyncio.sleep(0.1)
            return await self.acquire_stdio_process(server_name, adapter_factory)

        # 创建新进程
        logger.info(f"创建新的 stdio 进程: server={server_name}, 当前数量={len(processes) + 1}")
        adapter = await adapter_factory()

        # 创建进程信息
        proc_info = StdioProcessInfo(
            server_name=server_name,
            process=getattr(adapter, "_process", None),
            adapter=adapter,
            is_active=True
        )
        processes.append(proc_info)

        return adapter

    async def release_stdio_process(self, server_name: str, adapter: Any) -> None:
        """
        释放 stdio 进程

        Args:
            server_name: MCP 服务器名称
            adapter: MCPAdapter 实例
        """
        processes = self._stdio_processes[server_name]

        for proc_info in processes:
            if proc_info.adapter == adapter:
                proc_info.is_active = False
                proc_info.last_used_at = time.time()
                logger.info(f"释放 stdio 进程: server={server_name}")
                return

        logger.warning(f"未找到要释放的 stdio 进程: server={server_name}")

    # ========================================================================
    # HTTP/SSE 模式：连接池管理
    # ========================================================================

    async def acquire_http_connection(
        self,
        server_name: str,
        client_factory
    ) -> Any:
        """
        获取 HTTP 连接（连接池模式）

        Args:
            server_name: MCP 服务器名称
            client_factory: 客户端工厂函数

        Returns:
            httpx.AsyncClient 实例
        """
        # 检查是否已有连接
        if server_name in self._http_connections:
            conn_info = self._http_connections[server_name]
            conn_info.last_used_at = time.time()
            logger.info(f"复用 HTTP 连接: server={server_name}")
            return conn_info.client

        # 创建新连接
        logger.info(f"创建新的 HTTP 连接: server={server_name}")
        client = await client_factory()

        conn_info = HttpConnectionInfo(
            server_name=server_name,
            client=client,
            is_active=True
        )
        self._http_connections[server_name] = conn_info

        return client

    async def release_http_connection(self, server_name: str) -> None:
        """
        释放 HTTP 连接（不实际关闭，保持连接池）

        Args:
            server_name: MCP 服务器名称
        """
        if server_name in self._http_connections:
            conn_info = self._http_connections[server_name]
            conn_info.is_active = False
            conn_info.last_used_at = time.time()
            logger.info(f"标记 HTTP 连接为空闲: server={server_name}")

    # ========================================================================
    # 连接池状态查询
    # ========================================================================

    async def get_pool_stats(self, server_name: str, transport_mode: str) -> ConnectionPoolStats:
        """
        获取连接池统计信息

        Args:
            server_name: MCP 服务器名称
            transport_mode: 传输模式（stdio, sse, http）

        Returns:
            连接池统计信息
        """
        if transport_mode == "stdio":
            processes = self._stdio_processes[server_name]
            active_count = sum(1 for p in processes if p.is_active)
            idle_count = len(processes) - active_count

            return ConnectionPoolStats(
                server_name=server_name,
                transport_mode=transport_mode,
                total_connections=len(processes),
                active_connections=active_count,
                idle_connections=idle_count,
                max_pool_size=STDIO_PROCESS_POOL_SIZE
            )
        else:
            # SSE 和 HTTP 模式
            conn_info = self._http_connections.get(server_name)
            if conn_info:
                return ConnectionPoolStats(
                    server_name=server_name,
                    transport_mode=transport_mode,
                    total_connections=1,
                    active_connections=1 if conn_info.is_active else 0,
                    idle_connections=0 if conn_info.is_active else 1,
                    max_pool_size=HTTP_CONNECTION_POOL_SIZE
                )
            else:
                return ConnectionPoolStats(
                    server_name=server_name,
                    transport_mode=transport_mode,
                    total_connections=0,
                    active_connections=0,
                    idle_connections=0,
                    max_pool_size=HTTP_CONNECTION_POOL_SIZE
                )

    async def get_all_pool_stats(self) -> List[ConnectionPoolStats]:
        """
        获取所有连接池统计信息

        Returns:
            所有连接池统计信息列表
        """
        stats = []

        # stdio 模式
        for server_name, processes in self._stdio_processes.items():
            stat = await self.get_pool_stats(server_name, "stdio")
            stats.append(stat)

        # HTTP/SSE 模式
        for server_name, conn_info in self._http_connections.items():
            transport_mode = "sse" if "sse" in server_name.lower() else "http"
            stat = await self.get_pool_stats(server_name, transport_mode)
            stats.append(stat)

        return stats

    # ========================================================================
    # 后台清理任务
    # ========================================================================

    async def _cleanup_loop(self) -> None:
        """后台清理循环"""
        while self._running:
            try:
                await self._cleanup_idle_stdio_processes()
                await asyncio.sleep(60)  # 每分钟清理一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务失败: {e}")

    async def _cleanup_idle_stdio_processes(self) -> None:
        """清理空闲的 stdio 进程"""
        now = time.time()

        for server_name, processes in list(self._stdio_processes.items()):
            # 保留活跃进程和最近使用的进程
            active_processes = []
            for proc_info in processes:
                idle_time = now - proc_info.last_used_at

                if proc_info.is_active or idle_time < STDIO_PROCESS_IDLE_TIMEOUT:
                    active_processes.append(proc_info)
                else:
                    # 终止空闲进程
                    try:
                        if proc_info.process and hasattr(proc_info.process, "terminate"):
                            proc_info.process.terminate()
                        logger.info(
                            f"终止空闲 stdio 进程: server={server_name}, "
                            f"空闲时间={idle_time:.0f}秒"
                        )
                    except Exception as e:
                        logger.error(f"终止进程失败: {e}")

            self._stdio_processes[server_name] = active_processes

    async def _cleanup_all(self) -> None:
        """清理所有连接"""
        # 清理 stdio 进程
        for server_name, processes in self._stdio_processes.items():
            for proc_info in processes:
                try:
                    if proc_info.process and hasattr(proc_info.process, "terminate"):
                        proc_info.process.terminate()
                except Exception as e:
                    logger.error(f"终止进程失败: {e}")
        self._stdio_processes.clear()

        # 清理 HTTP 连接
        for server_name, conn_info in self._http_connections.items():
            try:
                if hasattr(conn_info.client, "aclose"):
                    await conn_info.client.aclose()
            except Exception as e:
                logger.error(f"关闭连接失败: {e}")
        self._http_connections.clear()


# =============================================================================
# 全局 MCP 并发控制器实例
# =============================================================================

mcp_concurrency_manager = MCPConcurrencyManager()


def get_mcp_concurrency_manager() -> MCPConcurrencyManager:
    """获取全局 MCP 并发控制器实例"""
    return mcp_concurrency_manager
