"""
系统管理 API 路由
处理系统初始化、状态检查等
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from core.auth.rbac import Role
from core.auth.security import password_manager
from core.config import settings
from core.db.mongodb import mongodb
from core.user.models import RegisterRequest, UserModel, UserStatus

router = APIRouter(tags=["系统管理"])

# 系统状态缓存（简单的内存缓存）
_status_cache: Optional[dict] = None
_cache_lock = asyncio.Lock()
_CACHE_TTL = 30  # 缓存有效期（秒）


class SystemStatus(BaseModel):
    """系统状态"""
    initialized: bool
    has_admin: bool
    version: str
    status: str


class SystemInitRequest(BaseModel):
    """系统初始化请求"""
    email: str
    username: str
    password: str


async def _get_system_status_from_db() -> dict:
    """
    从数据库获取系统状态（内部函数）
    """
    db = mongodb.database

    # 检查是否有管理员账号
    admin_count = await db.users.count_documents({
        "role": {"$in": [Role.ADMIN, Role.SUPER_ADMIN]}
    })
    has_admin = admin_count > 0

    # 检查系统配置中的初始化标记
    config = await db.system_config.find_one({"_id": "system_init"})
    config_initialized = config is not None and config.get("initialized", False)

    # 智能判断：如果有管理员用户，系统即视为已初始化
    # 同时同步状态到配置文件（防止不一致）
    initialized = has_admin or config_initialized
    if has_admin and not config_initialized:
        # 自动修复：有管理员但配置未标记，自动同步
        await db.system_config.update_one(
            {"_id": "system_init"},
            {
                "$set": {
                    "initialized": True,
                    "auto_fixed_at": datetime.now(timezone.utc),
                    "fix_reason": "admin_exists_but_config_not_initialized"
                }
            },
            upsert=True
        )

    return {
        "initialized": initialized,
        "has_admin": has_admin,
        "version": settings.APP_VERSION,
        "status": "running",
        "debug": settings.DEBUG,
        "captcha_enabled": settings.CAPTCHA_ENABLED
    }


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status():
    """
    获取系统状态

    异常处理策略：
    - 使用内存缓存减少数据库查询（30秒 TTL）
    - 如果数据库连接失败或查询出错，抛出 500 错误让前端处理
    - 不再返回 initialized: False，避免前端误判导致状态不一致
    """
    async with _cache_lock:
        global _status_cache

        # 检查缓存是否有效
        if _status_cache is not None:
            cache_time = _status_cache.get("time")
            if cache_time and (datetime.now(timezone.utc).timestamp() - cache_time) < _CACHE_TTL:
                # 返回缓存数据
                return {k: v for k, v in _status_cache.items() if k != "time"}

        # 从数据库获取最新状态
        status_data = await _get_system_status_from_db()

        # 更新缓存
        _status_cache = {**status_data, "time": datetime.now(timezone.utc).timestamp()}

        return {k: v for k, v in status_data.items() if k != "time"}


@router.post("/system/initialize")
async def initialize_system(data: SystemInitRequest):
    """
    初始化系统并创建第一个超级管理员

    注意：此接口仅在系统未初始化时可用，初始化后自动禁用
    """
    try:
        db = mongodb.database

        # 检查是否已有管理员账号（统一判断标准）
        admin_count = await db.users.count_documents({
            "role": {"$in": [Role.ADMIN, Role.SUPER_ADMIN]}
        })
        if admin_count > 0:
            # 自动修复状态：如果有管理员但配置未标记，同步状态
            config = await db.system_config.find_one({"_id": "system_init"})
            if not config or not config.get("initialized", False):
                await db.system_config.update_one(
                    {"_id": "system_init"},
                    {"$set": {"initialized": True}},
                    upsert=True
                )
            # 提供更详细的错误提示
            hint = ""
            if settings.DEBUG:
                hint = " 开发环境可使用 /api/system/reinit 接口重置。"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"系统已完成初始化，已有 {admin_count} 个管理员账号。请直接登录。{hint}"
            )

        # 检查用户名/邮箱是否已存在
        existing = await db.users.find_one({
            "$or": [{"email": data.email}, {"username": data.username}]
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名或邮箱已存在"
            )

        # 创建超级管理员
        hashed_password = password_manager.hash_password(data.password)
        user_doc = {
            "email": data.email,
            "username": data.username,
            "hashed_password": hashed_password,
            "role": Role.SUPER_ADMIN,
            "status": UserStatus.ACTIVE,
            "is_active": True,
            "is_verified": True,  # 超级管理员默认已验证
            "created_by": None,
            "last_login_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        result = await db.users.insert_one(user_doc)

        # 标记系统已初始化
        await db.system_config.update_one(
            {"_id": "system_init"},
            {
                "$set": {
                    "initialized": True,
                    "initialized_at": datetime.now(timezone.utc),
                    "initialized_by": str(result.inserted_id),
                }
            },
            upsert=True
        )

        # 返回创建的用户信息
        created_user = await db.users.find_one({"_id": result.inserted_id})
        user_model = UserModel.model_validate(created_user)

        # 自动登录：生成 access_token 和 refresh_token
        from core.auth.security import jwt_manager
        access_token = jwt_manager.create_access_token(
            data={"sub": str(user_model.id), "role": user_model.role}
        )
        refresh_token = jwt_manager.create_refresh_token(
            data={"sub": str(user_model.id)}
        )

        # 清除状态缓存，确保下次查询返回最新状态
        async with _cache_lock:
            global _status_cache
            _status_cache = None

        return {
            "success": True,
            "message": "系统初始化成功",
            "user": {
                "id": str(user_model.id),
                "email": user_model.email,
                "username": user_model.username,
                "role": user_model.role,
            },
            # 返回 token，让前端自动登录
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"系统初始化失败: {str(e)}"
        )


@router.post("/system/reinit")
async def reinitialize_system():
    """
    重置系统初始化状态（危险操作，仅用于开发/测试）

    注意：此操作会删除所有管理员账号并重置系统状态
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此操作仅在 DEBUG 模式下可用"
        )

    try:
        db = mongodb.database

        # 删除所有管理员账号
        await db.users.delete_many({
            "role": {"$in": [Role.ADMIN, Role.SUPER_ADMIN]}
        })

        # 重置系统初始化状态
        await db.system_config.update_one(
            {"_id": "system_init"},
            {"$set": {"initialized": False}},
            upsert=True
        )

        # 清除状态缓存，确保下次查询返回最新状态
        async with _cache_lock:
            global _status_cache
            _status_cache = None

        return {
            "success": True,
            "message": "系统已重置到未初始化状态"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置失败: {str(e)}"
        )
