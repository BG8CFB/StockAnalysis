"""
用户服务 (UserService) 单元测试

覆盖范围：
- 用户注册（密码哈希、校验、重复检查）
- 用户登录（凭证验证、令牌生成、失败记录、IP 封禁）
- 用户 CRUD（查询、更新、唯一性校验）
- 密码重置（请求重置、使用 token 重置）
- 账户状态管理（状态检查、is_active 联动）
- 会话管理（登出、令牌刷新、偏好设置）
- 审计日志
"""

import json
from datetime import datetime, timezone
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from core.auth.rbac import Role
from core.user.models import (
    LoginRequest,
    RegisterRequest,
    UpdatePreferencesRequest,
    UpdateUserRequest,
    UserModel,
    UserStatus,
)
from core.user.service import (
    InvalidCredentialsError,
    InvalidUserStatusError,
    IPBlockedError,
    UserExistsError,
    UserService,
)

# ==================== 辅助工具 ====================


class _AsyncIter:
    """将普通列表包装为异步迭代器，供 `async for` 使用"""

    def __init__(self, items: Any) -> None:
        self._items = list(items)
        self._index = 0

    def __aiter__(self) -> "_AsyncIter":
        return self

    async def __anext__(self) -> Any:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


def async_iter(items: Any) -> _AsyncIter:
    """工厂函数：创建异步迭代器"""
    return _AsyncIter(items)


# ==================== Fixtures ====================


@pytest.fixture
def user_id() -> str:
    """生成测试用 ObjectId 字符串"""
    return str(ObjectId())


@pytest.fixture
def another_user_id() -> str:
    """生成另一个测试用 ObjectId 字符串"""
    return str(ObjectId())


@pytest.fixture
def sample_user_doc(user_id: str) -> dict:
    """构造一个标准的用户文档（模拟 MongoDB 返回）"""
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId(user_id),
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": "$2b$12$abcdefghijklmnopqrstuvwxABCDEFGHIJ1234567890abcdefghijklm",
        "role": Role.USER,
        "status": UserStatus.ACTIVE,
        "is_active": True,
        "is_verified": False,
        "created_by": None,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def sample_admin_doc() -> dict:
    """构造管理员用户文档"""
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId(),
        "email": "admin@example.com",
        "username": "admin",
        "hashed_password": "$2b$12$admin_hash_value_here_abcdefgHIJKLMN",
        "role": Role.ADMIN,
        "status": UserStatus.ACTIVE,
        "is_active": True,
        "is_verified": True,
        "created_by": None,
        "last_login_at": now,
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def mock_db() -> Generator[MagicMock, None, None]:
    """创建模拟的 MongoDB 数据库对象，包含 users / user_preferences / audit_logs 集合"""
    db = MagicMock()

    # users 集合
    users_col = AsyncMock()
    users_col.find_one = AsyncMock(return_value=None)
    users_col.insert_one = AsyncMock()
    users_col.update_one = AsyncMock()

    # user_preferences 集合
    prefs_col = AsyncMock()
    prefs_col.find_one = AsyncMock(return_value=None)
    prefs_col.insert_one = AsyncMock()
    prefs_col.update_one = AsyncMock()

    # audit_logs 集合
    audit_col = AsyncMock()
    audit_col.insert_one = AsyncMock()
    audit_col.find = MagicMock()

    db.users = users_col
    db.user_preferences = prefs_col
    db.audit_logs = audit_col

    return db


