from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Any

from core.auth.dependencies import get_current_user, get_current_active_user
from core.auth.models import User as CurrentUser

from .service import user_service
from .models import (
    UserCreate, UserRegisterResponse, UserLoginResponse,
    UserResponse, UserProfileUpdate, PasswordChange
)

# 创建路由器
router = APIRouter()

# 安全方案
security = HTTPBearer()


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate) -> Any:
    """用户注册"""
    try:
        user = await user_service.create_user(user_data)
        return UserRegisterResponse(
            message="User registered successfully",
            user=user
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=UserLoginResponse)
async def login(email: str, password: str) -> Any:
    """用户登录"""
    try:
        access_token, user = await user_service.login_user(email, password)
        return UserLoginResponse(
            message="Login successful",
            token=access_token,
            expires_in=1800,  # 30分钟
            user=user
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_active_user)
) -> Any:
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserProfileUpdate,
    current_user: CurrentUser = Depends(get_current_active_user)
) -> Any:
    """更新当前用户资料"""
    try:
        updated_user = await user_service.update_user_profile(current_user.id, update_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            username=updated_user.username,
            full_name=updated_user.full_name,
            is_active=updated_user.is_active,
            is_superuser=updated_user.is_superuser,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
            last_login=updated_user.last_login
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: CurrentUser = Depends(get_current_active_user)
) -> Any:
    """修改当前用户密码"""
    try:
        success = await user_service.change_password(current_user.id, password_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}"
        )


@router.post("/logout")
async def logout(
    current_user: CurrentUser = Depends(get_current_active_user)
) -> Any:
    """用户登出"""
    # 在实际应用中，这里可以将token加入黑名单
    # 目前只返回成功消息
    return {"message": "Logout successful"}