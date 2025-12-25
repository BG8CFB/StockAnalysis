"""
认证依赖注入
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.models import PyObjectId, UserModel
from core.auth.security import jwt_manager
from core.db.mongodb import mongodb

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UserModel]:
    """获取当前用户（可选，未登录返回 None）"""
    if credentials is None:
        return None

    token = credentials.credentials
    payload = jwt_manager.verify_token(token, "access")
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        user = await mongodb.database.users.find_one({"_id": PyObjectId(user_id)})
        if user is None:
            return None
        return UserModel(**user)
    except Exception:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserModel:
    """获取当前用户（必须登录）"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = jwt_manager.verify_token(token, "access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await mongodb.database.users.find_one({"_id": PyObjectId(user_id)})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        return UserModel(**user)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败",
        )


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """获取当前激活用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用",
        )
    return current_user


async def get_current_verified_user(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    """获取当前已验证用户"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户邮箱未验证",
        )
    return current_user
