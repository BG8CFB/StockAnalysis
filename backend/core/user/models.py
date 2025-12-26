"""
用户核心数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from core.config import settings
from core.auth.rbac import Role
from core.db.models import PyObjectId

class UserStatus(str, Enum):
    """用户状态枚举"""
    PENDING = "pending"       # 待审核
    ACTIVE = "active"         # 已激活
    DISABLED = "disabled"     # 已禁用
    REJECTED = "rejected"     # 已拒绝


# ==================== 数据库模型 ====================


class UserModel(BaseModel):
    """用户模型（数据库）- 完整版本"""

    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email: EmailStr
    username: str
    hashed_password: str  # 永远不在响应中返回
    role: Role = Role.USER
    status: UserStatus = Field(default=UserStatus.ACTIVE)  # 兼容旧数据默认为 ACTIVE

    # 审核相关
    reviewed_by: Optional[PyObjectId] = None  # 审核人
    reviewed_at: Optional[datetime] = None    # 审核时间
    reject_reason: Optional[str] = None       # 拒绝原因

    # 基础字段
    is_active: bool = True  # 保留（兼容 status，DISABLED 时为 False）
    is_verified: bool = False
    created_by: Optional[PyObjectId] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class UserPreferences(BaseModel):
    """用户配置"""
    user_id: PyObjectId
    theme: str = "light"
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    notification_enabled: bool = True
    email_alerts: bool = False


# ==================== 请求/响应模型 ====================


class SystemInitializeRequest(BaseModel):
    """系统初始化请求"""
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("两次输入的密码不一致")
        return v


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    initialized: bool
    version: str
    users_count: int = 0


# ==================== 认证相关 ====================


class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    confirm_password: str
    captcha_token: Optional[str] = None
    slide_x: Optional[int] = None
    slide_y: Optional[int] = None

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("两次输入的密码不一致")
        return v


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str
    captcha_token: Optional[str] = None
    slide_x: Optional[int] = None
    slide_y: Optional[int] = None


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


# ==================== 用户信息响应（不含密码）====================


class UserResponse(BaseModel):
    """用户信息响应（不含密码）"""
    id: str
    email: str
    username: str
    role: str
    status: UserStatus
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """用户列表响应（管理员）"""
    id: str
    email: str
    username: str
    role: str
    status: UserStatus
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = Field(None, serialization_alias="last_login")
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


# ==================== 更新相关 ====================


class UpdateUserRequest(BaseModel):
    """更新用户信息请求"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=2, max_length=50)


class UpdateUserByAdminRequest(BaseModel):
    """管理员更新用户信息请求"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class UpdatePreferencesRequest(BaseModel):
    """更新用户配置请求"""
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    notification_enabled: Optional[bool] = None
    email_alerts: Optional[bool] = None


class CreateUserRequest(BaseModel):
    """管理员创建用户请求"""
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    role: Role = Role.USER


# ==================== 审核相关 ====================


class ApproveUserRequest(BaseModel):
    """通过用户审核"""
    pass


class RejectUserRequest(BaseModel):
    """拒绝用户审核"""
    reason: str = Field(..., min_length=1, max_length=500, description="拒绝原因")


class DisableUserRequest(BaseModel):
    """禁用用户请求"""
    reason: Optional[str] = Field(None, max_length=500, description="禁用原因")


# ==================== 密码重置相关 ====================


class RequestPasswordResetRequest(BaseModel):
    """请求密码重置"""
    email: EmailStr
    captcha_token: Optional[str] = None
    slide_x: Optional[int] = None
    slide_y: Optional[int] = None


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    token: str
    new_password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("两次输入的密码不一致")
        return v


class AdminResetPasswordRequest(BaseModel):
    """管理员触发密码重置请求"""
    email: EmailStr  # 目标用户邮箱


# ==================== 验证码相关 ====================


class CaptchaGenerateRequest(BaseModel):
    """生成验证码请求"""
    action: Literal["login", "register", "reset_password"] = "login"


class CaptchaGenerateResponse(BaseModel):
    """生成验证码响应"""
    token: str
    puzzle_position: Dict  # {"x": 100, "y": 50}


class CaptchaVerifyRequest(BaseModel):
    """验证验证码请求"""
    token: str
    slide_x: int
    slide_y: int


class CaptchaRequiredResponse(BaseModel):
    """检查是否需要验证码响应"""
    required: bool
    reason: Optional[str] = None


# ==================== 邮箱验证码模型 ====================


class EmailCodeSendRequest(BaseModel):
    """发送邮箱验证码请求"""
    email: EmailStr
    captcha_token: Optional[str] = None
    slide_x: Optional[int] = None
    slide_y: Optional[int] = None


class EmailCodeSendResponse(BaseModel):
    """发送邮箱验证码响应"""
    code_id: str
    expires_in: int


class EmailCodeVerifyRequest(BaseModel):
    """验证邮箱验证码请求"""
    email: EmailStr
    code_id: str
    code: str


# ==================== 审计日志模型 ====================


class AuditLogResponse(BaseModel):
    """审核日志响应"""
    id: str
    user_id: str
    action: Literal[
        "approve", "reject", "disable", "enable",
        "create", "update", "delete", "role_change",
        "password_reset", "login", "logout"
    ]
    target_user_id: Optional[str] = None
    reason: Optional[str] = None
    auditor_id: str
    auditor_name: str
    ip_address: Optional[str] = None
    created_at: datetime
