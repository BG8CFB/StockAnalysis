"""
用户配置管理 API 路由

提供用户配置的 CRUD、导入导出、配额查询等接口。
"""

import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from core.auth.dependencies import get_current_user, get_current_active_user
from core.auth.rbac import Role, require_role
from core.user.models import UserModel
from core.settings.models.user import (
    CoreSettingsUpdate,
    NotificationSettingsUpdate,
    TradingAgentsSettingsUpdate,
    UserSettingsResponse,
    SettingsExport,
    SettingsImport,
)
from core.settings.services.user_service import get_user_settings_service

router = APIRouter(prefix="/settings", tags=["User Settings"])

# =============================================================================
# 核心设置
# =============================================================================

@router.get("/core", response_model=UserSettingsResponse)
async def get_core_settings(
    current_user: UserModel = Depends(get_current_active_user)
):
    """获取用户核心设置"""
    service = get_user_settings_service()
    settings = await service.get_user_settings(str(current_user.id))
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


@router.put("/core", response_model=UserSettingsResponse)
async def update_core_settings(
    request: CoreSettingsUpdate,
    current_user: UserModel = Depends(get_current_active_user)
):
    """更新用户核心设置"""
    service = get_user_settings_service()
    settings = await service.update_core_settings(str(current_user.id), request)
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


# =============================================================================
# 通知设置
# =============================================================================

@router.get("/notifications", response_model=UserSettingsResponse)
async def get_notification_settings(
    current_user: UserModel = Depends(get_current_active_user)
):
    """获取用户通知设置"""
    service = get_user_settings_service()
    settings = await service.get_user_settings(str(current_user.id))
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


@router.put("/notifications", response_model=UserSettingsResponse)
async def update_notification_settings(
    request: NotificationSettingsUpdate,
    current_user: UserModel = Depends(get_current_active_user)
):
    """更新用户通知设置"""
    service = get_user_settings_service()
    settings = await service.update_notification_settings(str(current_user.id), request)
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


# =============================================================================
# TradingAgents 设置
# =============================================================================

@router.get("/trading-agents", response_model=UserSettingsResponse)
async def get_trading_agents_settings(
    current_user: UserModel = Depends(get_current_active_user)
):
    """获取 TradingAgents 设置"""
    service = get_user_settings_service()
    settings = await service.get_user_settings(str(current_user.id))
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


@router.put("/trading-agents", response_model=UserSettingsResponse)
async def update_trading_agents_settings(
    request: TradingAgentsSettingsUpdate,
    current_user: UserModel = Depends(get_current_active_user)
):
    """更新 TradingAgents 设置"""
    service = get_user_settings_service()
    settings = await service.update_trading_agents_settings(str(current_user.id), request)
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


# =============================================================================
# 配额信息
# =============================================================================

@router.get("/quota")
async def get_quota_info(
    current_user: UserModel = Depends(get_current_active_user)
):
    """获取用户配额信息"""
    service = get_user_settings_service()
    quota = await service.get_quota_info(str(current_user.id))
    if not quota:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return quota.model_dump()


# =============================================================================
# 配置导入导出
# =============================================================================

@router.get("/export")
async def export_settings(
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    导出用户配置

    返回 JSON 文件下载
    """
    service = get_user_settings_service()
    try:
        export_data = await service.export_settings(str(current_user.id))

        # 返回 JSON 文件下载
        json_data = export_data.model_dump_json(indent=2)
        filename = f"settings_{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return JSONResponse(
            content=json.loads(json_data),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/json",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/import")
async def import_settings(
    import_data: SettingsImport,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    导入用户配置

    支持两种策略：
    - merge: 合并模式，只更新提供的字段
    - replace: 完全覆盖模式，替换所有配置
    """
    service = get_user_settings_service()
    try:
        settings = await service.import_settings(str(current_user.id), import_data)
        return {
            "success": True,
            "message": "配置导入成功",
            "settings": settings.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"配置导入失败: {str(e)}")


# =============================================================================
# 兼容旧接口
# =============================================================================

@router.get("/preferences")
async def get_preferences_legacy(
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取用户偏好（兼容旧接口）

    保持向后兼容，返回旧格式的数据
    """
    service = get_user_settings_service()
    settings = await service.get_user_settings(str(current_user.id))

    if not settings:
        # 返回默认值
        return {
            "theme": "light",
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "watchlist": [],
            "notification_enabled": True,
            "email_alerts": False,
        }

    # 转换为旧格式
    return {
        "theme": settings.core_settings.theme,
        "language": settings.core_settings.language,
        "timezone": settings.core_settings.timezone,
        "watchlist": settings.core_settings.watchlist,
        "notification_enabled": settings.notification_settings.enabled,
        "email_alerts": settings.notification_settings.email_alerts,
    }


@router.put("/preferences")
async def update_preferences_legacy(
    request: dict,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    更新用户偏好（兼容旧接口）

    保持向后兼容，接受旧格式的数据
    """
    service = get_user_settings_service()

    # 构建更新请求
    core_update = CoreSettingsUpdate()
    notification_update = NotificationSettingsUpdate()

    if "theme" in request:
        core_update.theme = request["theme"]
    if "language" in request:
        core_update.language = request["language"]
    if "timezone" in request:
        core_update.timezone = request["timezone"]
    if "watchlist" in request:
        core_update.watchlist = request["watchlist"]
    if "notification_enabled" in request:
        notification_update.enabled = request["notification_enabled"]
    if "email_alerts" in request:
        notification_update.email_alerts = request["email_alerts"]

    # 更新配置
    await service.update_core_settings(str(current_user.id), core_update)
    await service.update_notification_settings(str(current_user.id), notification_update)

    # 返回更新后的配置（旧格式）
    return await get_preferences_legacy(current_user)
