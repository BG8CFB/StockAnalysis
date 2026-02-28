"""
MCP 请求队列管理

提供超出并发限制时的请求排队功能。
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class MCPRequestQueue:
    """
    MCP 请求队列

    当并发限制达到上限时，新的请求会被放入队列等待。
    """

    def __init__(self, maxsize: int = 200):
        """
        初始化队列

        Args:
            maxsize: 队列最大容量
        """
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._maxsize = maxsize
        logger.info(f"[MCPRequestQueue] 初始化队列，最大容量: {maxsize}")

    async def put(self, request: "MCPRequest") -> None:
        """
        放入请求

        Args:
            request: MCP 请求对象

        Raises:
            asyncio.QueueFull: 队列已满时抛出
        """
        await self._queue.put(request)
        logger.debug(f"[MCPRequestQueue] 请求入队: {request.request_id}")

    async def get(self) -> "MCPRequest":
        """
        获取请求（阻塞）

        Returns:
            MCP 请求对象
        """
        request = await self._queue.get()
        logger.debug(f"[MCPRequestQueue] 请求出队: {request.request_id}")
        return request

    def qsize(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()

    def empty(self) -> bool:
        """队列是否为空"""
        return self._queue.empty()

    def full(self) -> bool:
        """队列是否已满"""
        return self._queue.full()

    async def clear(self) -> None:
        """清空队列"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        logger.info("[MCPRequestQueue] 队列已清空")


class MCPRequest:
    """
    MCP 请求对象

    封装一个 MCP 连接请求的所有信息。
    """

    def __init__(
        self,
        server_id: str,
        task_id: str,
        user_id: str,
        callback: Callable,
        timeout: Optional[float] = None,
    ):
        """
        初始化请求

        Args:
            server_id: MCP 服务器 ID
            task_id: 任务 ID
            user_id: 用户 ID
            callback: 回调函数（用于在请求处理完成后调用）
            timeout: 超时时间（秒）
        """
        self.request_id = f"{server_id}:{task_id}:{user_id}"
        self.server_id = server_id
        self.task_id = task_id
        self.user_id = user_id
        self.callback = callback
        self.timeout = timeout
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    async def wait(self, timeout: Optional[float] = None) -> Any:
        """
        等待请求完成

        Args:
            timeout: 超时时间（秒），默认使用请求的超时时间

        Returns:
            回调函数的结果

        Raises:
            asyncio.TimeoutError: 超时时抛出
        """
        timeout = timeout or self.timeout
        # 这里需要实现实际的等待逻辑
        # 可以使用 asyncio.Event 或 Future
        raise NotImplementedError("等待逻辑需要在连接池中实现")

    @property
    def pending_time(self) -> float:
        """获取等待时长（秒）"""
        if self.started_at:
            return (self.started_at - self.created_at).total_seconds()
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    @property
    def processing_time(self) -> Optional[float]:
        """获取处理时长（秒）"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def total_time(self) -> float:
        """获取总时长（秒）"""
        end_time = self.completed_at or datetime.now(timezone.utc)
        return (end_time - self.created_at).total_seconds()

    def __repr__(self) -> str:
        return (
            f"MCPRequest(id={self.request_id}, "
            f"server={self.server_id}, "
            f"task={self.task_id}, "
            f"user={self.user_id}, "
            f"pending={self.pending_time:.2f}s)"
        )
