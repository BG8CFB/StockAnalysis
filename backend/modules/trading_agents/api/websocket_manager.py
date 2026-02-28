"""
WebSocket 推送管理器

管理 WebSocket 连接，实现按需连接和事件广播。
支持：
- 按需连接（用户打开详情页面时连接）
- 单用户最多 5 个连接限制
- 事件广播（无连接时丢弃事件，不缓存）
- 任务级权限验证
- 连接时间跟踪与定期清理陈旧连接
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Set, Any, Optional, List, Callable

from fastapi import WebSocket, WebSocketDisconnect

from modules.trading_agents.workflow.events import TaskEvent, EventType

logger = logging.getLogger(__name__)

# 配置常量（可通过环境变量覆盖）
CLEANUP_INTERVAL = 300  # 清理间隔（秒）：5 分钟
CONNECTION_TIMEOUT = 1800  # 连接超时（秒）：30 分钟


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
    - 任务级权限验证
    - 连接时间跟踪与定期清理陈旧连接
    """

    # 单用户最大连接数
    MAX_CONNECTIONS_PER_USER = 5

    def __init__(self):
        # {task_id: {user_id: Set[WebSocket]}}
        self._connections: Dict[str, Dict[str, Set[WebSocket]]] = defaultdict(lambda: defaultdict(set))

        # {websocket: (task_id, user_id, created_at, last_active_at)} 反向映射
        # 添加连接时间和最后活跃时间，用于超时清理
        self._connection_info: Dict[WebSocket, tuple[str, str, datetime, datetime]] = {}

        # 任务权限验证回调函数
        self._task_auth_callback: Optional[Callable[[str, str], bool]] = None

        # 清理任务标志
        self._cleanup_task: Optional[asyncio.Task] = None

    def _start_cleanup_task(self) -> None:
        """启动定期清理陈旧连接的后台任务（必须在事件循环内调用）"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_stale_connections())
            logger.info("[WebSocketManager] 已启动陈旧连接清理任务")

    async def initialize(self) -> None:
        """初始化 WebSocket 管理器（在应用启动时调用，确保事件循环已就绪）"""
        self._start_cleanup_task()

    async def _cleanup_stale_connections(self) -> None:
        """
        定期清理陈旧连接的后台任务

        检查所有连接，将超过超时阈值的连接断开。
        """
        try:
            while True:
                # 等待清理间隔
                await asyncio.sleep(CLEANUP_INTERVAL)

                now = datetime.now()
                stale_connections: List[WebSocket] = []

                # 找出超时的连接
                for websocket, (_, _, created_at, last_active_at) in self._connection_info.items():
                    # 如果最后活跃时间超过阈值，或者创建时间超过阈值（从未活跃）
                    timeout_threshold = last_active_at + timedelta(seconds=CONNECTION_TIMEOUT)
                    if now > timeout_threshold:
                        stale_connections.append(websocket)

                # 断开陈旧连接
                for websocket in stale_connections:
                    try:
                        task_id, user_id, _, _ = self._connection_info.get(websocket, (None, None, None, None))
                        await self.disconnect(websocket, code=4000, reason="Connection timeout")
                        logger.info(
                            f"[WebSocketManager] 清理超时连接: task={task_id}, user={user_id}"
                        )
                    except Exception as e:
                        logger.warning(f"[WebSocketManager] 清理连接时出错: {e}")

                if stale_connections:
                    logger.info(
                        f"[WebSocketManager] 本次清理超时连接 {len(stale_connections)} 个"
                    )

        except asyncio.CancelledError:
            logger.info("[WebSocketManager] 陈旧连接清理任务已取消")
            raise
        except Exception as e:
            logger.error(f"[WebSocketManager] 陈旧连接清理任务出错: {e}")

    def set_task_auth_callback(self, callback: Callable[[str, str], bool]) -> None:
        """
        设置任务权限验证回调函数

        Args:
            callback: 回调函数，接收 task_id 和 user_id，返回是否有权限
        """
        self._task_auth_callback = callback

    async def _verify_task_access(self, task_id: str, user_id: str) -> bool:
        """
        验证用户是否有权访问任务

        Args:
            task_id: 任务 ID
            user_id: 用户 ID

        Returns:
            是否有访问权限
        """
        # 如果有自定义验证回调，使用回调
        if self._task_auth_callback:
            return self._task_auth_callback(task_id, user_id)

        # 默认验证：从数据库查询任务所属用户
        try:
            from core.db.mongodb import mongodb
            from bson import ObjectId

            task = await mongodb.database.analysis_tasks.find_one(
                {"_id": ObjectId(task_id)}
            )

            if not task:
                logger.warning(f"任务不存在: task_id={task_id}")
                return False

            # 验证任务是否属于该用户
            task_user_id = task.get("user_id")
            # 统一转换为字符串比较，避免类型不匹配（如 str vs PyObjectId）
            task_user_id_str = str(task_user_id) if task_user_id else ""
            user_id_str = str(user_id) if user_id else ""
            if task_user_id_str != user_id_str:
                logger.warning(
                    f"用户无权访问任务: task_id={task_id}, "
                    f"task_user={task_user_id}, request_user={user_id}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"验证任务权限时发生错误: task_id={task_id}, error={e}")
            return False

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

        Raises:
            WebSocketDisconnect: 权限验证失败时关闭连接
        """
        # 首先验证用户是否有权访问该任务
        has_access = await self._verify_task_access(task_id, user_id)
        if not has_access:
            logger.warning(
                f"WebSocket 连接被拒绝: 用户无权访问任务, task={task_id}, user={user_id}"
            )
            await websocket.close(code=1008, reason="无权访问该任务")
            return

        # 检查用户连接数
        user_connections = self._get_user_connection_count(user_id)

        if user_connections >= self.MAX_CONNECTIONS_PER_USER:
            # 超过限制，断开最早的连接
            await self._disconnect_oldest(user_id)

        # 接受连接
        await websocket.accept()

        now = datetime.now()

        # 添加连接
        self._connections[task_id][user_id].add(websocket)
        # 记录连接时间和最后活跃时间
        self._connection_info[websocket] = (task_id, user_id, now, now)

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
                "timestamp": asyncio.get_running_loop().time(),
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

        task_id, user_id, _, _ = self._connection_info[websocket]

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
        # 复制外层字典防止 disconnect() 在迭代中修改字典（字典大小变化导致 RuntimeError）
        task_conns = dict(self._connections.get(task_id, {}))
        for user_id, websockets in task_conns.items():
            for ws in list(websockets):
                try:
                    # 更新最后活跃时间
                    if ws in self._connection_info:
                        task_id_, user_id_, created_at, _ = self._connection_info[ws]
                        self._connection_info[ws] = (task_id_, user_id_, created_at, datetime.now())

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
                        # 更新最后活跃时间
                        if ws in self._connection_info:
                            task_id_, user_id_, created_at, _ = self._connection_info[ws]
                            self._connection_info[ws] = (task_id_, user_id_, created_at, datetime.now())

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
                # 更新最后活跃时间
                if websocket in self._connection_info:
                    task_id_, user_id_, created_at, _ = self._connection_info[websocket]
                    self._connection_info[websocket] = (task_id_, user_id_, created_at, datetime.now())

                await self._send_to_websocket(websocket, event_data)
            except Exception as e:
                logger.warning(f"WebSocket 发送失败: {e}")
                await self.disconnect(websocket)

    async def send_event(
        self,
        task_id: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        发送事件到指定任务的所有连接

        Args:
            task_id: 任务 ID
            event_data: 事件数据字典
        """
        if task_id not in self._connections:
            # 没有连接，丢弃事件
            return

        for user_id, connections in self._connections[task_id].items():
            for ws in list(connections):
                try:
                    # 更新最后活跃时间
                    if ws in self._connection_info:
                        task_id_, user_id_, created_at, _ = self._connection_info[ws]
                        self._connection_info[ws] = (task_id_, user_id_, created_at, datetime.now())

                    await self._send_to_websocket(ws, event_data)
                except Exception as e:
                    logger.warning(f"WebSocket 发送失败: {e}")
                    await self.disconnect(ws)

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

        # 统计陈旧连接
        stale_count = 0
        now = datetime.now()
        for _, (_, _, _, last_active_at) in self._connection_info.items():
            if now - last_active_at > timedelta(seconds=CONNECTION_TIMEOUT):
                stale_count += 1

        return {
            "total_connections": total_connections,
            "total_tasks": len(self._connections),
            "task_stats": task_stats,
            "stale_connections": stale_count,
            "cleanup_interval": CLEANUP_INTERVAL,
            "connection_timeout": CONNECTION_TIMEOUT,
        }

    async def close_all(self) -> None:
        """关闭所有连接"""
        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

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
