"""
用户认证依赖注入
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.auth.security import jwt_manager
from core.auth.rbac import Role
from core.db.mongodb import get_mongodb, mongodb
from core.user.models import PyObjectId, UserModel, UserStatus

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIOMotorDatabase:
    """获取数据库连接"""
    return await get_mongodb()


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
        # 兼容旧数据：如果没有 status 字段，根据 is_active 设置默认值
        if "status" not in user:
            user["status"] = UserStatus.ACTIVE if user.get("is_active", True) else UserStatus.DISABLED
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
        # 兼容旧数据：如果没有 status 字段，根据 is_active 设置默认值
        if "status" not in user:
            user["status"] = UserStatus.ACTIVE if user.get("is_active", True) else UserStatus.DISABLED

        # 显式将 _id 转换为 id 字符串（修复 alias 映射问题）
        if "_id" in user and "id" not in user:
            user["id"] = str(user["_id"])

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
    """获取当前激活用户（检查状态和 is_active）"""
    # 检查用户状态
    if current_user.status == UserStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用",
        )
    if current_user.status == UserStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被拒绝",
        )
    if current_user.status == UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号待审核",
        )

    # 检查 is_active 字段（兼容）
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


async def get_current_admin_user(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    """获取当前管理员用户"""
    if current_user.role not in (Role.ADMIN, Role.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


async def get_current_super_admin(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    """获取当前超级管理员用户"""
    if current_user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return current_user
