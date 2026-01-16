"""
MCP 服务器健康检查后台任务

定期自动检测所有启用MCP服务器的状态。
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from core.db.mongodb import mongodb
from core.mcp.config.loader import (
    get_health_check_interval,
    get_health_check_max_concurrent_checks,
    get_health_check_timeout,
)
from core.mcp.schemas import MCPServerConfigResponse, MCPServerStatusEnum
from core.mcp.service.mcp_service import get_mcp_service

logger = logging.getLogger(__name__)


class MCPHealthChecker:
    """
    MCP 服务器健康检查器

    定期检测所有启用的MCP服务器状态，更新数据库中的状态信息。
    """

    # 健康检查配置（从配置文件加载）
    CHECK_INTERVAL = get_health_check_interval()
    CHECK_TIMEOUT = get_health_check_timeout()
    MAX_CONCURRENT_CHECKS = get_health_check_max_concurrent_checks()

    # 状态衰减配置
    STALE_THRESHOLD = 600             # 状态过期阈值（秒）- 10分钟
    FAILURE_THRESHOLD = 3             # 连续失败次数阈值

    def __init__(self):
        """初始化健康检查器"""
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # 追踪连续失败次数
        self._failure_counts: dict[str, int] = {}

        logger.info("MCP健康检查器已初始化")

    async def start(self):
        """启动健康检查后台任务"""
        if self._task is not None:
            logger.warning("健康检查任务已在运行")
            return

        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("MCP健康检查后台任务已启动")

    async def stop(self):
        """停止健康检查后台任务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("MCP健康检查后台任务已停止")

    async def _check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                await self._run_health_check()
                await asyncio.sleep(self.CHECK_INTERVAL)
            except asyncio.CancelledError:
                logger.info("健康检查任务被取消")
                break
            except Exception as e:
                logger.error(f"健康检查任务错误: {e}", exc_info=True)
                # 出错后等待一段时间再继续
                await asyncio.sleep(60)

    async def _run_health_check(self):
        """执行一次健康检查"""
        logger.info("开始MCP服务器健康检查")

        try:
            mcp_service = get_mcp_service()

            # 获取所有启用的服务器列表
            collection = mongodb.get_collection("mcp_servers")
            cursor = collection.find({"enabled": True})
            servers = []
            async for doc in cursor:
                servers.append(MCPServerConfigResponse.from_db(doc))

            logger.info(f"找到 {len(servers)} 个启用的MCP服务器")

            # 并发检查服务器状态
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_CHECKS)

            async def check_with_limit(server):
                async with semaphore:
                    return await self._check_single_server(server)

            results = await asyncio.gather(
                *[check_with_limit(server) for server in servers],
                return_exceptions=True
            )

            # 统计结果
            success_count = sum(1 for r in results if r is True)
            failure_count = sum(1 for r in results if r is False)
            error_count = sum(1 for r in results if isinstance(r, Exception))

            logger.info(
                f"健康检查完成: 成功={success_count}, "
                f"失败={failure_count}, 错误={error_count}"
            )

        except Exception as e:
            logger.error(f"健康检查执行失败: {e}", exc_info=True)

    async def _check_single_server(self, server) -> bool:
        """
        检查单个服务器状态

        Args:
            server: MCPServerConfigResponse实例

        Returns:
            True表示服务器可用，False表示不可用
        """
        server_id = server.id
        server_name = server.name

        try:
            # 检查状态是否需要更新
            now = datetime.utcnow()
            last_check = server.last_check_at

            # 如果状态较新，跳过检查
            if last_check:
                time_since_check = (now - last_check).total_seconds()
                if time_since_check < self.STALE_THRESHOLD:
                    logger.debug(
                        f"跳过检查（状态较新）: server={server_name}, "
                        f"last_check={time_since_check:.0f}秒前"
                    )
                    # 返回当前状态是否为可用
                    return server.status == MCPServerStatusEnum.AVAILABLE

            logger.info(f"检查服务器状态: server={server_name}")

            # 执行连接测试
            result = await self._test_connection(server)

            if result:
                # 连接成功，重置失败计数
                if server_id in self._failure_counts:
                    del self._failure_counts[server_id]
                logger.info(f"服务器状态正常: server={server_name}")
                return True
            else:
                # 连接失败，增加失败计数
                self._failure_counts[server_id] = self._failure_counts.get(server_id, 0) + 1
                logger.warning(
                    f"服务器状态异常: server={server_name}, "
                    f"fail_count={self._failure_counts[server_id]}"
                )
                return False

        except Exception as e:
            logger.error(f"检查服务器时出错: server={server_name}, error={e}")
            return False

    async def _test_connection(self, server) -> bool:
        """
        测试服务器连接

        Args:
            server: MCPServerConfigResponse实例

        Returns:
            连接是否成功
        """
        from core.mcp.adapter.adapter import build_auth_headers, get_mcp_tools, map_transport_mode

        try:
            # 构建连接配置
            headers = build_auth_headers(
                headers=server.headers,
                auth_type=server.auth_type.value,
                auth_token=server.auth_token,
            )

            transport = map_transport_mode(server.transport.value)

            # 根据传输模式构建配置
            if transport == "stdio":
                from core.mcp.adapter.adapter import build_stdio_connection
                connection_config = build_stdio_connection(
                    command=server.command,
                    args=server.args,
                    env=server.env,
                )
            elif transport == "sse":
                from core.mcp.adapter.adapter import build_sse_connection
                connection_config = build_sse_connection(
                    url=server.url,
                    headers=headers,
                )
            elif transport == "streamable_http":
                from core.mcp.adapter.adapter import build_streamable_http_connection
                connection_config = build_streamable_http_connection(
                    url=server.url,
                    headers=headers,
                )
            elif transport == "websocket":
                from core.mcp.adapter.adapter import build_websocket_connection
                connection_config = build_websocket_connection(
                    url=server.url,
                )
            else:
                logger.warning(f"不支持的传输模式: {transport}")
                await self._update_server_status(
                    server.id, MCPServerStatusEnum.UNAVAILABLE
                )
                return False

            # 测试连接
            tools = await get_mcp_tools(server.name, connection_config)
            tool_count = len(tools) if isinstance(tools, list) else 0

            await self._update_server_status(
                server.id, MCPServerStatusEnum.AVAILABLE
            )

            logger.debug(
                f"MCP服务器连接成功: server={server.name}, tools={tool_count}"
            )
            return True

        except asyncio.TimeoutError:
            logger.warning(f"连接超时: server={server.name}")
            await self._update_server_status(
                server.id, MCPServerStatusEnum.UNAVAILABLE
            )
            return False
        except Exception as e:
            logger.warning(f"连接失败: server={server.name}, error={e}")
            await self._update_server_status(
                server.id, MCPServerStatusEnum.UNAVAILABLE
            )
            return False

    async def _update_server_status(
        self,
        server_id: str,
        status: MCPServerStatusEnum
    ):
        """更新服务器状态"""
        try:
            from bson import ObjectId
            collection = mongodb.get_collection("mcp_servers")

            await collection.update_one(
                {"_id": ObjectId(server_id)},
                {
                    "$set": {
                        "status": status.value,
                        "last_check_at": datetime.utcnow(),
                    }
                }
            )
        except Exception as e:
            logger.error(f"更新服务器状态失败: server_id={server_id}, error={e}")

    async def check_server_now(self, server_id: str) -> bool:
        """
        立即检查指定服务器的状态

        Args:
            server_id: 服务器ID

        Returns:
            服务器是否可用
        """
        try:
            from bson import ObjectId
            collection = mongodb.get_collection("mcp_servers")

            doc = await collection.find_one({"_id": ObjectId(server_id)})

            if not doc:
                logger.error(f"服务器不存在: server_id={server_id}")
                return False

            server = MCPServerConfigResponse.from_db(doc)
            return await self._check_single_server(server)

        except Exception as e:
            logger.error(f"立即检查服务器失败: server_id={server_id}, error={e}")
            return False


# =============================================================================
# 全局健康检查器实例
# =============================================================================

_mcp_health_checker: Optional[MCPHealthChecker] = None


def get_mcp_health_checker() -> MCPHealthChecker:
    """获取全局MCP健康检查器实例"""
    global _mcp_health_checker
    if _mcp_health_checker is None:
        _mcp_health_checker = MCPHealthChecker()
    return _mcp_health_checker
