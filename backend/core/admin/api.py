"""
管理员核心 API 路由
处理用户审核、管理、列表查询等
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.admin.service import admin_service
from core.auth.rbac import Role
from core.user.dependencies import get_current_admin_user, get_current_super_admin
from core.user.models import (
    ApproveUserRequest,
    DisableUserRequest,
    RejectUserRequest,
    UpdateUserByAdminRequest,
    UserListResponse,
    UserModel,
    UserStatus,
)

router = APIRouter(prefix="/admin", tags=["管理员"])


# ==================== 用户管理 ====================


@router.get("/users")
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[Role] = None,
    status: Optional[UserStatus] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """获取用户列表（支持筛选和搜索）"""
    users, total = await admin_service.get_users(
        skip=skip,
        limit=limit,
        role=role,
        status=status,
        is_active=is_active,
        search=search,
    )
    return {"users": users, "total": total}


@router.get("/users/pending")
async def get_pending_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """获取待审核用户列表"""
    users, total = await admin_service.get_pending_users(skip=skip, limit=limit)
    return {"users": users, "total": total}


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """获取单个用户详情"""
    try:
        user = await admin_service.get_user_by_id(user_id)
        return user.model_dump()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/users")
async def create_user(
    data: dict,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """管理员创建用户"""
    try:
        user = await admin_service.create_user(
            email=data.get("email"),
            username=data.get("username"),
            password=data.get("password"),
            role=data.get("role", Role.USER),
            created_by=str(current_admin.id),
        )
        return user.model_dump()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    data: ApproveUserRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """通过用户审核"""
    try:
        user = await admin_service.approve_user(user_id, str(current_admin.id))
        return {
            "success": True,
            "message": "用户审核通过",
            "user": UserListResponse(**user.model_dump()),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/users/{user_id}/reject")
async def reject_user(
    user_id: str,
    data: RejectUserRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """拒绝用户审核"""
    try:
        user = await admin_service.reject_user(user_id, str(current_admin.id), data.reason)
        return {
            "success": True,
            "message": "用户已拒绝",
            "user": UserListResponse(**user.model_dump()),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    data: DisableUserRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """禁用用户"""
    try:
        user = await admin_service.disable_user(user_id, str(current_admin.id), data.reason)
        return {
            "success": True,
            "message": "用户已禁用",
            "user": UserListResponse(**user.model_dump()),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/users/{user_id}/enable")
async def enable_user(
    user_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """启用用户"""
    try:
        user = await admin_service.enable_user(user_id, str(current_admin.id))
        return {
            "success": True,
            "message": "用户已启用",
            "user": UserListResponse(**user.model_dump()),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UpdateUserByAdminRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """更新用户信息"""
    try:
        user = await admin_service.update_user(user_id, data.model_dump(exclude_unset=True))
        return {
            "success": True,
            "message": "用户信息已更新",
            "user": UserListResponse(**user.model_dump()),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    new_role: Role = Query(...),
    current_admin: UserModel = Depends(get_current_super_admin),
):
    """修改用户角色（仅超级管理员）"""
    try:
        user = await admin_service.change_user_role(user_id, new_role, str(current_admin.id))
        return {
            "success": True,
            "message": "用户角色已修改",
            "user": UserListResponse(**user.model_dump()),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """删除用户"""
    try:
        success = await admin_service.delete_user(user_id, str(current_admin.id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        return {"success": True, "message": "用户已删除"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/users/{user_id}/reset-password")
async def admin_request_password_reset(
    user_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """管理员触发用户密码重置"""
    try:
        reset_token = await admin_service.admin_request_password_reset(user_id, str(current_admin.id))
        # 开发环境返回 token，生产环境应该只返回成功消息
        return {
            "success": True,
            "message": "密码重置链接已生成",
            "token": reset_token if current_admin.role == Role.SUPER_ADMIN else None,  # 只有超管能看到token
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ==================== 审计日志 ====================


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """获取审计日志"""
    from core.user.service import user_service

    logs = await user_service.get_audit_logs(
        skip=skip,
        limit=limit,
        action=action,
        user_id=user_id,
    )
    return {"logs": logs}
