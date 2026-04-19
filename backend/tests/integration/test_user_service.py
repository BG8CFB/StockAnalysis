"""
用户服务集成测试 - 使用真实 MongoDB + Redis

测试用户注册、登录、CRUD 等完整业务流程
"""

import time

import pytest

from core.auth.rbac import Role
from core.auth.security import password_manager
from core.user.models import (
    LoginRequest,
    RegisterRequest,
    UpdateUserRequest,
    UserStatus,
)
from core.user.service import InvalidCredentialsError, UserExistsError, UserService

_ts = str(int(time.time()))[-6:]


@pytest.fixture
def service() -> UserService:
    return UserService()


@pytest.fixture
def register_data() -> RegisterRequest:
    return RegisterRequest(
        username=f"test_integ_{_ts}",
        email=f"test_integ_{_ts}@example.com",
        password="TestPass123!",
        confirm_password="TestPass123!",
    )


class TestUserRegistration:
    """用户注册集成测试"""

    @pytest.mark.asyncio
    async def test_register_new_user(
        self, service: UserService, register_data: RegisterRequest
    ) -> None:
        """测试注册新用户"""
        user = await service.register(register_data, client_ip="127.0.0.1")
        assert user is not None
        assert user.username == f"test_integ_{_ts}"
        assert user.email == f"test_integ_{_ts}@example.com"
        assert user.status == UserStatus.PENDING  # REQUIRE_APPROVAL=true
        assert user.role == Role.USER

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, service: UserService, register_data: RegisterRequest
    ) -> None:
        """测试重复用户名注册"""
        await service.register(register_data, client_ip="127.0.0.1")
        with pytest.raises(UserExistsError):
            await service.register(register_data, client_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_password_is_hashed(self, service: UserService) -> None:
        """测试密码被正确哈希"""
        data = RegisterRequest(
            username=f"test_hash_{_ts}",
            email=f"test_hash_{_ts}@example.com",
            password="MySecret123!",
            confirm_password="MySecret123!",
        )
        user = await service.register(data, client_ip="127.0.0.1")
        assert user.hashed_password != "MySecret123!"
        assert password_manager.verify_password("MySecret123!", user.hashed_password)  # type: ignore[arg-type]


class TestUserLogin:
    """用户登录集成测试"""

    @pytest.mark.asyncio
    async def test_login_with_username(self, service: UserService) -> None:
        """测试用户名登录"""
        data = RegisterRequest(
            username=f"test_login_{_ts}",
            email=f"test_login_{_ts}@example.com",
            password="LoginPass123!",
            confirm_password="LoginPass123!",
        )
        await service.register(data, client_ip="127.0.0.1")

        # 激活用户
        from core.db.mongodb import mongodb

        await mongodb.database.users.update_one(
            {"username": f"test_login_{_ts}"},
            {"$set": {"status": UserStatus.ACTIVE.value, "is_active": True}},
        )

        # 登录
        login_req = LoginRequest(account=f"test_login_{_ts}", password="LoginPass123!")
        user, access_token, refresh_token = await service.login(login_req, "127.0.0.1")
        assert user is not None
        assert access_token is not None
        assert refresh_token is not None

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, service: UserService) -> None:
        """测试错误密码登录"""
        data = RegisterRequest(
            username=f"test_wrong_{_ts}",
            email=f"test_wrong_{_ts}@example.com",
            password="CorrectPass123!",
            confirm_password="CorrectPass123!",
        )
        await service.register(data, client_ip="127.0.0.1")
        from core.db.mongodb import mongodb

        await mongodb.database.users.update_one(
            {"username": f"test_wrong_{_ts}"},
            {"$set": {"status": UserStatus.ACTIVE.value, "is_active": True}},
        )

        login_req = LoginRequest(account=f"test_wrong_{_ts}", password="WrongPass123!")
        with pytest.raises(InvalidCredentialsError):
            await service.login(login_req, "127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_pending_user_fails(self, service: UserService) -> None:
        """测试待审核用户无法登录"""
        data = RegisterRequest(
            username=f"test_pending_{_ts}",
            email=f"test_pending_{_ts}@example.com",
            password="PendingPass123!",
            confirm_password="PendingPass123!",
        )
        await service.register(data, client_ip="127.0.0.1")

        login_req = LoginRequest(account=f"test_pending_{_ts}", password="PendingPass123!")
        with pytest.raises(Exception):
            await service.login(login_req, "127.0.0.1")


class TestUserCRUD:
    """用户 CRUD 集成测试"""

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, service: UserService) -> None:
        """测试通过 ID 获取用户"""
        data = RegisterRequest(
            username=f"test_get_{_ts}",
            email=f"test_get_{_ts}@example.com",
            password="GetPass123!",
            confirm_password="GetPass123!",
        )
        user = await service.register(data, client_ip="127.0.0.1")
        fetched = await service.get_user(str(user.id))
        assert fetched is not None
        assert fetched.username == f"test_get_{_ts}"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, service: UserService) -> None:
        """测试获取不存在的用户"""
        from bson import ObjectId

        fetched = await service.get_user(str(ObjectId()))
        assert fetched is None

    @pytest.mark.asyncio
    async def test_update_user(self, service: UserService) -> None:
        """测试更新用户信息"""
        data = RegisterRequest(
            username=f"test_update_{_ts}",
            email=f"test_update_{_ts}@example.com",
            password="UpdatePass123!",
            confirm_password="UpdatePass123!",
        )
        user = await service.register(data, client_ip="127.0.0.1")
        update_req = UpdateUserRequest(email=f"updated_{_ts}@test.com")  # type: ignore[call-arg]
        updated = await service.update_user(str(user.id), update_req)
        assert updated is not None
        assert updated.email == f"updated_{_ts}@test.com"


class TestIsEmail:
    """邮箱格式验证测试（纯逻辑，不需要数据库）"""

    def test_valid_email(self) -> None:
        assert UserService._is_email("user@example.com") is True

    def test_valid_email_with_dots(self) -> None:
        assert UserService._is_email("first.last@sub.domain.com") is True

    def test_username_not_email(self) -> None:
        assert UserService._is_email("testuser") is False

    def test_numeric_not_email(self) -> None:
        assert UserService._is_email("12345") is False

    def test_empty_not_email(self) -> None:
        assert UserService._is_email("") is False
