"""
用户核心模块
"""
from core.user.dependencies import (
    get_current_active_user,
    get_current_admin_user,
    get_current_super_admin,
    get_current_user,
    get_current_user_optional,
    get_current_verified_user,
    get_db,
)
from core.user.models import (
    AdminResetPasswordRequest,
    ApproveUserRequest,
    DisableUserRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RejectUserRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    SystemInitializeRequest,
    SystemStatusResponse,
    TokenResponse,
    UpdatePreferencesRequest,
    UpdateUserRequest,
    UserListResponse,
    UserModel,
    UserResponse,
    UserStatus,
)
from core.user.service import (
    InvalidCredentialsError,
    InvalidUserStatusError,
    IPBlockedError,
    UserExistsError,
    UserNotFoundError,
    UserService,
    user_service,
)

__all__ = [
    # Models
    "UserModel",
    "UserStatus",
    "UserResponse",
    "UserListResponse",
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UpdateUserRequest",
    "UpdatePreferencesRequest",
    "SystemInitializeRequest",
    "SystemStatusResponse",
    "ApproveUserRequest",
    "RejectUserRequest",
    "DisableUserRequest",
    "RequestPasswordResetRequest",
    "ResetPasswordRequest",
    "AdminResetPasswordRequest",
    # Service
    "UserService",
    "user_service",
    # Exceptions
    "UserExistsError",
    "InvalidCredentialsError",
    "IPBlockedError",
    "UserNotFoundError",
    "InvalidUserStatusError",
    # Dependencies
    "get_current_user_optional",
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "get_current_admin_user",
    "get_current_super_admin",
    "get_db",
]
