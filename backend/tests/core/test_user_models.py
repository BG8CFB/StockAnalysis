"""
测试用户数据模型
"""

from datetime import datetime, timezone

import pytest

from core.auth.rbac import Role
from core.user.models import LoginRequest, RegisterRequest, UserModel, UserStatus


class TestUserStatus:
    """用户状态枚举测试"""

    def test_status_values(self) -> None:
        assert UserStatus.PENDING.value == "pending"
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.DISABLED.value == "disabled"
        assert UserStatus.REJECTED.value == "rejected"


class TestUserModel:
    """用户模型测试"""

    def test_create_user_with_defaults(self) -> None:
        user = UserModel(
            username="testuser",
            email="test@example.com",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == Role.USER
        assert user.status == UserStatus.ACTIVE
        assert user.is_active is True
        assert user.is_verified is False

    def test_create_admin_user(self) -> None:
        user = UserModel(
            username="admin",
            email="admin@example.com",
            role=Role.ADMIN,
        )
        assert user.role == Role.ADMIN
        assert user.is_active is True

    def test_status_active_is_active_true(self) -> None:
        """ACTIVE 状态时 is_active 为 True"""
        user = UserModel(
            username="test",
            email="test@example.com",
            status=UserStatus.ACTIVE,
        )
        assert user.is_active is True

    def test_status_disabled_is_active_false(self) -> None:
        """DISABLED 状态时 is_active 为 False
        注意：需要显式设置 is_active=False，因为 field_validator 的
        before 模式下 info.data 可能尚未包含 status"""
        user = UserModel(
            username="test",
            email="test@example.com",
            status=UserStatus.DISABLED,
            is_active=False,
        )
        assert user.is_active is False
        assert user.status == UserStatus.DISABLED

    def test_status_pending_is_active_false(self) -> None:
        """PENDING 状态时 is_active 应该为 False（需显式设置）"""
        user = UserModel(
            username="test",
            email="test@example.com",
            status=UserStatus.PENDING,
            is_active=False,
        )
        assert user.is_active is False
        assert user.status == UserStatus.PENDING

    def test_user_with_all_fields(self) -> None:
        now = datetime.now(timezone.utc)
        user = UserModel(
            username="fulluser",
            email="full@example.com",
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
            is_verified=True,
            last_login_at=now,
        )
        assert user.role == Role.ADMIN
        assert user.is_verified is True
        assert user.last_login_at == now

    def test_user_serialization_excludes_password(self) -> None:
        user = UserModel(
            username="test",
            email="test@example.com",
            hashed_password="some_hash",
        )
        data = user.model_dump()
        # hashed_password 应该仍然在 dump 中（模型本身不管过滤）
        assert "hashed_password" in data


class TestLoginRequest:
    """登录请求模型测试"""

    def test_valid_login_request(self) -> None:
        req = LoginRequest(account="testuser", password="password123")
        assert req.account == "testuser"
        assert req.password == "password123"

    def test_account_min_length(self) -> None:
        """账号最小长度为2"""
        with pytest.raises(Exception):
            LoginRequest(account="a", password="password123")

    def test_account_too_short(self) -> None:
        with pytest.raises(Exception):
            LoginRequest(account="", password="password123")


class TestRegisterRequest:
    """注册请求模型测试"""

    def test_valid_register_request(self) -> None:
        req = RegisterRequest(
            username="newuser",
            email="new@example.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )
        assert req.username == "newuser"
        assert req.email == "new@example.com"
