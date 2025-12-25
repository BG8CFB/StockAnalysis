"""
系统设置 API 路由
"""
from fastapi import APIRouter, Depends

from core.settings.service import settings_service
from core.user.dependencies import get_current_admin_user, get_current_super_admin
from core.user.models import UserModel

router = APIRouter(tags=["系统设置"])


@router.get("/settings/system")
async def get_system_config(
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """获取系统配置"""
    config = await settings_service.get_system_config()
    return config


@router.put("/settings/system")
async def update_system_config(
    config_updates: dict,
    current_admin: UserModel = Depends(get_current_super_admin),
):
    """更新系统配置（仅超级管理员）"""
    config = await settings_service.update_system_config(config_updates, str(current_admin.id))
    return {"success": True, "message": "系统配置已更新", "config": config}


@router.get("/system/info")
async def get_system_info(
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """获取完整系统信息"""
    info = await settings_service.get_system_info()
    return info
