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
        return UserModel.model_validate(user)
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
        return UserModel.model_validate(user)
    except HTTPException:
        raise
    except (ValueError, TypeError):
        # ObjectId 转换错误或模型验证错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户数据格式错误",
        )
    except Exception:
        # 其他未预期的错误（数据库连接错误等）
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


async def get_current_user_from_query(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = None,
) -> UserModel:
    """
    获取当前用户（支持从 Authorization Header 或查询参数获取 token）

    用于 SSE 连接等不支持自定义 header 的场景
    """
    # 优先从 Authorization Header 获取 token
    auth_token = None
    if credentials is not None:
        auth_token = credentials.credentials

    # 如果 Header 中没有 token，从查询参数获取
    if auth_token is None and token is not None:
        auth_token = token

    if auth_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
        )

    payload = jwt_manager.verify_token(auth_token, "access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
        )

    try:
        user = await mongodb.database.users.find_one({"_id": PyObjectId(user_id)})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        return UserModel.model_validate(user)
    except HTTPException:
        raise
    except (ValueError, TypeError):
        # ObjectId 转换错误或模型验证错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户数据格式错误",
        )
    except Exception:
        # 其他未预期的错误（数据库连接错误等）
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败",
        )


async def verify_token_only(token: str) -> UserModel:
    """
    仅通过 Token 验证用户（不使用 FastAPI 依赖注入）

    专用于 WebSocket、SSE 等无法使用 HTTP Header 的场景。
    与 get_current_user_from_query 不同，这个函数不接受 Depends 参数，
    可以直接在 WebSocket 路由中调用。

    Args:
        token: JWT 访问令牌字符串

    Returns:
        UserModel: 验证通过的用户对象

    Raises:
        HTTPException: Token 无效或用户不存在
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
        )

    # 验证 token
    payload = jwt_manager.verify_token(token, "access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )

    # 获取用户 ID
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
        )

    # 查询用户
    try:
        user = await mongodb.database.users.find_one({"_id": PyObjectId(user_id)})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        return UserModel.model_validate(user)
    except HTTPException:
        raise
    except (ValueError, TypeError):
        # ObjectId 转换错误或模型验证错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户数据格式错误",
        )
    except Exception:
        # 其他未预期的错误（数据库连接错误等）
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败",
        )
