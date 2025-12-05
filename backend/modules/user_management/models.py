from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from core.auth.models import User, UserCreate


class UserRegisterResponse(BaseModel):
    """用户注册响应"""
    message: str
    user: User


class UserLoginResponse(BaseModel):
    """用户登录响应"""
    message: str
    token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class UserProfileUpdate(BaseModel):
    """用户资料更新"""
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    """密码修改"""
    current_password: str
    new_password: str