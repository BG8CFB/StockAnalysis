"""
测试配置和共享 fixtures
"""

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, ".")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建 session 级别的事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongodb() -> Generator[MagicMock, None, None]:
    """模拟 MongoDB 数据库"""
    with patch("core.db.mongodb.mongodb") as mock:
        mock.get_collection.return_value = MagicMock()
        mock.get_database.return_value = MagicMock()
        mock.client = MagicMock()
        yield mock


@pytest.fixture
def mock_redis() -> Generator[AsyncMock, None, None]:
    """模拟 Redis"""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.scan_iter = AsyncMock(return_value=[])
    with patch("core.db.redis.get_redis", return_value=redis_mock):
        yield redis_mock


@pytest.fixture
def mock_user() -> Any:
    """模拟已认证用户"""
    from core.user.models import UserModel

    now = datetime.now(timezone.utc)
    return UserModel(
        username="testuser",
        email="test@test.com",
        hashed_password="hashed",
        is_active=True,
        is_verified=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_admin_user() -> Any:
    """模拟管理员用户"""
    from core.auth.rbac import Role
    from core.user.models import UserModel

    now = datetime.now(timezone.utc)
    return UserModel(
        username="admin",
        email="admin@test.com",
        hashed_password="hashed",
        role=Role.ADMIN,
        is_active=True,
        is_verified=True,
        created_at=now,
        updated_at=now,
    )
