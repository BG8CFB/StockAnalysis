"""
认证依赖注入
"""

from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.models import PyObjectId, UserModel  # noqa: F401 - re-exports for backward compat
from core.auth.security import jwt_manager
from core.db.mongodb import mongodb
from core.db.redis import UserRedisKey, get_redis

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
    except (ValueError, TypeError, KeyError):
        # 预期的数据格式错误，视为未认证
        return None
    except Exception as e:
        # 非预期错误（数据库故障、网络超时等）记录告警日志，而非静默忽略
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"获取用户信息时发生意外错误: user_id={user_id}, error={e}", exc_info=True)
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
    ticket: Optional[str] = Query(
        None, description="短期认证 ticket，用于 SSE/WS，避免 token 出现在 URL"
    ),
) -> UserModel:
    """
    获取当前用户（支持 Authorization Header、查询参数 token、或短期 ticket）

    用于 SSE 连接等不支持自定义 header 的场景。优先使用 ticket 可避免 JWT 出现在 URL。
    """
    user_id = None

    # 1. 优先从 Authorization Header 获取 token
    if credentials is not None:
        payload = jwt_manager.verify_token(credentials.credentials, "access")
        if payload:
            user_id = payload.get("sub")

    # 2. 若无 Header token，从查询参数 token 获取
    if user_id is None and token is not None:
        payload = jwt_manager.verify_token(token, "access")
        if payload:
            user_id = payload.get("sub")

    # 3. 若无 token，尝试短期 ticket（一次性，从 Redis 换取 user_id）
    if user_id is None and ticket is not None:
        try:
            redis = await get_redis()
            key = UserRedisKey.stream_ticket(ticket)
            raw = await redis.get(key)
            await redis.delete(key)  # 一次性使用
            if raw:
                user_id = raw.strip()
        except Exception:
            pass

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌或 ticket 无效/已使用",
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户数据格式错误",
        )
    except Exception:
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
