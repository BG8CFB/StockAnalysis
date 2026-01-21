"""
WebSocket 路由

提供实时任务进度更新的 WebSocket 端点。
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel

from core.auth.dependencies import verify_token_only
from modules.trading_agents.api.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

router = APIRouter()

# 获取全局 WebSocket 管理器实例
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """获取全局 WebSocket 管理器实例"""
    global _ws_manager
    if _ws_manager is None:
        from modules.trading_agents.api.websocket_manager import websocket_manager
        _ws_manager = websocket_manager
    return _ws_manager


@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_updates(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(..., description="JWT 认证令牌")
):
    """
    任务进度更新 WebSocket 端点

    Args:
        websocket: WebSocket 连接
        task_id: 任务 ID
        token: JWT 认证令牌
    """
    # 验证用户认证
    try:
        user = await verify_token_only(token)
    except Exception as e:
        logger.warning(f"WebSocket 认证失败: {e}")
        await websocket.close(code=1008, reason="认证失败")
        return

    if not user:
        await websocket.close(code=1008, reason="认证失败")
        return

    user_id = user.id

    # 获取管理器
    ws_manager = get_ws_manager()

    # 建立连接
    await ws_manager.connect(websocket, task_id, user_id)

    try:
        # 保持连接并接收消息
        while True:
            data = await websocket.receive_text()
            # 这里可以处理客户端发送的消息
            logger.debug(f"收到 WebSocket 消息: task={task_id}, user={user_id}, data={data}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: task={task_id}, user={user_id}")

    except Exception as e:
        logger.error(f"WebSocket 错误: task={task_id}, user={user_id}, error={e}")

    finally:
        # 断开连接
        await ws_manager.disconnect(websocket)
