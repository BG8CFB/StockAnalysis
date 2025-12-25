"""
系统管理 API 路由
处理系统初始化、状态检查等
"""
from datetime import datetime
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


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status():
    """获取系统状态"""
    try:
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
                        "auto_fixed_at": datetime.utcnow(),
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
    except Exception as e:
        return {
            "initialized": False,
            "has_admin": False,
            "version": settings.APP_VERSION,
            "status": f"error: {str(e)}"
        }


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="系统已有管理员账号，无法初始化"
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
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await db.users.insert_one(user_doc)

        # 标记系统已初始化
        await db.system_config.update_one(
            {"_id": "system_init"},
            {
                "$set": {
                    "initialized": True,
                    "initialized_at": datetime.utcnow(),
                    "initialized_by": str(result.inserted_id),
                }
            },
            upsert=True
        )

        # 返回创建的用户信息
        created_user = await db.users.find_one({"_id": result.inserted_id})
        user_model = UserModel.model_validate(created_user)

        return {
            "success": True,
            "message": "系统初始化成功",
            "user": {
                "id": str(user_model.id),
                "email": user_model.email,
                "username": user_model.username,
                "role": user_model.role,
            }
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

        return {
            "success": True,
            "message": "系统已重置到未初始化状态"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置失败: {str(e)}"
        )
