"""
用户核心业务逻辑服务
集成验证码、限流、IP信任管理、审核工作流、密码重置
"""
import json
import secrets
from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from core.auth.security import jwt_manager, password_manager
from core.auth.rbac import Role
from core.config import settings
from core.db.mongodb import mongodb
from core.db.redis import UserRedisKey, get_redis
from core.security.captcha_service import get_captcha_service
from core.security.ip_trust import get_ip_trust_manager
from core.security.rate_limiter import (
    RateLimitConfig,
    get_rate_limiter,
)
from core.user.models import (
    LoginRequest,
    RegisterRequest,
    UpdatePreferencesRequest,
    UpdateUserRequest,
    UserModel,
    UserStatus,
)

# ==================== 异常类 ====================


class UserExistsError(Exception):
    """用户已存在错误"""
    pass


class InvalidCredentialsError(Exception):
    """无效凭证错误 - 账号密码错误或Token无效"""
    pass


class InvalidUserStatusError(Exception):
    """用户状态无效 - 账号待审核/已禁用/已拒绝"""
    pass


class CaptchaRequiredError(Exception):
    """需要验证码"""
    pass


class IPBlockedError(Exception):
    """IP 已被封禁"""
    pass


class UserNotFoundError(Exception):
    """用户不存在"""
    pass


class InvalidUserStatusError(Exception):
    """用户状态无效"""
    pass


# ==================== 用户服务 ====================