@pytest.fixture
def mock_redis() -> AsyncMock:
    """创建模拟的 Redis 客户端"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    # scan_iter 被 async for 使用，需要返回异步可迭代对象
    redis.scan_iter = MagicMock(return_value=async_iter([]))
    return redis


@pytest.fixture
def mock_rate_limiter() -> AsyncMock:
    """创建模拟的限流器"""
    limiter = AsyncMock()
    limiter.is_allowed = AsyncMock(return_value=(True, 0))
    return limiter


@pytest.fixture
def mock_ip_trust() -> AsyncMock:
    """创建模拟的 IP 信任管理器"""
    trust = AsyncMock()
    trust.record_login_success = AsyncMock()
    return trust


@pytest.fixture
def patched_service(
    mock_db: MagicMock,
    mock_redis: AsyncMock,
    mock_rate_limiter: AsyncMock,
    mock_ip_trust: AsyncMock,
) -> Generator[tuple[UserService, MagicMock, AsyncMock], None, None]:
    """
    创建注入了 mock 依赖的 UserService 实例。

    通过 patch 目标模块中的全局对象，使 UserService 的 db 属性和 get_redis()
    返回 mock 对象。
    """
    svc = UserService()
    svc.rate_limiter = mock_rate_limiter
    svc.ip_trust = mock_ip_trust

    with (
        patch("core.user.service.mongodb") as mock_mongodb,
        patch("core.user.service.get_redis", return_value=mock_redis),
    ):
        mock_mongodb.database = mock_db
        yield svc, mock_db, mock_redis


# ==================== 辅助方法 ====================


class TestIsEmail:
    """测试 _is_email 静态方法"""

    def test_valid_email(self) -> None:
        assert UserService._is_email("user@example.com") is True

    def test_valid_email_with_dots(self) -> None:
        assert UserService._is_email("first.last@sub.domain.com") is True

    def test_valid_email_with_plus(self) -> None:
        assert UserService._is_email("user+tag@example.com") is True

    def test_username_not_email(self) -> None:
        assert UserService._is_email("testuser") is False

    def test_numeric_string_not_email(self) -> None:
        assert UserService._is_email("12345") is False

    def test_empty_string_not_email(self) -> None:
        assert UserService._is_email("") is False

    def test_partial_email_not_valid(self) -> None:
        assert UserService._is_email("user@") is False

    def test_no_tld_not_valid(self) -> None:
        assert UserService._is_email("user@domain") is False


class TestFindUserByAccount:
    """测试 _find_user_by_account 方法"""

    @pytest.mark.asyncio
    async def test_find_by_email(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, _ = patched_service
        email = "test@example.com"
        expected_doc = {"_id": ObjectId(), "email": email, "username": "testuser"}
        mock_db.users.find_one = AsyncMock(return_value=expected_doc)

        result = await service._find_user_by_account(email)
        assert result == expected_doc
        mock_db.users.find_one.assert_called_once_with({"email": email})

    @pytest.mark.asyncio
    async def test_find_by_username(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, _ = patched_service
        username = "testuser"
        expected_doc = {"_id": ObjectId(), "email": "test@example.com", "username": username}
        mock_db.users.find_one = AsyncMock(return_value=expected_doc)

        result = await service._find_user_by_account(username)
        assert result == expected_doc
        mock_db.users.find_one.assert_called_once_with({"username": username})

    @pytest.mark.asyncio
    async def test_find_nonexistent_user(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, _ = patched_service
        mock_db.users.find_one = AsyncMock(return_value=None)
        result = await service._find_user_by_account("nonexistent")
        assert result is None


# ==================== 注册测试 ====================


class TestRegister:
    """用户注册测试"""

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        data = RegisterRequest(
            email="new@example.com",
            username="newuser",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )
        inserted_id = ObjectId(user_id)
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id=inserted_id))

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.settings") as mock_settings,
        ):
            mock_pw.hash_password = MagicMock(return_value="$2b$12$hashed_password_value")
            mock_settings.REQUIRE_APPROVAL = False
            user = await service.register(data, client_ip="127.0.0.1")

        assert isinstance(user, UserModel)
        assert user.email == "new@example.com"
        assert user.username == "newuser"
        assert user.role == Role.USER
        assert user.status == UserStatus.ACTIVE
        assert user.is_active is True
        assert user.is_verified is False

        # 验证创建了默认偏好
        mock_db.user_preferences.insert_one.assert_called_once()
        # 验证创建了审计日志
        mock_db.audit_logs.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_password_is_hashed(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        data = RegisterRequest(
            email="hash@example.com",
            username="hashtest",
            password="MyPassword123!",
            confirm_password="MyPassword123!",
        )
        inserted_id = ObjectId(user_id)
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id=inserted_id))

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.hash_password = MagicMock(return_value="$2b$12$hashed_pwd")
            await service.register(data, client_ip="127.0.0.1")
            mock_pw.hash_password.assert_called_once_with("MyPassword123!")

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, _ = patched_service
        data = RegisterRequest(
            email="existing@example.com",
            username="newuser",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )
        existing_doc = {"_id": ObjectId(), "email": "existing@example.com"}
        mock_db.users.find_one = AsyncMock(return_value=existing_doc)

        with pytest.raises(UserExistsError, match="邮箱已被注册"):
            await service.register(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, _ = patched_service
        data = RegisterRequest(
            email="new@example.com",
            username="existinguser",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )

        async def mock_find_one(query: Any) -> Any:
            if "email" in query:
                return None  # 邮箱不存在
            if "username" in query:
                return {"_id": ObjectId(), "username": "existinguser"}  # 用户名存在
            return None

        mock_db.users.find_one = mock_find_one

        with pytest.raises(UserExistsError, match="用户名已被使用"):
            await service.register(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_register_rate_limited(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, _ = patched_service
        data = RegisterRequest(
            email="rate@example.com",
            username="rateuser",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )
        service.rate_limiter.is_allowed = AsyncMock(return_value=(False, 60))  # type: ignore[method-assign]

        with pytest.raises(ValueError, match="注册请求过于频繁"):
            await service.register(data, client_ip="192.168.1.1")

    @pytest.mark.asyncio
    async def test_register_with_require_approval(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        data = RegisterRequest(
            email="pending@example.com",
            username="pendinguser",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )
        inserted_id = ObjectId(user_id)
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id=inserted_id))

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.settings") as mock_settings,
        ):
            mock_pw.hash_password = MagicMock(return_value="$2b$12$hashed_pwd")
            mock_settings.REQUIRE_APPROVAL = True
            user = await service.register(data, client_ip="127.0.0.1")

        assert user.status == UserStatus.PENDING
        assert user.is_active is False

    @pytest.mark.asyncio
    async def test_register_duplicate_key_error(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, _ = patched_service
        data = RegisterRequest(
            email="dup@example.com",
            username="dupuser",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )
        mock_db.users.find_one = AsyncMock(return_value=None)

        from pymongo.errors import DuplicateKeyError

        mock_db.users.insert_one = AsyncMock(side_effect=DuplicateKeyError("duplicate"))

        with (
            patch("core.user.service.password_manager") as mock_pw,
            pytest.raises(UserExistsError, match="邮箱已被注册"),
        ):
            mock_pw.hash_password = MagicMock(return_value="$2b$12$hashed_pwd")
            await service.register(data, client_ip="127.0.0.1")


# ==================== 登录测试 ====================


class TestLogin:
    """用户登录测试"""

    @pytest.mark.asyncio
    async def test_login_success_by_username(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.jwt_manager") as mock_jwt,
        ):
            mock_pw.verify_password = MagicMock(return_value=True)
            mock_jwt.create_access_token = MagicMock(return_value="access_token_123")
            mock_jwt.create_refresh_token = MagicMock(return_value="refresh_token_456")

            user_model, access_token, refresh_token = await service.login(
                data, client_ip="127.0.0.1"
            )

        assert isinstance(user_model, UserModel)
        assert access_token == "access_token_123"
        assert refresh_token == "refresh_token_456"

        # 验证更新了最后登录时间
        mock_db.users.update_one.assert_called_once()
        update_call_args = mock_db.users.update_one.call_args
        assert "$set" in update_call_args[0][1]
        assert "last_login_at" in update_call_args[0][1]["$set"]

        # 验证清除了登录失败记录
        assert mock_redis.delete.call_count >= 2

        # 验证记录了 IP 信任
        service.ip_trust.record_login_success.assert_called_once_with(user_id, "127.0.0.1")  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_login_success_by_email(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="test@example.com", password="password123")
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.jwt_manager") as mock_jwt,
        ):
            mock_pw.verify_password = MagicMock(return_value=True)
            mock_jwt.create_access_token = MagicMock(return_value="access_token")
            mock_jwt.create_refresh_token = MagicMock(return_value="refresh_token")

            user_model, at, rt = await service.login(data, client_ip="127.0.0.1")

        assert isinstance(user_model, UserModel)

    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="nouser", password="password123")
        mock_db.users.find_one = AsyncMock(return_value=None)

        with patch("core.user.service.password_manager"):
            with pytest.raises(InvalidCredentialsError, match="用户名或密码错误"):
                await service.login(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="wrongpassword")
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.verify_password = MagicMock(return_value=False)
            with pytest.raises(InvalidCredentialsError, match="用户名或密码错误"):
                await service.login(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_user_missing_password_field(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        user_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "username": "testuser",
            # 没有 hashed_password
            "role": Role.USER,
            "status": UserStatus.ACTIVE,
            "is_active": True,
        }
        mock_db.users.find_one = AsyncMock(return_value=user_doc)

        with patch("core.user.service.password_manager"):
            with pytest.raises(InvalidCredentialsError, match="账号数据异常"):
                await service.login(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_ip_blocked(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        mock_redis.get = AsyncMock(return_value="120")

        with pytest.raises(IPBlockedError, match="临时封禁"):
            await service.login(data, client_ip="10.0.0.1")

    @pytest.mark.asyncio
    async def test_login_pending_user(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        pending_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "$2b$12$hashed",
            "role": Role.USER,
            "status": UserStatus.PENDING,
            "is_active": False,
        }
        mock_db.users.find_one = AsyncMock(return_value=pending_doc)

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.verify_password = MagicMock(return_value=True)
            with pytest.raises(InvalidUserStatusError, match="待审核"):
                await service.login(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_disabled_user(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        disabled_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "$2b$12$hashed",
            "role": Role.USER,
            "status": UserStatus.DISABLED,
            "is_active": False,
        }
        mock_db.users.find_one = AsyncMock(return_value=disabled_doc)

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.verify_password = MagicMock(return_value=True)
            with pytest.raises(InvalidUserStatusError, match="已被禁用"):
                await service.login(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_rejected_user(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        rejected_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "$2b$12$hashed",
            "role": Role.USER,
            "status": UserStatus.REJECTED,
            "is_active": False,
        }
        mock_db.users.find_one = AsyncMock(return_value=rejected_doc)

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.verify_password = MagicMock(return_value=True)
            with pytest.raises(InvalidUserStatusError, match="已被拒绝"):
                await service.login(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        inactive_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "$2b$12$hashed",
            "role": Role.USER,
            "status": UserStatus.ACTIVE,
            "is_active": False,
        }
        mock_db.users.find_one = AsyncMock(return_value=inactive_doc)

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.verify_password = MagicMock(return_value=True)
            with pytest.raises(InvalidCredentialsError, match="已被禁用"):
                await service.login(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_session_cached_to_redis(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.jwt_manager") as mock_jwt,
        ):
            mock_pw.verify_password = MagicMock(return_value=True)
            mock_jwt.create_access_token = MagicMock(return_value="access_token_123")
            mock_jwt.create_refresh_token = MagicMock(return_value="refresh_token_456")

            await service.login(data, client_ip="127.0.0.1")

        # 验证 Redis.set 被调用（session 缓存）
        redis_set_calls = mock_redis.set.call_args_list
        assert len(redis_set_calls) >= 1
        session_call = redis_set_calls[0]
        session_key = session_call[0][0]
        assert session_key.startswith(f"user:{user_id}:session:")
        assert session_call[1].get("ex") == 1800  # 30分钟

    @pytest.mark.asyncio
    async def test_login_audit_log_created(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.jwt_manager") as mock_jwt,
        ):
            mock_pw.verify_password = MagicMock(return_value=True)
            mock_jwt.create_access_token = MagicMock(return_value="at")
            mock_jwt.create_refresh_token = MagicMock(return_value="rt")

            await service.login(data, client_ip="192.168.1.100")

        audit_call = mock_db.audit_logs.insert_one.call_args
        log_doc = audit_call[0][0]
        assert log_doc["action"] == "login"
        assert log_doc["ip_address"] == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_login_token_contains_role(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.jwt_manager") as mock_jwt,
        ):
            mock_pw.verify_password = MagicMock(return_value=True)
            mock_jwt.create_access_token = MagicMock(return_value="at")
            mock_jwt.create_refresh_token = MagicMock(return_value="rt")

            await service.login(data, client_ip="127.0.0.1")

        token_data_call = mock_jwt.create_access_token.call_args[0][0]
        assert "sub" in token_data_call
        assert "role" in token_data_call
        assert token_data_call["role"] == Role.USER


# ==================== 登录失败记录测试 ====================


class TestLoginFailureRecording:
    """登录失败记录与 IP 封禁测试"""

    @pytest.mark.asyncio
    async def test_record_login_failure_increments_counters(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, _, mock_redis = patched_service
        with patch("core.user.service.settings") as mock_settings:
            mock_settings.LOGIN_FAIL_WINDOW = 300
            mock_settings.LOGIN_MAX_ATTEMPTS = 5
            mock_settings.LOGIN_BLOCK_DURATION = 1800

            await service._record_login_failure("testuser", "10.0.0.1")

        assert mock_redis.incr.call_count == 2
        assert mock_redis.expire.call_count == 2

    @pytest.mark.asyncio
    async def test_record_login_failure_blocks_ip_after_max_attempts(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, _, mock_redis = patched_service
        mock_redis.incr = AsyncMock(return_value=5)  # 达到阈值

        with patch("core.user.service.settings") as mock_settings:
            mock_settings.LOGIN_FAIL_WINDOW = 300
            mock_settings.LOGIN_MAX_ATTEMPTS = 5
            mock_settings.LOGIN_BLOCK_DURATION = 1800

            await service._record_login_failure("testuser", "10.0.0.1")

        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_login_failure_no_block_below_threshold(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, _, mock_redis = patched_service
        mock_redis.incr = AsyncMock(return_value=3)  # 未达阈值

        with patch("core.user.service.settings") as mock_settings:
            mock_settings.LOGIN_FAIL_WINDOW = 300
            mock_settings.LOGIN_MAX_ATTEMPTS = 5
            mock_settings.LOGIN_BLOCK_DURATION = 1800

            await service._record_login_failure("testuser", "10.0.0.1")

        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_login_failures(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, _, mock_redis = patched_service
        await service._clear_login_failures("testuser", "10.0.0.1")
        assert mock_redis.delete.call_count == 2


# ==================== 用户 CRUD 测试 ====================


class TestGetUser:
    """获取用户信息测试"""

    @pytest.mark.asyncio
    async def test_get_user_success(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

        user = await service.get_user(user_id)
        assert isinstance(user, UserModel)
        assert user.email == "test@example.com"
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, _ = patched_service
        mock_db.users.find_one = AsyncMock(return_value=None)
        user = await service.get_user(str(ObjectId()))
        assert user is None


class TestUpdateUser:
    """更新用户信息测试"""

    @pytest.mark.asyncio
    async def test_update_username_success(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        updated_doc = {**sample_user_doc, "username": "newusername"}
        call_count = 0

        async def mock_find_one(query: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # 唯一性检查通过
            return updated_doc

        mock_db.users.find_one = mock_find_one
        mock_db.users.update_one = AsyncMock()

        data = UpdateUserRequest(username="newusername")
        result = await service.update_user(user_id, data)

        assert result is not None
        assert result.username == "newusername"

    @pytest.mark.asyncio
    async def test_update_email_success(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        updated_doc = {**sample_user_doc, "email": "newemail@example.com"}
        call_count = 0

        async def mock_find_one(query: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # 唯一性检查通过
            return updated_doc

        mock_db.users.find_one = mock_find_one
        mock_db.users.update_one = AsyncMock()

        data = UpdateUserRequest(email="newemail@example.com")  # type: ignore[call-arg]
        result = await service.update_user(user_id, data)

        assert result is not None
        assert result.email == "newemail@example.com"

    @pytest.mark.asyncio
    async def test_update_email_duplicate(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        existing_doc = {"_id": ObjectId(), "email": "taken@example.com"}
        mock_db.users.find_one = AsyncMock(return_value=existing_doc)

        data = UpdateUserRequest(email="taken@example.com")  # type: ignore[call-arg]
        with pytest.raises(ValueError, match="邮箱已被其他用户使用"):
            await service.update_user(user_id, data)

    @pytest.mark.asyncio
    async def test_update_username_duplicate(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service

        async def mock_find_one(query: Any) -> Any:
            if "email" in query:
                return None
            if "username" in query:
                return {"_id": ObjectId(), "username": "taken_username"}
            return None

        mock_db.users.find_one = mock_find_one

        data = UpdateUserRequest(username="taken_username")
        with pytest.raises(ValueError, match="用户名已被其他用户使用"):
            await service.update_user(user_id, data)

    @pytest.mark.asyncio
    async def test_update_with_empty_data_returns_current(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)
        data = UpdateUserRequest()  # type: ignore[call-arg]
        result = await service.update_user(user_id, data)
        assert result is not None
        mock_db.users.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_sets_updated_at(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        updated_doc = {**sample_user_doc, "username": "updated"}
        call_count = 0

        async def mock_find_one(query: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return updated_doc

        mock_db.users.find_one = mock_find_one
        mock_db.users.update_one = AsyncMock()

        data = UpdateUserRequest(username="updated")  # type: ignore[call-arg]
        await service.update_user(user_id, data)

        update_call = mock_db.users.update_one.call_args
        set_data = update_call[0][1]["$set"]
        assert "updated_at" in set_data


# ==================== 用户配置测试 ====================


class TestPreferences:
    """用户配置测试"""

    @pytest.mark.asyncio
    async def test_get_preferences_from_cache(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        cached_prefs = json.dumps(
            {
                "theme": "dark",
                "language": "en-US",
                "timezone": "UTC",
            }
        )
        mock_redis.get = AsyncMock(return_value=cached_prefs)

        result = await service.get_preferences(user_id)

        assert result["theme"] == "dark"
        assert result["language"] == "en-US"
        mock_db.user_preferences.find_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_preferences_from_database(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        mock_redis.get = AsyncMock(return_value=None)
        db_prefs = {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "theme": "light",
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "notification_enabled": True,
            "email_alerts": False,
        }
        mock_db.user_preferences.find_one = AsyncMock(return_value=db_prefs)

        result = await service.get_preferences(user_id)

        assert result["theme"] == "light"
        assert result["language"] == "zh-CN"
        assert "_id" not in result
        assert "user_id" not in result
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_preferences_default_when_no_record(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        mock_redis.get = AsyncMock(return_value=None)
        mock_db.user_preferences.find_one = AsyncMock(return_value=None)

        result = await service.get_preferences(user_id)

        assert result["theme"] == "light"
        assert result["language"] == "zh-CN"
        assert result["timezone"] == "Asia/Shanghai"
        assert result["notification_enabled"] is True
        assert result["email_alerts"] is False

    @pytest.mark.asyncio
    async def test_update_preferences_with_model(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        mock_redis.get = AsyncMock(return_value=None)
        updated_prefs = {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "theme": "dark",
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "notification_enabled": True,
            "email_alerts": True,
        }
        mock_db.user_preferences.find_one = AsyncMock(return_value=updated_prefs)
        mock_db.user_preferences.update_one = AsyncMock()

        data = UpdatePreferencesRequest(theme="dark", email_alerts=True)
        await service.update_preferences(user_id, data)

        mock_db.user_preferences.update_one.assert_called_once()
        update_call = mock_db.user_preferences.update_one.call_args
        assert update_call[1].get("upsert") is True
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_update_preferences_with_dict(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        mock_redis.get = AsyncMock(return_value=None)
        updated_prefs = {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "theme": "dark",
            "language": "en-US",
            "timezone": "UTC",
            "notification_enabled": False,
            "email_alerts": False,
        }
        mock_db.user_preferences.find_one = AsyncMock(return_value=updated_prefs)
        mock_db.user_preferences.update_one = AsyncMock()

        data = {"theme": "dark", "language": "en-US", "timezone": "UTC"}
        await service.update_preferences(user_id, data)

        mock_db.user_preferences.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_preferences_empty_data(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        mock_redis.get = AsyncMock(return_value=json.dumps({"theme": "light"}))

        data = UpdatePreferencesRequest()
        await service.update_preferences(user_id, data)

        mock_db.user_preferences.update_one.assert_not_called()


# ==================== 密码重置测试 ====================


class TestPasswordReset:
    """密码重置流程测试"""

    @pytest.mark.asyncio
    async def test_request_password_reset_existing_email(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        user_doc = {"_id": ObjectId(user_id), "email": "test@example.com"}
        mock_db.users.find_one = AsyncMock(return_value=user_doc)

        token = await service.request_password_reset("test@example.com", client_ip="127.0.0.1")

        assert isinstance(token, str)
        assert len(token) > 0

        mock_redis.set.assert_called_once()
        set_call = mock_redis.set.call_args
        token_key = set_call[0][0]
        assert token_key.startswith("password_reset:")
        assert set_call[1].get("ex") == 3600

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_email(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, mock_db, mock_redis = patched_service
        mock_db.users.find_one = AsyncMock(return_value=None)

        result = await service.request_password_reset(
            "nonexistent@example.com", client_ip="127.0.0.1"
        )

        assert result == "ok"
        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        token = "valid_reset_token_abc123"
        token_data = json.dumps({"user_id": user_id})

        mock_redis.get = AsyncMock(return_value=token_data)
        mock_redis.scan_iter = MagicMock(return_value=async_iter([]))

        user_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "$2b$12$old_hash",
            "role": Role.USER,
            "status": UserStatus.ACTIVE,
            "is_active": True,
        }
        mock_db.users.find_one = AsyncMock(return_value=user_doc)

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.hash_password = MagicMock(return_value="$2b$12$new_hash")
            result = await service.reset_password(token, "NewPassword123!")

        assert result is True

        mock_db.users.update_one.assert_called_once()
        update_call = mock_db.users.update_one.call_args
        set_data = update_call[0][1]["$set"]
        assert set_data["hashed_password"] == "$2b$12$new_hash"

        mock_redis.delete.assert_called()
        mock_db.audit_logs.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(
        self, patched_service: tuple[UserService, MagicMock, AsyncMock]
    ) -> None:
        service, _, mock_redis = patched_service
        mock_redis.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="重置链接无效或已过期"):
            await service.reset_password("invalid_token", "NewPassword123!")

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        token = "valid_token_but_user_gone"
        mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": user_id}))
        mock_db.users.find_one = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="用户不存在"):
            await service.reset_password(token, "NewPassword123!")

    @pytest.mark.asyncio
    async def test_reset_password_clears_sessions(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        token = "session_clear_token"
        mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": user_id}))
        session_keys = [
            f"user:{user_id}:session:abc",
            f"user:{user_id}:session:def",
        ]
        mock_redis.scan_iter = MagicMock(return_value=async_iter(session_keys))

        user_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "hashed_password": "$2b$12$old",
            "role": Role.USER,
            "status": UserStatus.ACTIVE,
            "is_active": True,
        }
        mock_db.users.find_one = AsyncMock(return_value=user_doc)

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.hash_password = MagicMock(return_value="$2b$12$new")
            await service.reset_password(token, "NewPassword123!")

        delete_calls = mock_redis.delete.call_args_list
        all_deleted_keys = [call[0][0] for call in delete_calls]
        for sk in session_keys:
            assert sk in all_deleted_keys


# ==================== 会话管理测试 ====================


class TestLogout:
    """用户登出测试"""

    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        await service.logout(user_id, "access_token_1234567890ab")

        mock_redis.delete.assert_called()
        delete_key = mock_redis.delete.call_args[0][0]
        assert delete_key.startswith(f"user:{user_id}:session:")

    @pytest.mark.asyncio
    async def test_logout_creates_audit_log(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        await service.logout(user_id, "some_token_value_here_xx")

        mock_db.audit_logs.insert_one.assert_called_once()
        log_doc = mock_db.audit_logs.insert_one.call_args[0][0]
        assert log_doc["action"] == "logout"
        assert str(log_doc["user_id"]) == user_id


class TestRefreshToken:
    """令牌刷新测试"""

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        with patch("core.user.service.jwt_manager") as mock_jwt:
            mock_jwt.verify_token = MagicMock(
                return_value={"sub": user_id, "role": Role.USER, "type": "refresh"}
            )
            mock_jwt.create_access_token = MagicMock(return_value="new_access_token")
            mock_jwt.create_refresh_token = MagicMock(return_value="new_refresh_token")

            mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

            access, refresh = await service.refresh_access_token("old_refresh_token")

        assert access == "new_access_token"
        assert refresh == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self) -> None:
        svc = UserService()
        with patch("core.user.service.jwt_manager") as mock_jwt:
            mock_jwt.verify_token = MagicMock(return_value=None)
            with pytest.raises(ValueError, match="无效的 refresh_token"):
                await svc.refresh_access_token("bad_token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_missing_sub(self) -> None:
        svc = UserService()
        with patch("core.user.service.jwt_manager") as mock_jwt:
            mock_jwt.verify_token = MagicMock(return_value={"role": Role.USER, "type": "refresh"})
            with pytest.raises(ValueError, match="无效的 refresh_token"):
                await svc.refresh_access_token("token_no_sub")

    @pytest.mark.asyncio
    async def test_refresh_access_token_verification_exception(self) -> None:
        svc = UserService()
        with patch("core.user.service.jwt_manager") as mock_jwt:
            mock_jwt.verify_token = MagicMock(side_effect=Exception("decode error"))
            with pytest.raises(ValueError, match="无效的 refresh_token"):
                await svc.refresh_access_token("corrupt_token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_user_not_found(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        with patch("core.user.service.jwt_manager") as mock_jwt:
            mock_jwt.verify_token = MagicMock(return_value={"sub": user_id, "type": "refresh"})
            mock_db.users.find_one = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="用户不存在"):
                await service.refresh_access_token("valid_but_user_gone")

    @pytest.mark.asyncio
    async def test_refresh_access_token_user_disabled(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        disabled_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "$2b$12$hash",
            "role": Role.USER,
            "status": UserStatus.DISABLED,
            "is_active": False,
        }
        with patch("core.user.service.jwt_manager") as mock_jwt:
            mock_jwt.verify_token = MagicMock(return_value={"sub": user_id, "type": "refresh"})
            mock_db.users.find_one = AsyncMock(return_value=disabled_doc)

            with pytest.raises(ValueError, match="用户状态异常"):
                await service.refresh_access_token("disabled_user_token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_user_inactive(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        inactive_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "username": "testuser",
            "hashed_password": "$2b$12$hash",
            "role": Role.USER,
            "status": UserStatus.ACTIVE,
            "is_active": False,
        }
        with patch("core.user.service.jwt_manager") as mock_jwt:
            mock_jwt.verify_token = MagicMock(return_value={"sub": user_id, "type": "refresh"})
            mock_db.users.find_one = AsyncMock(return_value=inactive_doc)

            with pytest.raises(ValueError, match="用户已被禁用"):
                await service.refresh_access_token("inactive_user_token")


# ==================== 审计日志测试 ====================


class TestAuditLogs:
    """审计日志测试"""

    @pytest.mark.asyncio
    async def test_create_audit_log(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        await service._create_audit_log(
            action="create",
            user_id=user_id,
            target_user_id=user_id,
        )

        mock_db.audit_logs.insert_one.assert_called_once()
        log_doc = mock_db.audit_logs.insert_one.call_args[0][0]
        assert log_doc["action"] == "create"
        assert str(log_doc["user_id"]) == user_id
        assert log_doc["target_user_id"] is not None

    @pytest.mark.asyncio
    async def test_create_audit_log_with_ip(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        await service._create_audit_log(
            action="login",
            user_id=user_id,
            ip_address="192.168.1.1",
        )

        log_doc = mock_db.audit_logs.insert_one.call_args[0][0]
        assert log_doc["ip_address"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_create_audit_log_with_reason(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        admin_id = str(ObjectId())  # 使用合法的 ObjectId 格式
        await service._create_audit_log(
            action="disable",
            user_id=admin_id,
            target_user_id=user_id,
            reason="违反规定",
        )

        log_doc = mock_db.audit_logs.insert_one.call_args[0][0]
        assert log_doc["reason"] == "违反规定"

    @pytest.mark.asyncio
    async def test_get_audit_logs(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        log1 = {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "action": "login",
            "created_at": datetime.now(timezone.utc),
        }
        # 构造异步 cursor 模拟
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.__aiter__ = MagicMock(return_value=async_iter([log1]))

        mock_db.audit_logs.find = MagicMock(return_value=mock_cursor)

        logs = await service.get_audit_logs(skip=0, limit=10)

        assert len(logs) == 1
        assert logs[0]["action"] == "login"

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.__aiter__ = MagicMock(return_value=async_iter([]))

        mock_db.audit_logs.find = MagicMock(return_value=mock_cursor)

        await service.get_audit_logs(action="login", user_id=user_id)

        find_call_args = mock_db.audit_logs.find.call_args[0][0]
        assert find_call_args["action"] == "login"
        assert find_call_args["user_id"] == ObjectId(user_id)


# ==================== 账户状态综合测试 ====================


class TestAccountStatusIntegration:
    """账户状态管理综合测试"""

    @pytest.mark.asyncio
    async def test_full_status_lifecycle(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        active_doc = {
            "_id": ObjectId(user_id),
            "email": "lifecycle@example.com",
            "username": "lifecycle_user",
            "hashed_password": "$2b$12$hashed",
            "role": Role.USER,
            "status": UserStatus.ACTIVE,
            "is_active": True,
            "is_verified": False,
            "created_at": now,
            "updated_at": now,
        }
        user = UserModel.model_validate(active_doc)
        assert user.is_active is True
        assert user.status == UserStatus.ACTIVE

        disabled_doc = {**active_doc, "status": UserStatus.DISABLED, "is_active": False}
        user_disabled = UserModel.model_validate(disabled_doc)
        assert user_disabled.is_active is False

        reactivated_doc = {**active_doc, "status": UserStatus.ACTIVE, "is_active": True}
        user_reactivated = UserModel.model_validate(reactivated_doc)
        assert user_reactivated.is_active is True

    @pytest.mark.asyncio
    async def test_all_status_transitions_affect_login(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service

        statuses_and_errors = [
            (UserStatus.PENDING, InvalidUserStatusError, "待审核"),
            (UserStatus.DISABLED, InvalidUserStatusError, "已被禁用"),
            (UserStatus.REJECTED, InvalidUserStatusError, "已被拒绝"),
        ]

        for status_val, expected_error, expected_msg in statuses_and_errors:
            doc = {
                "_id": ObjectId(user_id),
                "email": "statustest@example.com",
                "username": "statustest",
                "hashed_password": "$2b$12$hashed",
                "role": Role.USER,
                "status": status_val,
                "is_active": status_val == UserStatus.ACTIVE,
            }
            mock_db.users.find_one = AsyncMock(return_value=doc)

            data = LoginRequest(account="statustest", password="password123")

            with patch("core.user.service.password_manager") as mock_pw:
                mock_pw.verify_password = MagicMock(return_value=True)
                with pytest.raises(expected_error, match=expected_msg):
                    await service.login(data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_admin_role_in_token(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_admin_doc: dict,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="admin@example.com", password="adminpass")
        mock_db.users.find_one = AsyncMock(return_value=sample_admin_doc)

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.jwt_manager") as mock_jwt,
        ):
            mock_pw.verify_password = MagicMock(return_value=True)
            mock_jwt.create_access_token = MagicMock(return_value="admin_at")
            mock_jwt.create_refresh_token = MagicMock(return_value="admin_rt")

            _, _, _ = await service.login(data, client_ip="127.0.0.1")

        token_data = mock_jwt.create_access_token.call_args[0][0]
        assert token_data["role"] == Role.ADMIN


# ==================== 边界条件与异常测试 ====================


class TestEdgeCases:
    """边界条件与异常处理测试"""

    @pytest.mark.asyncio
    async def test_login_failure_then_success_clears_failures(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        data = LoginRequest(account="testuser", password="password123")
        mock_db.users.find_one = AsyncMock(return_value=sample_user_doc)

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.jwt_manager") as mock_jwt,
        ):
            mock_pw.verify_password = MagicMock(return_value=True)
            mock_jwt.create_access_token = MagicMock(return_value="at")
            mock_jwt.create_refresh_token = MagicMock(return_value="rt")

            await service.login(data, client_ip="127.0.0.1")

        delete_calls = mock_redis.delete.call_args_list
        assert len(delete_calls) >= 2

    @pytest.mark.asyncio
    async def test_update_user_preserves_other_fields(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        sample_user_doc: dict,
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        updated_doc = {**sample_user_doc, "email": "updated@example.com"}
        call_count = 0

        async def mock_find_one(query: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return updated_doc

        mock_db.users.find_one = mock_find_one
        mock_db.users.update_one = AsyncMock()

        data = UpdateUserRequest(email="updated@example.com")  # type: ignore[call-arg]
        result = await service.update_user(user_id, data)

        assert result is not None
        assert result.username == "testuser"
        assert result.role == Role.USER

    @pytest.mark.asyncio
    async def test_password_reset_token_one_time_use(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        token = "one_time_token"
        token_data = json.dumps({"user_id": user_id})

        mock_redis.get = AsyncMock(return_value=token_data)
        user_doc = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "hashed_password": "$2b$12$old",
            "role": Role.USER,
            "status": UserStatus.ACTIVE,
            "is_active": True,
        }
        mock_db.users.find_one = AsyncMock(return_value=user_doc)

        with patch("core.user.service.password_manager") as mock_pw:
            mock_pw.hash_password = MagicMock(return_value="$2b$12$new")
            await service.reset_password(token, "NewPassword123!")

        delete_calls = [call[0][0] for call in mock_redis.delete.call_args_list]
        assert f"password_reset:{token}" in delete_calls

    @pytest.mark.asyncio
    async def test_register_creates_default_preferences(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, _ = patched_service
        data = RegisterRequest(
            email="prefs@example.com",
            username="prefuser",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )
        inserted_id = ObjectId(user_id)
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id=inserted_id))

        with (
            patch("core.user.service.password_manager") as mock_pw,
            patch("core.user.service.settings") as mock_settings,
        ):
            mock_pw.hash_password = MagicMock(return_value="$2b$12$hashed")
            mock_settings.REQUIRE_APPROVAL = False
            await service.register(data, client_ip="127.0.0.1")

        prefs_call = mock_db.user_preferences.insert_one.call_args
        prefs_doc = prefs_call[0][0]
        assert prefs_doc["theme"] == "light"
        assert prefs_doc["language"] == "zh-CN"
        assert prefs_doc["timezone"] == "Asia/Shanghai"
        assert prefs_doc["watchlist"] == []
        assert prefs_doc["notification_enabled"] is True
        assert prefs_doc["email_alerts"] is False

    @pytest.mark.asyncio
    async def test_get_preferences_cache_hit_avoids_db(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        cached = json.dumps({"theme": "dark"})
        mock_redis.get = AsyncMock(return_value=cached)

        result = await service.get_preferences(user_id)

        assert result["theme"] == "dark"
        mock_db.user_preferences.find_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_preferences_clears_cache(
        self,
        patched_service: tuple[UserService, MagicMock, AsyncMock],
        user_id: str,
    ) -> None:
        service, mock_db, mock_redis = patched_service
        mock_redis.get = AsyncMock(return_value=None)
        mock_db.user_preferences.find_one = AsyncMock(
            return_value={
                "_id": ObjectId(),
                "user_id": ObjectId(user_id),
                "theme": "dark",
            }
        )
        mock_db.user_preferences.update_one = AsyncMock()

        data = UpdatePreferencesRequest(theme="dark")
        await service.update_preferences(user_id, data)

        cache_key = f"user:{user_id}:preferences"
        mock_redis.delete.assert_any_call(cache_key)
