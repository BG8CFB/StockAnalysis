from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm

from core.user.service import UserService, UserExistsError, InvalidCredentialsError, IPBlockedError, CaptchaRequiredError, InvalidUserStatusError
from core.user.models import (
    UserModel, LoginRequest, RegisterRequest, TokenResponse,
    RequestPasswordResetRequest, ResetPasswordRequest,
    CaptchaGenerateRequest, CaptchaGenerateResponse, CaptchaVerifyRequest
)
from core.user.dependencies import get_current_user, get_current_active_user
from core.auth.security import jwt_manager
from core.config import settings
from core.security.captcha_service import get_captcha_service

router = APIRouter(tags=["用户管理"])
user_service = UserService()
captcha_service = get_captcha_service()

@router.post("/users/register", response_model=UserModel)
async def register(request: Request, data: RegisterRequest):
    """用户注册"""
    try:
        # 获取客户端 IP
        client_ip = request.client.host
        user = await user_service.register(data, client_ip)
        return user
    except UserExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或邮箱已存在"
        )
    except IPBlockedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前IP暂时无法注册"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

import logging

# ...

logger = logging.getLogger(__name__)

@router.post("/users/login", response_model=TokenResponse)
async def login(request: Request, data: LoginRequest):
    """用户登录 - 支持用户名或邮箱"""
    logger.info(f"Login request received for account: {data.account}")
    try:
        client_ip = request.client.host
        user, access_token, refresh_token = await user_service.login(data, client_ip)

        logger.info(f"Login success for account: {data.account}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except InvalidUserStatusError as e:
        # 用户状态问题:返回 403 Forbidden (比 401 更准确)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except IPBlockedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前IP已被封禁"
        )
    except CaptchaRequiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请完成图形验证码",
            headers={"X-Captcha-Required": "true"}
        )
    except InvalidCredentialsError:
        # 只有真正的账号密码错误才返回 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名、邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/users/captcha/generate", response_model=CaptchaGenerateResponse)
async def generate_captcha_post(request: CaptchaGenerateRequest):
    """生成验证码（POST方式）"""
    try:
        captcha = await captcha_service.generate_captcha()
        return captcha
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成验证码失败: {str(e)}"
        )

@router.get("/users/captcha/generate", response_model=CaptchaGenerateResponse)
async def generate_captcha(action: str = "login"):
    """生成验证码（GET方式）"""
    try:
        captcha = await captcha_service.generate_captcha()
        return captcha
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成验证码失败: {str(e)}"
        )

@router.post("/users/captcha/verify")
async def verify_captcha(request: CaptchaVerifyRequest):
    """验证验证码"""
    try:
        is_valid = await captcha_service.verify_captcha(
            request.token,
            request.slide_x,
            request.slide_y
        )
        return {"valid": is_valid}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证码验证失败: {str(e)}"
        )

@router.get("/users/captcha/required")
async def check_captcha_required(account: str):
    """检查是否需要验证码"""
    try:
        required, reason = await user_service.check_captcha_required(account, "")
        return {"required": required, "reason": reason}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查验证码状态失败: {str(e)}"
        )

@router.get("/users/me", response_model=UserModel)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.put("/users/me", response_model=UserModel)
async def update_users_me(
    data: dict,
    current_user: UserModel = Depends(get_current_active_user),
):
    """更新当前用户信息"""
    try:
        updated_user = await user_service.update_user(str(current_user.id), data)
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户信息失败: {str(e)}"
        )

@router.get("/users/me/preferences")
async def get_user_preferences(current_user: UserModel = Depends(get_current_active_user)):
    """获取当前用户配置（主题、语言等）"""
    try:
        preferences = await user_service.get_preferences(str(current_user.id))
        return preferences
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户配置失败: {str(e)}"
        )

@router.put("/users/me/preferences")
async def update_user_preferences(
    preferences: dict,
    current_user: UserModel = Depends(get_current_active_user)
):
    """更新当前用户配置（主题、语言等）"""
    try:
        updated = await user_service.update_preferences(str(current_user.id), preferences)
        return updated
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户配置失败: {str(e)}"
        )

@router.post("/users/request-reset")
async def request_password_reset(
    request: Request,
    data: RequestPasswordResetRequest
):
    """用户请求密码重置"""
    try:
        client_ip = request.client.host
        reset_token = await user_service.request_password_reset(
            data.email,
            client_ip,
            data.captcha_token,
            data.slide_x,
            data.slide_y
        )
        return {"success": True, "token": reset_token}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"请求密码重置失败: {str(e)}"
        )

@router.post("/users/reset-password")
async def reset_password(data: ResetPasswordRequest):
    """使用 token 重置密码"""
    try:
        success = await user_service.reset_password(
            data.token,
            data.new_password
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码重置失败: {str(e)}"
        )

@router.post("/users/refresh-token", response_model=TokenResponse)
async def refresh_token(data: dict):
    """刷新访问令牌"""
    import time
    start_time = time.time()
    logger.info(f"Token refresh request received")
    try:
        refresh_token_value = data.get("refresh_token")
        if not refresh_token_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="refresh_token 是必填项"
            )
        
        access_token, new_refresh_token = await user_service.refresh_access_token(refresh_token_value)
        elapsed_time = time.time() - start_time
        logger.info(f"Token refresh success, elapsed: {elapsed_time:.2f}s")
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    except ValueError as e:
        elapsed_time = time.time() - start_time
        logger.warning(f"Token refresh failed (ValueError): {str(e)}, elapsed: {elapsed_time:.2f}s")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Token refresh failed (Exception): {str(e)}, elapsed: {elapsed_time:.2f}s", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刷新令牌失败: {str(e)}"
        )

@router.post("/users/logout")
async def logout(request: Request, current_user: UserModel = Depends(get_current_active_user)):
    """用户登出"""
    try:
        # 从 Authorization header 获取 access_token
        authorization = request.headers.get("Authorization")
        access_token = None
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization.split(" ")[1]

        await user_service.logout(str(current_user.id), access_token or "")
        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登出失败: {str(e)}"
        )
