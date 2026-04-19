"""
TradingAgents API 路由聚合

合并后的 API 路由模块：
- 健康检查路由

注意：
- WebSocket 路由已移至 websocket.py，统一使用 /ws/tasks/{task_id}
- 报告管理路由已删除，前端直接使用任务对象中的报告
- 设置路由已删除，使用统一设置系统 /settings/trading-agents
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)


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
