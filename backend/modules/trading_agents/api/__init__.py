"""
TradingAgents API 路由聚合模块

合并后的 API 路由模块：
- tasks.py: 任务管理 + 智能体配置路由
- reports.py: WebSocket + 健康检查路由（报告管理和设置路由已删除）
"""

from fastapi import APIRouter

from .tasks import router as tasks_router, config_router
from .reports import websocket_router, health_router

# 创建聚合路由器
router = APIRouter()

# 注册子路由
router.include_router(tasks_router)
router.include_router(config_router)
router.include_router(websocket_router)
router.include_router(health_router)

__all__ = ["router"]
