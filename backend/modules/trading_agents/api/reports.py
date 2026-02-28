"""
TradingAgents API 路由聚合

合并后的 API 路由模块：
- WebSocket 路由
- 健康检查路由

注意：
- 报告管理路由已删除，前端直接使用任务对象中的报告
- 设置路由已删除，使用统一设置系统 /settings/trading-agents
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from core.auth.security import jwt_manager
from modules.trading_agents.api.websocket_manager import get_ws_manager, WebSocketManager

logger = logging.getLogger(__name__)


# =============================================================================
# WebSocket API 路由（从 websocket.py 合并）
# =============================================================================

# 创建 WebSocket 路由器
websocket_router = APIRouter(prefix="/trading-agents", tags=["TradingAgents - WebSocket"])


@websocket_router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    token: Optional[str] = Query(None),
    ticket: Optional[str] = Query(None),
):
    """
    WebSocket 连接端点。

    支持 token 或 ticket 认证；优先使用 ticket，避免 JWT 出现在 URL。
    """
    user_id = None

    if ticket:
        try:
            from core.db.redis import UserRedisKey, get_redis
            redis = await get_redis()
            key = UserRedisKey.stream_ticket(ticket)
            raw = await redis.get(key)
            await redis.delete(key)
            if raw:
                user_id = raw.strip()
        except Exception as e:
            logger.warning(f"WebSocket ticket 验证失败: {e}")

    if user_id is None and token:
        try:
            payload = jwt_manager.verify_token(token, "access")
            if payload:
                user_id = payload.get("sub")
        except Exception as e:
            logger.warning(f"WebSocket 令牌验证失败: {e}")

    if not user_id:
        await websocket.close(code=4001, reason="无效的访问令牌或 ticket")
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


# =============================================================================
# 健康检查 API 路由（从 health.py 合并）
# =============================================================================

# 创建健康检查路由器
health_router = APIRouter(prefix="/trading-agents", tags=["TradingAgents - 健康检查"])


@health_router.get("/health", response_model=dict)
async def health_check():
    """
    健康检查端点

    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "module": "TradingAgents",
    }
