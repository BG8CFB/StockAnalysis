"""
MCP 长连接对象

实现任务级长连接管理，包含状态机和生命周期管理。
"""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from modules.mcp.config.loader import (
    get_connection_complete_timeout,
    get_connection_failed_timeout,
)

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """连接状态枚举"""
    IDLE = "idle"                     # 空闲（未使用）
    CONNECTING = "connecting"         # 连接中
    ACTIVE = "active"                 # 活跃（长连接保持）
    CLOSING = "closing"               # 关闭中（任务完成后 10 秒）
    FAILED_CLEANUP = "failed_cleanup" # 失败清理中（30 秒）
    CLOSED = "closed"                 # 已关闭


class MCPConnection:
    """
    任务级长连接对象

    生命周期：
    - 任务开始时创建
    - 任务执行中保持 ACTIVE 状态
    - 任务完成后进入 CLOSING 状态，10 秒后销毁
    - 任务失败后进入 FAILED_CLEANUP 状态，30 秒后销毁
    """

    def __init__(
        self,
        server_id: str,
        server_name: str,
        task_id: str,
        user_id: str,
        connection_config: Dict[str, Any],
    ):
        """
        初始化连接对象

        Args:
            server_id: MCP 服务器 ID
            server_name: MCP 服务器名称
            task_id: 任务 ID
            user_id: 用户 ID
            connection_config: MCP 连接配置（传递给 MultiServerMCPClient）
        """
        self.connection_id = str(uuid.uuid4())
        self.server_id = server_id
        self.server_name = server_name
        self.task_id = task_id
        self.user_id = user_id
        self.state = ConnectionState.IDLE
        self._connection_config = connection_config

        # 客户端（初始化时创建）
        self._client: Optional[MultiServerMCPClient] = None
        self._tools: List[BaseTool] = []

        # 时间戳
        self.created_at = datetime.utcnow()
        self.last_used_at: Optional[datetime] = None

        # 清理定时器
        self._cleanup_timer: Optional[asyncio.Task] = None
        self._cleanup_lock = asyncio.Lock()

        logger.info(
            f"[MCPConnection] 创建连接对象: connection_id={self.connection_id}, "
            f"server_id={server_id}, task_id={task_id}, user_id={user_id}"
        )

    async def initialize(self) -> List[BaseTool]:
        """
        初始化连接，返回工具列表（官方标准实现）

        Returns:
            LangChain 工具列表

        Raises:
            MCPConnectionError: 连接失败时抛出
        """
        if self.state != ConnectionState.IDLE:
            raise RuntimeError(f"连接状态不正确: {self.state}")

        self.state = ConnectionState.CONNECTING
        logger.info(f"[MCPConnection] 开始连接: {self.connection_id}")

        try:
            # 创建 MCP 客户端
            self._client = MultiServerMCPClient(
                {self.server_name: self._connection_config}
            )

            # 使用官方 get_tools() 方法加载工具
            # 官方实现会自动管理 session 生命周期
            # 工具对象可以在后续调用时自动创建 session
            self._tools = await self._client.get_tools(
                server_name=self.server_name
            )

            self.state = ConnectionState.ACTIVE
            self.last_used_at = datetime.utcnow()

            # 为工具添加 server_id 属性（用于过滤）
            for tool in self._tools:
                tool.mcp_server_id = self.server_id
                tool.mcp_server_name = self.server_name
                tool.mcp_connection_id = self.connection_id

            logger.info(
                f"[MCPConnection] 连接成功: {self.connection_id}, "
                f"获取到 {len(self._tools)} 个工具"
            )

            return self._tools

        except Exception as e:
            self.state = ConnectionState.FAILED_CLEANUP
            logger.error(
                f"[MCPConnection] 连接失败: {self.connection_id}, error={e}",
                exc_info=True
            )
            # 启动失败清理定时器（从配置加载超时时间）
            self._schedule_cleanup(get_connection_failed_timeout())
            raise

    async def mark_complete(self) -> None:
        """
        标记任务完成，启动延迟倒计时后销毁
        """
        async with self._cleanup_lock:
            if self.state != ConnectionState.ACTIVE:
                logger.warning(
                    f"[MCPConnection] 非活动状态下调用 mark_complete: {self.state}"
                )
                return

            timeout = get_connection_complete_timeout()
            logger.info(f"[MCPConnection] 任务完成，启动 {timeout} 秒清理倒计时: {self.connection_id}")
            self.state = ConnectionState.CLOSING
            self._schedule_cleanup(timeout)

    async def mark_failed(self) -> None:
        """
        标记任务失败，启动延迟倒计时后销毁
        """
        async with self._cleanup_lock:
            if self.state == ConnectionState.CLOSED:
                return

            timeout = get_connection_failed_timeout()
            logger.info(f"[MCPConnection] 任务失败，启动 {timeout} 秒清理倒计时: {self.connection_id}")
            self.state = ConnectionState.FAILED_CLEANUP
            self._schedule_cleanup(timeout)

    def _schedule_cleanup(self, delay_seconds: int) -> None:
        """安排清理定时器"""
        if self._cleanup_timer and not self._cleanup_timer.done():
            self._cleanup_timer.cancel()

        self._cleanup_timer = asyncio.create_task(self._cleanup_after_delay(delay_seconds))

    async def _cleanup_after_delay(self, delay_seconds: int) -> None:
        """延迟后清理"""
        try:
            await asyncio.sleep(delay_seconds)
            await self.close()
        except asyncio.CancelledError:
            logger.debug(f"[MCPConnection] 清理任务被取消: {self.connection_id}")
        except Exception as e:
            logger.error(f"[MCPConnection] 清理过程中出错: {self.connection_id}, error={e}")

    async def close(self) -> None:
        """
        优雅关闭连接
        """
        async with self._cleanup_lock:
            if self.state == ConnectionState.CLOSED:
                return

            logger.info(f"[MCPConnection] 关闭连接: {self.connection_id}")
            self.state = ConnectionState.CLOSED

            # 取消清理定时器
            if self._cleanup_timer and not self._cleanup_timer.done():
                self._cleanup_timer.cancel()

            # 关闭客户端
            if self._client:
                try:
                    # 注意：具体关闭方法取决于 langchain-mcp-adapters 实现
                    if hasattr(self._client, 'close'):
                        await self._client.close()
                    elif hasattr(self._client, 'aclose'):
                        await self._client.aclose()
                except Exception as e:
                    logger.error(
                        f"[MCPConnection] 关闭客户端时出错: {self.connection_id}, error={e}"
                    )

            self._client = None
            self._tools = []

            logger.info(f"[MCPConnection] 连接已关闭: {self.connection_id}")

    async def destroy(self) -> None:
        """
        强制销毁连接（立即关闭）
        """
        logger.info(f"[MCPConnection] 强制销毁连接: {self.connection_id}")
        await self.close()

    @property
    def tools(self) -> List[BaseTool]:
        """获取工具列表"""
        return self._tools

    @property
    def is_active(self) -> bool:
        """是否处于活跃状态"""
        return self.state == ConnectionState.ACTIVE

    @property
    def is_usable(self) -> bool:
        """是否可用（可用于工具调用）"""
        return self.state in (ConnectionState.ACTIVE, ConnectionState.CLOSING, ConnectionState.FAILED_CLEANUP)

    def __repr__(self) -> str:
        return (
            f"MCPConnection(id={self.connection_id}, "
            f"server={self.server_name}, "
            f"state={self.state.value}, "
            f"task={self.task_id}, "
            f"user={self.user_id})"
        )
