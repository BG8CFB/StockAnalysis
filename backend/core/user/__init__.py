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
    CaptchaGenerateResponse,
    CaptchaRequiredResponse,
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
    CaptchaRequiredError,
    InvalidCredentialsError,
    InvalidUserStatusError,
    IPBlockedError,
    UserExistsError,
    UserNotFoundError,
    UserService,
    user_service,
)
from core.user.settings_service import (
    get_user_settings_service,
    UserSettingsService,
)
from core.user.settings_api import router as settings_router

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
    "CaptchaGenerateResponse",
    "CaptchaRequiredResponse",
    # Service
    "UserService",
    "user_service",
    # Settings
    "UserSettingsService",
    "get_user_settings_service",
    "settings_router",
    # Exceptions
    "UserExistsError",
    "InvalidCredentialsError",
    "CaptchaRequiredError",
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
