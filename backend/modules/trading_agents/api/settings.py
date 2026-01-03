"""
TradingAgents 设置管理 API 路由
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends

from core.auth.dependencies import get_current_active_user
from core.user.models import UserModel

from modules.trading_agents.services.settings_service import get_trading_agents_settings_service
from modules.trading_agents.schemas import (
    TradingAgentsSettings,
    TradingAgentsSettingsResponse,
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/trading-agents/settings", tags=["TradingAgents - 设置"])


# =============================================================================
# TradingAgents 设置端点
# =============================================================================

@router.get("", response_model=TradingAgentsSettingsResponse)
async def get_settings(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取用户的 TradingAgents 设置

    返回用户的分析规则配置，包括 AI 模型、辩论轮次、超时等设置。

    Args:
        current_user: 当前用户

    Returns:
        用户设置，如果不存在则返回默认设置
    """
    service = get_trading_agents_settings_service()
    settings = await service.get_user_settings(str(current_user.id))

    if not settings:
        # 返回默认设置
        default_settings = TradingAgentsSettings()
        return TradingAgentsSettingsResponse(
            id="",
            user_id=str(current_user.id),
            settings=default_settings,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    return settings


@router.put("", response_model=TradingAgentsSettingsResponse)
async def update_settings(
    request: TradingAgentsSettings,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    更新用户的 TradingAgents 设置

    更新用户的分析规则配置，包括 AI 模型、辩论轮次、超时等设置。

    Args:
        request: 设置数据
        current_user: 当前用户

    Returns:
        更新后的设置
    """
    service = get_trading_agents_settings_service()
    updated = await service.update_user_settings(str(current_user.id), request)

    return updated
