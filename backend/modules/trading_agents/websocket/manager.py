"""
WebSocket 管理器

管理 WebSocket 连接，实现按需连接和事件广播。
"""

import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Set, Any, Optional, List

from fastapi import WebSocket, WebSocketDisconnect

from modules.trading_agents.websocket.events import TaskEvent, EventType

logger = logging.getLogger(__name__)


# =============================================================================
# WebSocket 连接管理器
# =============================================================================

class WebSocketManager:
    """
    WebSocket 连接管理器

    实现：
    - 按需连接（用户打开详情页面时连接）
    - 单用户最多 5 个连接限制
    - 事件广播（无连接时丢弃事件，不缓存）
    """

    # 单用户最大连接数
    MAX_CONNECTIONS_PER_USER = 5

    def __init__(self):
        # {task_id: {user_id: Set[WebSocket]}}
        self._connections: Dict[str, Dict[str, Set[WebSocket]]] = defaultdict(lambda: defaultdict(set))

        # {websocket: (task_id, user_id)} 反向映射
        self._connection_info: Dict[WebSocket, tuple[str, str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        task_id: str,
        user_id: str
    ) -> None:
        """
        建立连接

        Args:
            websocket: WebSocket 连接对象
            task_id: 任务 ID
            user_id: 用户 ID
        """
        # 检查用户连接数
        user_connections = self._get_user_connection_count(user_id)

        if user_connections >= self.MAX_CONNECTIONS_PER_USER:
            # 超过限制，断开最早的连接
            await self._disconnect_oldest(user_id)

        # 接受连接
        await websocket.accept()

        # 添加连接
        self._connections[task_id][user_id].add(websocket)
        self._connection_info[websocket] = (task_id, user_id)

        logger.info(
            f"WebSocket 连接建立: task={task_id}, user={user_id}, "
            f"当前连接数={user_connections + 1}"
        )

        # 发送连接成功确认
        await self._send_to_websocket(
            websocket,
            {
                "event_type": "connection_established",
                "task_id": task_id,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

    async def disconnect(
        self,
        websocket: WebSocket,
        code: int = 1000,
        reason: str = ""
    ) -> None:
        """
        断开连接

        Args:
            websocket: WebSocket 连接对象
            code: 关闭代码
            reason: 关闭原因
        """
        if websocket not in self._connection_info:
            return

        task_id, user_id = self._connection_info[websocket]

        # 从连接集合中移除
        if task_id in self._connections:
            if user_id in self._connections[task_id]:
                self._connections[task_id][user_id].discard(websocket)

                # 清理空集合
                if not self._connections[task_id][user_id]:
                    del self._connections[task_id][user_id]

            # 清理空任务
            if not self._connections[task_id]:
                del self._connections[task_id]

        # 移除反向映射
        del self._connection_info[websocket]

        # 关闭连接
        try:
            await websocket.close(code=code, reason=reason)
        except Exception:
            pass  # 连接可能已关闭

        logger.debug(f"WebSocket 连接断开: task={task_id}, user={user_id}")

    async def broadcast_event(
        self,
        task_id: str,
        event: TaskEvent
    ) -> None:
        """
        广播事件到订阅该任务的连接

        Args:
            task_id: 任务 ID
            event: 事件对象

        注意：
            如果没有连接，则丢弃事件（不缓存）
        """
        if task_id not in self._connections:
            # 没有连接，丢弃事件
            logger.debug(f"没有连接，丢弃事件: task={task_id}, event={event.event_type}")
            return

        # 准备事件数据
        event_data = event.to_dict()

        # 向所有连接的客户端推送事件
        for user_id, websockets in self._connections[task_id].items():
            for ws in list(websockets):  # 使用 list 复制以避免迭代时修改
                try:
                    await self._send_to_websocket(ws, event_data)
                except Exception as e:
                    logger.warning(f"WebSocket 发送失败: {e}")
                    # 自动断开无效连接
                    await self.disconnect(ws)

    async def send_to_user(
        self,
        user_id: str,
        event: TaskEvent
    ) -> None:
        """
        发送事件到指定用户的所有连接

        Args:
            user_id: 用户 ID
            event: 事件对象
        """
        event_data = event.to_dict()

        # 遍历所有任务，找到该用户的连接
        for task_id, task_connections in self._connections.items():
            if user_id in task_connections:
                for ws in list(task_connections[user_id]):
                    try:
                        await self._send_to_websocket(ws, event_data)
                    except Exception as e:
                        logger.warning(f"WebSocket 发送失败: {e}")
                        await self.disconnect(ws)

    async def broadcast_to_all(
        self,
        event: TaskEvent
    ) -> None:
        """
        广播事件到所有连接

        Args:
            event: 事件对象
        """
        event_data = event.to_dict()

        # 遍历所有连接
        for websocket in list(self._connection_info.keys()):
            try:
                await self._send_to_websocket(websocket, event_data)
            except Exception as e:
                logger.warning(f"WebSocket 发送失败: {e}")
                await self.disconnect(websocket)

    async def _send_to_websocket(
        self,
        websocket: WebSocket,
        data: Dict[str, Any]
    ) -> None:
        """
        发送数据到 WebSocket

        Args:
            websocket: WebSocket 连接对象
            data: 要发送的数据
        """
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.warning(f"发送 WebSocket 消息失败: {e}")
            raise

    def _get_user_connection_count(self, user_id: str) -> int:
        """
        获取用户当前连接数

        Args:
            user_id: 用户 ID

        Returns:
            连接数
        """
        count = 0
        for task_connections in self._connections.values():
            count += len(task_connections.get(user_id, set()))
        return count

    async def _disconnect_oldest(self, user_id: str) -> None:
        """
        断开用户最早的连接

        Args:
            user_id: 用户 ID
        """
        # 找到最早的连接并断开
        for task_id, task_connections in self._connections.items():
            if user_id in task_connections:
                for ws in list(task_connections[user_id]):
                    await self.disconnect(ws, code=1000, reason="超过最大连接数限制")
                    logger.info(f"断开旧连接: user={user_id}, task={task_id}")
                    return

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息

        Returns:
            统计信息字典
        """
        total_connections = len(self._connection_info)

        # 按任务统计
        task_stats = {}
        for task_id, task_connections in self._connections.items():
            task_stats[task_id] = {
                "total_connections": sum(len(conns) for conns in task_connections.values()),
                "users": list(task_connections.keys()),
            }

        return {
            "total_connections": total_connections,
            "total_tasks": len(self._connections),
            "task_stats": task_stats,
        }

    async def close_all(self) -> None:
        """关闭所有连接"""
        for websocket in list(self._connection_info.keys()):
            try:
                await self.disconnect(websocket, code=1001, reason="服务器关闭")
            except Exception:
                pass

        logger.info("已关闭所有 WebSocket 连接")


# =============================================================================
# 全局 WebSocket 管理器实例
# =============================================================================

websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """获取全局 WebSocket 管理器实例"""
    return websocket_manager


# =============================================================================
# FastAPI 依赖项
# =============================================================================

async def get_ws_manager() -> WebSocketManager:
    """
    FastAPI 依赖项：获取 WebSocket 管理器

    Returns:
        WebSocket 管理器实例
    """
    return websocket_manager
