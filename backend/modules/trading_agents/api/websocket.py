"""
WebSocket API 路由
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse

from core.auth.security import jwt_manager

from modules.trading_agents.websocket import get_ws_manager, WebSocketManager

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/trading-agents", tags=["TradingAgents - WebSocket"])


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(...),
):
    """
    WebSocket 连接端点

    用于实时接收任务进度和事件。

    Args:
        websocket: WebSocket 连接
        task_id: 任务 ID
        token: 访问令牌（通过查询参数传递）
    """
    # 验证 token 获取用户 ID
    try:
        payload = jwt_manager.verify_token(token, "access")
        if not payload:
            raise ValueError("Invalid token")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing user_id in token")
    except Exception as e:
        logger.warning(f"WebSocket 令牌验证失败: {e}")
        await websocket.close(code=4001, reason="无效的访问令牌")
        return

    ws_manager: WebSocketManager = get_ws_manager()

    try:
        await ws_manager.connect(websocket, task_id, user_id)

        # 保持连接，接收客户端消息（如心跳）
        while True:
            data = await websocket.receive_json()
            # 处理客户端消息（如心跳保活）
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: task_id={task_id}, user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: task_id={task_id}, error={e}")
    finally:
        await ws_manager.disconnect(websocket)
