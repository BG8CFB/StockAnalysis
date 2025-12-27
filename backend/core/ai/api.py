"""
核心 AI 模块 API 路由

提供统一的 AI 模型配置管理接口，作为项目的公共基础设施。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from core.auth.dependencies import get_current_active_user
from core.user.models import UserModel
from core.auth.rbac import Role
from core.ai.model import get_model_service
from core.ai.model.schemas import (
    AIModelConfigCreate,
    AIModelConfigUpdate,
    AIModelConfigResponse,
    AIModelTestRequest,
    ConnectionTestResponse,
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/ai", tags=["AI Core"])


# =============================================================================
# AI 模型管理端点
# =============================================================================

@router.post("/models", response_model=AIModelConfigResponse)
async def create_model(
    request: AIModelConfigCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    创建 AI 模型配置

    Args:
        request: 模型配置请求
        current_user: 当前用户

    Returns:
        创建的模型配置
    """
    # 系统级配置需要管理员权限
    if request.is_system:
        # TODO: 添加管理员权限检查
        pass

    service = get_model_service()
    return await service.create_model(str(current_user.id), request)


@router.get("/models")
async def list_models(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    列出 AI 模型配置

    Args:
        current_user: 当前用户

    Returns:
        模型配置列表 {"system": [...], "user": [...]}
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    return await service.list_models(str(current_user.id), is_admin)


@router.get("/models/{model_id}", response_model=AIModelConfigResponse)
async def get_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取单个 AI 模型配置

    Args:
        model_id: 模型 ID
        current_user: 当前用户

    Returns:
        模型配置
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    model = await service.get_model(model_id, str(current_user.id), is_admin)

    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    return model


@router.put("/models/{model_id}", response_model=AIModelConfigResponse)
async def update_model(
    model_id: str,
    request: AIModelConfigUpdate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    更新 AI 模型配置

    Args:
        model_id: 模型 ID
        request: 更新请求
        current_user: 当前用户

    Returns:
        更新后的模型配置
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    model = await service.update_model(model_id, str(current_user.id), request, is_admin)

    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在或无权修改")

    return model


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    删除 AI 模型配置

    Args:
        model_id: 模型 ID
        current_user: 当前用户

    Returns:
        操作结果
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    success = await service.delete_model(model_id, str(current_user.id), is_admin)

    if not success:
        raise HTTPException(status_code=404, detail="模型配置不存在或无权删除")

    return {"message": "模型配置已删除", "success": True}


@router.post("/models/{model_id}/test", response_model=ConnectionTestResponse)
async def test_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    测试 AI 模型连接

    Args:
        model_id: 模型 ID
        current_user: 当前用户

    Returns:
        测试结果
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()

    # 获取模型配置
    model = await service.get_model(model_id, str(current_user.id), is_admin)
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    # 构建测试请求
    test_request = AIModelTestRequest(
        api_base_url=model.api_base_url,
        api_key=model.api_key,
        model_id=model.model_id,
        timeout_seconds=10,
    )

    return await service.test_model_connection(test_request)


@router.post("/models/test", response_model=ConnectionTestResponse)
async def test_model_connection(
    request: AIModelTestRequest,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    测试 AI 模型连接（通用接口）

    Args:
        request: 测试请求
        current_user: 当前用户

    Returns:
        测试结果
    """
    service = get_model_service()
    return await service.test_model_connection(request)


# =============================================================================
# 健康检查端点
# =============================================================================

@router.get("/health")
async def health_check():
    """
    健康检查端点

    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "module": "AI Core",
    }
