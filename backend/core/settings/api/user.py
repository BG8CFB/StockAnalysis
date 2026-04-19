"""
用户配置管理 API 路由

提供用户配置的 CRUD、导入导出、配额查询等接口。
"""

import json
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from core.auth.dependencies import get_current_active_user
from core.settings.models.user import (
    CoreSettingsUpdate,
    NotificationSettingsUpdate,
    SettingsImport,
    UserSettingsResponse,
)
from core.settings.services.user_service import get_user_settings_service
from core.user.models import UserModel

router = APIRouter(prefix="/settings", tags=["User Settings"])

# =============================================================================
# 核心设置
# =============================================================================


@router.get("/core", response_model=UserSettingsResponse)
async def get_core_settings(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserSettingsResponse:
    """获取用户核心设置"""
    service = get_user_settings_service()
    settings = await service.get_user_settings(str(current_user.id))
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


@router.put("/core", response_model=UserSettingsResponse)
async def update_core_settings(
    request: CoreSettingsUpdate, current_user: UserModel = Depends(get_current_active_user)
) -> UserSettingsResponse:
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
    current_user: UserModel = Depends(get_current_active_user),
) -> UserSettingsResponse:
    """获取用户通知设置"""
    service = get_user_settings_service()
    settings = await service.get_user_settings(str(current_user.id))
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


@router.put("/notifications", response_model=UserSettingsResponse)
async def update_notification_settings(
    request: NotificationSettingsUpdate, current_user: UserModel = Depends(get_current_active_user)
) -> UserSettingsResponse:
    """更新用户通知设置"""
    service = get_user_settings_service()
    settings = await service.update_notification_settings(str(current_user.id), request)
    if not settings:
        raise HTTPException(status_code=404, detail="用户配置不存在")
    return settings


# =============================================================================
# TradingAgents 设置（全局配置，所有用户共享）
# =============================================================================


@router.get("/trading-agents")
async def get_trading_agents_settings(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    获取 TradingAgents 全局配置

    注意：TradingAgents 配置是全局的，由管理员设置，所有用户共享。
    此接口返回全局配置，不包含用户特定数据。
    """
    from core.settings.services.global_trading_agents_service import get_global_settings

    settings = await get_global_settings()
    return settings


# =============================================================================
# 配额信息
# =============================================================================


@router.get("/quota")
async def get_quota_info(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
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
    current_user: UserModel = Depends(get_current_active_user),
) -> JSONResponse:
    """
    导出用户配置

    返回 JSON 文件下载
    """
    service = get_user_settings_service()
    try:
        export_data = await service.export_settings(str(current_user.id))

        # 返回 JSON 文件下载
        json_data = export_data.model_dump_json(indent=2)
        filename = (
            f"settings_{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        return JSONResponse(
            content=json.loads(json_data),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/json",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/import")
async def import_settings(
    import_data: SettingsImport, current_user: UserModel = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    导入用户配置

    支持两种策略：
    - merge: 合并模式，只更新提供的字段
    - replace: 完全覆盖模式，替换所有配置
    """
    service = get_user_settings_service()
    try:
        settings = await service.import_settings(str(current_user.id), import_data)
        return {"success": True, "message": "配置导入成功", "settings": settings.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"配置导入失败: {str(e)}")


# =============================================================================
# 配额管理
# =============================================================================


@router.post("/quota/fix-concurrent")
async def fix_concurrent_tasks(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    诊断并修复并发任务计数

    对比数据库中实际活跃的任务数与计数器，自动修复不一致的情况。
    """
    service = get_user_settings_service()
    result = await service.diagnose_and_fix_concurrent_tasks(str(current_user.id))
    return result