class UserService:
    """用户核心服务"""

    def __init__(self) -> None:
        self.rate_limiter = get_rate_limiter()
        self.ip_trust = get_ip_trust_manager()
        self.captcha = get_captcha_service()

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """获取数据库实例（延迟加载）"""
        return mongodb.database

    # ==================== 注册 ====================

    async def register(
        self,
        data: RegisterRequest,
        client_ip: str,
        captcha_token: Optional[str] = None,
        slide_x: Optional[int] = None,
        slide_y: Optional[int] = None,
    ) -> UserModel:
        """注册新用户（带验证码和限流）"""
        # 1. 检查 IP 注册频率限制
        rate_key = f"register:{client_ip}"
        allowed, retry_after = await self.rate_limiter.is_allowed(
            rate_key,
            RateLimitConfig.REGISTER_ATTEMPTS,
            RateLimitConfig.REGISTER_WINDOW,
        )
        if not allowed:
            raise ValueError(f"注册请求过于频繁，请 {retry_after} 秒后再试")

        # 2. 验证图形验证码（DEBUG 模式下跳过）
        if settings.CAPTCHA_ENABLED and not settings.DEBUG:
            if not captcha_token or slide_x is None or slide_y is None:
                raise ValueError("请完成图形验证码")
            if not await self.captcha.verify_captcha(captcha_token, slide_x, slide_y):
                raise ValueError("验证码验证失败")

        # 3. 检查用户是否已存在
        existing = await self.db.users.find_one({"email": data.email})
        if existing:
            raise UserExistsError("该邮箱已被注册")

        # 4. 根据配置决定初始状态
        initial_status = UserStatus.ACTIVE if not settings.REQUIRE_APPROVAL else UserStatus.PENDING

        # 5. 创建用户
        hashed_password = password_manager.hash_password(data.password)
        user_doc = {
            "email": data.email,
            "username": data.username,
            "hashed_password": hashed_password,
            "role": Role.USER,
            "status": initial_status,
            "is_active": initial_status == UserStatus.ACTIVE,
            "is_verified": False,
            "created_by": None,
            "last_login_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        try:
            result = await self.db.users.insert_one(user_doc)
            user_doc["_id"] = result.inserted_id
        except DuplicateKeyError:
            raise UserExistsError("该邮箱已被注册")

        # 6. 创建默认用户配置
        preferences_doc = {
            "user_id": result.inserted_id,
            "theme": "light",
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "watchlist": [],
            "notification_enabled": True,
            "email_alerts": False,
        }
        await self.db.user_preferences.insert_one(preferences_doc)

        # 7. 记录审计日志
        await self._create_audit_log(
            action="create",
            target_user_id=str(result.inserted_id),
            user_id=str(result.inserted_id),
        )

        # 使用 model_validate 处理 MongoDB 返回的字典（Pydantic v2 推荐方式）
        return UserModel.model_validate(user_doc)

    # ==================== 登录 ====================

    async def check_captcha_required(self, email: str, client_ip: str) -> tuple[bool, Optional[str]]:
        """检查是否需要验证码

        Returns:
            (是否需要验证码, 原因)
        """
        # 1. 检查 IP 是否被封禁
        redis = await get_redis()
        blocked_key = UserRedisKey.login_blocked_ip(client_ip)
        is_blocked = await redis.get(blocked_key)
        if is_blocked:
            raise IPBlockedError("该 IP 因多次登录失败已被临时封禁")

        # 2. 检查 IP 失败次数
        failures_key = UserRedisKey.login_failures_ip(client_ip)
        ip_failures = await redis.get(failures_key)
        ip_failures = int(ip_failures) if ip_failures else 0

        # 3. 检查邮箱失败次数
        email_failures_key = UserRedisKey.login_failures_email(email)
        email_failures = await redis.get(email_failures_key)
        email_failures = int(email_failures) if email_failures else 0

        # 4. 查询用户，检查是否为信任 IP
        user = await self.db.users.find_one({"email": email})
        if user:
            user_id = str(user["_id"])
            is_trusted = await self.ip_trust.is_ip_trusted(user_id, client_ip)
            if is_trusted and ip_failures < 3:
                # 信任 IP 且失败次数少，无需验证码
                return False, None

        # 5. 根据失败次数决定是否需要验证码
        max_failures = settings.LOGIN_MAX_ATTEMPTS
        if ip_failures >= 3 or email_failures >= 3:
            return True, "登录失败次数过多，请完成验证码后继续"
        if ip_failures >= max_failures or email_failures >= max_failures:
            return True, "登录已被临时锁定，请完成验证码"

        return False, None

    async def login(
        self,
        data: LoginRequest,
        client_ip: str,
        captcha_token: Optional[str] = None,
        slide_x: Optional[int] = None,
        slide_y: Optional[int] = None,
    ) -> tuple[UserModel, str, str]:
        """用户登录（带验证码和限流）"""
        redis = await get_redis()

        # 1. 检查 IP 封禁状态
        blocked_key = UserRedisKey.login_blocked_ip(client_ip)
        is_blocked = await redis.get(blocked_key)
        if is_blocked:
            remaining = int(is_blocked)
            raise IPBlockedError(f"该 IP 因多次登录失败已被临时封禁，剩余 {remaining} 秒")

        # 2. 获取失败次数
        failures_key = UserRedisKey.login_failures_ip(client_ip)
        ip_failures = await redis.get(failures_key)
        ip_failures = int(ip_failures) if ip_failures else 0

        # 3. 检查是否需要验证码
        user = await self.db.users.find_one({"email": data.email})
        needs_captcha = False

        if user:
            user_id = str(user["_id"])
            is_trusted = await self.ip_trust.is_ip_trusted(user_id, client_ip)
            if not is_trusted and ip_failures >= 3:
                needs_captcha = True
        elif ip_failures >= 3:
            needs_captcha = True

        # 4. 验证验证码（如果需要，DEBUG 模式下跳过）
        if (needs_captcha or captcha_token) and not settings.DEBUG:
            if settings.CAPTCHA_ENABLED:
                if not captcha_token or slide_x is None or slide_y is None:
                    raise CaptchaRequiredError("请完成图形验证码")
                if not await self.captcha.verify_captcha(captcha_token, slide_x, slide_y):
                    await self._record_login_failure(data.email, client_ip)
                    raise InvalidCredentialsError("验证码验证失败")

        # 5. 验证用户凭证
        if not user:
            await self._record_login_failure(data.email, client_ip)
            raise InvalidCredentialsError("邮箱或密码错误")

        if not password_manager.verify_password(data.password, user["hashed_password"]):
            await self._record_login_failure(data.email, client_ip)
            raise InvalidCredentialsError("邮箱或密码错误")

        # 8. ❗️ 检查用户状态 (根据不同情况抛出不同异常)
        user_status = user.get("status", UserStatus.ACTIVE)
        
        # 8.1 用户状态检查
        if user_status == UserStatus.PENDING:
            raise InvalidUserStatusError("账号待审核，请等待管理员审核")
        if user_status == UserStatus.DISABLED:
            raise InvalidUserStatusError("账号已被禁用")
        if user_status == UserStatus.REJECTED:
            raise InvalidUserStatusError("账号已被拒绝")
        
        # 8.2 is_active 字段检查
        if not user.get("is_active", True):
            raise InvalidCredentialsError("账号已被禁用")

        # 7. 登录成功，清除失败记录
        await self._clear_login_failures(data.email, client_ip)

        # 8. 记录 IP 信任
        user_id = str(user["_id"])
        await self.ip_trust.record_login_success(user_id, client_ip)

        # 9. 更新最后登录时间
        await self.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login_at": datetime.utcnow()}}
        )
        user["last_login_at"] = datetime.utcnow()
        # 使用 model_validate 处理 MongoDB 返回的字典（Pydantic v2 推荐方式）
        user_model = UserModel.model_validate(user)

        # 10. 生成令牌（包含角色信息）
        token_data = {"sub": str(user_model.id), "role": user_model.role}
        access_token = jwt_manager.create_access_token(token_data)
        refresh_token = jwt_manager.create_refresh_token(token_data)

        # 11. 缓存会话到 Redis
        session_key = UserRedisKey.session(str(user_model.id), access_token[:16])
        await redis.set(
            session_key,
            str(user_model.id),
            ex=1800,  # 30分钟
        )

        # 12. 记录登录审计日志
        await self._create_audit_log(
            action="login",
            user_id=str(user_model.id),
            ip_address=client_ip,
        )

        return user_model, access_token, refresh_token

    async def _record_login_failure(self, email: str, client_ip: str) -> None:
        """记录登录失败"""
        redis = await get_redis()

        # 增加 IP 失败计数
        ip_key = UserRedisKey.login_failures_ip(client_ip)
        ip_failures = await redis.incr(ip_key)
        await redis.expire(ip_key, settings.LOGIN_FAIL_WINDOW)

        # 增加邮箱失败计数
        email_key = UserRedisKey.login_failures_email(email)
        await redis.incr(email_key)
        await redis.expire(email_key, settings.LOGIN_FAIL_WINDOW)

        # 检查是否需要封禁
        if ip_failures >= settings.LOGIN_MAX_ATTEMPTS:
            blocked_key = UserRedisKey.login_blocked_ip(client_ip)
            await redis.set(blocked_key, settings.LOGIN_BLOCK_DURATION, ex=settings.LOGIN_BLOCK_DURATION)

    async def _clear_login_failures(self, email: str, client_ip: str) -> None:
        """清除登录失败记录"""
        redis = await get_redis()
        await redis.delete(UserRedisKey.login_failures_ip(client_ip))
        await redis.delete(UserRedisKey.login_failures_email(email))

    # ==================== 用户信息 ====================

    async def get_user(self, user_id: str) -> Optional[UserModel]:
        """获取用户信息"""
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None
        # 使用 model_validate 处理 MongoDB 返回的字典（Pydantic v2 推荐方式）
        return UserModel.model_validate(user)

    async def update_user(self, user_id: str, data: UpdateUserRequest) -> Optional[UserModel]:
        """更新用户信息"""
        update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        if not update_data:
            return await self.get_user(user_id)

        update_data["updated_at"] = datetime.utcnow()

        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
        )
        return await self.get_user(user_id)

    # ==================== 用户配置 ====================

    async def get_preferences(self, user_id: str) -> dict:
        """获取用户配置"""
        # 先从 Redis 缓存获取
        redis = await get_redis()
        cache_key = UserRedisKey.preferences(user_id)
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 从数据库获取
        prefs = await self.db.user_preferences.find_one({"user_id": ObjectId(user_id)})
        if not prefs:
            # 返回默认配置
            return {
                "theme": "light",
                "language": "zh-CN",
                "timezone": "Asia/Shanghai",
                "watchlist": [],
                "notification_enabled": True,
                "email_alerts": False,
            }

        prefs.pop("_id", None)
        prefs.pop("user_id", None)

        # 缓存到 Redis
        await redis.set(cache_key, json.dumps(prefs, default=str), ex=3600)  # 1小时

        return prefs

    async def update_preferences(
        self, user_id: str, data: UpdatePreferencesRequest | dict
    ) -> dict:
        """更新用户配置"""
        # 处理dict输入
        if isinstance(data, dict):
            update_data = {k: v for k, v in data.items() if v is not None}
        else:
            update_data = {
                k: v
                for k, v in data.model_dump(exclude_unset=True).items()
                if v is not None
            }

        if not update_data:
            return await self.get_preferences(user_id)

        # 更新数据库
        await self.db.user_preferences.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": update_data},
            upsert=True,
        )

        # 清除缓存
        redis = await get_redis()
        cache_key = UserRedisKey.preferences(user_id)
        await redis.delete(cache_key)

        return await self.get_preferences(user_id)

    async def logout(self, user_id: str, access_token: str) -> None:
        """用户登出"""
        redis = await get_redis()
        session_key = UserRedisKey.session(user_id, access_token[:16])
        await redis.delete(session_key)

        # 记录登出审计日志
        await self._create_audit_log(
            action="logout",
            user_id=user_id,
        )

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """使用 refresh_token 刷新 access_token

        Returns:
            (access_token, new_refresh_token)
        """
        # 1. 验证 refresh_token
        try:
            token_data = jwt_manager.verify_token(refresh_token, token_type="refresh")
        except Exception:
            raise ValueError("无效的 refresh_token")

        user_id = token_data.get("sub")
        if not user_id:
            raise ValueError("无效的 refresh_token")

        # 2. 检查用户是否存在且状态正常
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")

        user_status = user.get("status", UserStatus.ACTIVE)
        if user_status != UserStatus.ACTIVE:
            raise ValueError("用户状态异常，无法刷新令牌")

        if not user.get("is_active", True):
            raise ValueError("用户已被禁用")

        # 3. 生成新的令牌
        access_token = jwt_manager.create_access_token(token_data)
        new_refresh_token = jwt_manager.create_refresh_token(token_data)

        return access_token, new_refresh_token

    # ==================== 密码重置 ====================

    async def request_password_reset(
        self,
        email: str,
        client_ip: str,
        captcha_token: Optional[str] = None,
        slide_x: Optional[int] = None,
        slide_y: Optional[int] = None,
    ) -> str:
        """请求密码重置，生成 token

        Returns:
            reset_token: 重置令牌
        """
        # 1. 验证验证码（DEBUG 模式下跳过）
        if settings.CAPTCHA_ENABLED and not settings.DEBUG:
            if not captcha_token or slide_x is None or slide_y is None:
                raise ValueError("请完成图形验证码")
            if not await self.captcha.verify_captcha(captcha_token, slide_x, slide_y):
                raise ValueError("验证码验证失败")

        # 2. 查找用户
        user = await self.db.users.find_one({"email": email})
        if not user:
            # 为了安全，不暴露用户是否存在
            return "ok"

        # 3. 生成重置 token
        reset_token = secrets.token_urlsafe(32)
        token_key = f"password_reset:{reset_token}"

        # 4. 存储到 Redis（1小时有效期）
        redis = await get_redis()
        await redis.set(
            token_key,
            json.dumps({"user_id": str(user["_id"])}),
            ex=3600,
        )

        # 5. 开发环境：打印到控制台
        if settings.DEBUG:
            print(f"[Password Reset] Email: {email}, Token: {reset_token}")
            print(f"Reset URL: http://localhost:5173/reset-password?token={reset_token}")

        # TODO: 生产环境发送邮件

        return reset_token

    async def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> bool:
        """使用 token 重置密码"""
        redis = await get_redis()
        token_key = f"password_reset:{token}"

        # 1. 验证 token
        token_data = await redis.get(token_key)
        if not token_data:
            raise ValueError("重置链接无效或已过期")

        data = json.loads(token_data)
        user_id = data["user_id"]

        # 2. 获取用户
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("用户不存在")

        # 3. 更新密码
        hashed_password = password_manager.hash_password(new_password)
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "hashed_password": hashed_password,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        # 4. 删除 token（一次性使用）
        await redis.delete(token_key)

        # 5. 清除所有会话
        session_pattern = f"user:{user_id}:session:*"
        # Redis 不支持通配符删除，需要用 scan
        async for key in redis.scan_iter(match=f"user:{user_id}:session:*"):
            await redis.delete(key)

        # 6. 记录审计日志
        await self._create_audit_log(
            action="password_reset",
            target_user_id=user_id,
            user_id=user_id,
        )

        return True

    # ==================== 审计日志 ====================

    async def _create_audit_log(
        self,
        action: str,
        user_id: str,
        target_user_id: Optional[str] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """创建审计日志"""
        log_doc = {
            "user_id": ObjectId(user_id),
            "target_user_id": ObjectId(target_user_id) if target_user_id else None,
            "action": action,
            "reason": reason,
            "ip_address": ip_address,
            "created_at": datetime.utcnow(),
        }
        await self.db.audit_logs.insert_one(log_doc)

    async def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[dict]:
        """获取审计日志"""
        query = {}
        if action:
            query["action"] = action
        if user_id:
            query["user_id"] = ObjectId(user_id)

        cursor = (
            self.db.audit_logs
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        logs = []
        async for log in cursor:
            log["id"] = str(log.pop("_id"))
            log["user_id"] = str(log["user_id"])
            if log.get("target_user_id"):
                log["target_user_id"] = str(log["target_user_id"])
            logs.append(log)

        return logs


# 全局服务实例
user_service = UserService()
