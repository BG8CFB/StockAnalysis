"""
TradingAgents API 路由模块

API 层 - 对外接口（HTTP + WebSocket）
- tasks.py: 任务管理 API
- reports.py: 健康检查路由
- websocket.py: WebSocket 路由（统一使用 /ws/tasks/{task_id}）
"""

from fastapi import APIRouter

from .reports import health_router
from .tasks import agents_router, config_router
from .tasks import router as tasks_router
from .websocket import router as websocket_tasks_router

# 创建聚合路由器
router = APIRouter()

# 注册子路由（具体路径必须在通配路径 /{task_id} 之前注册，避免被拦截）
router.include_router(agents_router)
router.include_router(config_router)
router.include_router(tasks_router)
router.include_router(health_router)
router.include_router(websocket_tasks_router)

__all__ = ["router"]
