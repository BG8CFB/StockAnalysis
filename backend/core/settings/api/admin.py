"""
管理员 - TradingAgents 全局配置 API 路由

提供管理员对 TradingAgents 模块全局配置的管理接口。
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from core.auth.dependencies import get_current_active_user
from core.auth.rbac import Role, require_role
from core.user.models import UserModel
from core.settings.models.user import TradingAgentsSettingsUpdate
from core.settings.services.global_trading_agents_service import (
    get_global_settings,
    update_global_settings,
    reset_to_defaults,
)

router = APIRouter(prefix="/admin/settings/trading-agents", tags=["Admin - TradingAgents Settings"])


@router.get("")
async def admin_get_trading_agents_settings(
    current_user: UserModel = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    获取 TradingAgents 全局配置（管理员）

    所有用户共享此配置，需要管理员权限。
    """
    require_role(current_user, Role.ADMIN)

    settings = await get_global_settings()
    return settings


@router.put("")
async def admin_update_trading_agents_settings(
    request: TradingAgentsSettingsUpdate,
    current_user: UserModel = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    更新 TradingAgents 全局配置（管理员）

    所有用户共享此配置，需要管理员权限。
    """
    require_role(current_user, Role.ADMIN)

    # 只传递非 None 的字段
    update_data = request.model_dump(exclude_none=True)
    settings = await update_global_settings(update_data)

    return settings


@router.post("/reset")
async def admin_reset_trading_agents_settings(
    current_user: UserModel = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    重置 TradingAgents 全局配置为默认值（管理员）

    所有用户共享此配置，需要管理员权限。
    """
    require_role(current_user, Role.ADMIN)

    await reset_to_defaults()
    default_settings = await get_global_settings()

    return {
        "message": "全局配置已重置为默认值",
        "settings": default_settings
    }
