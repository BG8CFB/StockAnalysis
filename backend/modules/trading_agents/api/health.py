"""
健康检查 API 路由
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/trading-agents", tags=["TradingAgents - 健康检查"])


@router.get("/health", response_model=dict)
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
