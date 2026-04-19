"""
WebSocket 路由

提供实时任务进度更新的 WebSocket 端点。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

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
    token: Optional[str] = Query(None, description="JWT 认证令牌"),
    ticket: Optional[str] = Query(None, description="短期 ticket，优先于 token"),
) -> None:
    """
    任务进度更新 WebSocket 端点。支持 token 或 ticket 认证；优先 ticket，避免 JWT 出现在 URL。
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
            user = await verify_token_only(token)
            if user:
                user_id = str(user.id)
        except Exception as e:
            logger.warning(f"WebSocket 令牌验证失败: {e}")

    if not user_id:
        await websocket.close(code=1008, reason="认证失败")
        return

    # 获取管理器
    ws_manager = get_ws_manager()

    # 建立连接
    await ws_manager.connect(websocket, task_id, user_id)

    try:
        # 保持连接并接收消息
        while True:
            text_data = await websocket.receive_text()

            # 尝试解析 JSON 处理心跳
            try:
                import json

                data = json.loads(text_data)
                if isinstance(data, dict) and data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
            except Exception:
                pass

            # 这里可以处理客户端发送的消息
            logger.debug(f"收到 WebSocket 消息: task={task_id}, user={user_id}, data={text_data}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: task={task_id}, user={user_id}")

    except Exception as e:
        logger.error(f"WebSocket 错误: task={task_id}, user={user_id}, error={e}")

    finally:
        # 断开连接
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/batches/{batch_id}")
async def websocket_batch_updates(
    websocket: WebSocket,
    batch_id: str,
    token: Optional[str] = Query(None, description="JWT 认证令牌"),
    ticket: Optional[str] = Query(None, description="短期 ticket，优先于 token"),
) -> None:
    """
    批次进度更新 WebSocket 端点。支持 token 或 ticket 认证。

    订阅批次内所有任务的进度更新。
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
            logger.warning(f"WebSocket batch ticket 验证失败: {e}")

    if user_id is None and token:
        try:
            user = await verify_token_only(token)
            if user:
                user_id = str(user.id)
        except Exception as e:
            logger.warning(f"WebSocket batch 令牌验证失败: {e}")

    if not user_id:
        await websocket.close(code=1008, reason="认证失败")
        return

    ws_manager = get_ws_manager()

    # 为批次内每个子任务建立监听
    # 通过查询 batch 的子任务列表，订阅每个子任务
    try:
        from modules.trading_agents.manager.batch_manager import get_batch_manager

        batch_manager = get_batch_manager()
        batch_info = await batch_manager.get_batch_status(batch_id)

        if not batch_info:
            await websocket.close(code=1008, reason="批次不存在或无权限")
            return

        await ws_manager.connect(websocket, f"batch_{batch_id}", user_id)

        try:
            while True:
                text_data = await websocket.receive_text()
                try:
                    import json

                    data = json.loads(text_data)
                    if isinstance(data, dict) and data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        continue
                except Exception:
                    pass

                logger.debug(
                    f"收到 batch WebSocket 消息: batch={batch_id}, user={user_id}, data={text_data}"
                )

        except WebSocketDisconnect:
            logger.info(f"WebSocket batch 断开: batch={batch_id}, user={user_id}")

        except Exception as e:
            logger.error(f"WebSocket batch 错误: batch={batch_id}, user={user_id}, error={e}")

        finally:
            await ws_manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket batch 初始化失败: {e}")
        try:
            await websocket.close(code=1011, reason="内部错误")
        except Exception:
            pass
