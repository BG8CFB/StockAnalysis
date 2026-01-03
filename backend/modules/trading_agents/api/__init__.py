"""
TradingAgents API 路由聚合模块

拆分后的 API 路由模块，按功能组织：
- tasks.py: 任务管理相关路由
- reports.py: 报告管理相关路由
- config.py: 智能体配置相关路由
- settings.py: 设置相关路由
- websocket.py: WebSocket 路由
- health.py: 健康检查路由
"""

from fastapi import APIRouter

from .tasks import router as tasks_router
from .reports import router as reports_router
from .config import router as config_router
from .settings import router as settings_router
from .websocket import router as websocket_router
from .health import router as health_router

# 创建聚合路由器
router = APIRouter()

# 注册子路由
router.include_router(tasks_router)
router.include_router(reports_router)
router.include_router(config_router)
router.include_router(settings_router)
router.include_router(websocket_router)
router.include_router(health_router)

__all__ = ["router"]
