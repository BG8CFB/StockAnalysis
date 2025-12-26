"""
认证相关数据模型
"""
from datetime import datetime
from typing import Any, Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator

from core.auth.rbac import Role
from core.config import settings
from core.db.models import PyObjectId
class UserModel(BaseModel):
    """用户模型（数据库）"""

    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email: EmailStr
    username: str
    hashed_password: str
    role: Role = Role.USER
    is_active: bool = True
    is_verified: bool = False
    status: str = "active"
    created_by: Optional[PyObjectId] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_by: Optional[PyObjectId] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class UserPreferences(BaseModel):
    """用户配置"""

    user_id: PyObjectId
    theme: str = "light"
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    watchlist: list[str] = Field(default_factory=list)
    notification_enabled: bool = True
    email_alerts: bool = False


# ==================== 系统初始化模型 ====================


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


# ==================== 请求/响应模型 ====================


class RegisterRequest(BaseModel):
    """注册请求"""

    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)  # 新增
    password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    confirm_password: str
    captcha_token: Optional[str] = None  # 验证码 token
    slide_x: Optional[int] = None  # 滑块 X 坐标
    slide_y: Optional[int] = None  # 滑块 Y 坐标

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
    captcha_token: Optional[str] = None  # 验证码 token（可选）
    slide_x: Optional[int] = None  # 滑块 X 坐标
    slide_y: Optional[int] = None  # 滑块 Y 坐标


class TokenResponse(BaseModel):
    """令牌响应"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str


class UserResponse(BaseModel):
    """用户信息响应"""

    id: str
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    status: str = "active"
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
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


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


# ==================== 增强的请求模型 ====================


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


# ==================== 邮箱验证码模型 ====================


class EmailCodeSendRequest(BaseModel):
    """发送邮箱验证码请求"""

    email: EmailStr
    captcha_token: Optional[str] = None  # 可能需要先通过图形验证码
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
