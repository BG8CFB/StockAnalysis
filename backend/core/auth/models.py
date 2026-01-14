"""
认证相关数据模型
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

# 从 core.user.models 导入统一的模型定义
from core.user.models import (
    UserModel,
    UserStatus,
    SystemInitializeRequest,
    SystemStatusResponse,
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    UserListResponse,
    UpdateUserRequest,
    UpdateUserByAdminRequest,
    UpdatePreferencesRequest,
    CreateUserRequest,
    EmailCodeSendRequest,
    EmailCodeSendResponse,
    EmailCodeVerifyRequest,
)

from core.auth.rbac import Role
from core.config import settings
from core.db.models import PyObjectId


# ==================== 验证码相关模型 ====================


class CaptchaGenerateRequest(BaseModel):
    """生成验证码请求"""

    action: Literal["login", "register", "reset_password"] = "login"


class CaptchaGenerateResponse(BaseModel):
    """生成验证码响应"""

    token: str
    puzzle_position: dict  # {"x": 100, "y": 50}


class CaptchaVerifyRequest(BaseModel):
    """验证验证码请求"""

    token: str
    slide_x: int
    slide_y: int


class CaptchaRequiredResponse(BaseModel):
    """检查是否需要验证码响应"""

    required: bool
    reason: Optional[str] = None  # 需要验证码的原因


# ==================== 增强的请求模型（带验证码的登录/注册）====================


class RegisterRequestWithCaptcha(RegisterRequest):
    """带验证码的注册请求"""

    captcha_token: str
    slide_x: int
    slide_y: int


class LoginRequestWithCaptcha(LoginRequest):
    """带验证码的登录请求"""

    captcha_token: Optional[str] = None
    slide_x: Optional[int] = None
    slide_y: Optional[int] = None


# ==================== 审计日志模型 ====================


class AuditLog(BaseModel):
    """审计日志"""

    id: str
    user_id: str
    action: str
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class AuditLogQuery(BaseModel):
    """审计日志查询"""

    skip: int = 0
    limit: int = 20
    action: Optional[str] = None
    user_id: Optional[str] = None
