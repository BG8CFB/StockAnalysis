"""
集成测试 conftest - 使用真实的 MongoDB 和 Redis 容器
"""

import sys
from typing import AsyncGenerator, Generator

import pytest

sys.path.insert(0, ".")


@pytest.fixture(scope="session", autouse=True)
def db_connections() -> Generator[None, None, None]:
    """连接到真实的 MongoDB 和 Redis（同步方法）"""
    from core.db.mongodb import mongodb
    from core.db.redis import redis_manager

    mongodb.connect()
    redis_manager.connect()
    yield
    mongodb.close()


@pytest.fixture(autouse=True)
async def cleanup_test_data() -> AsyncGenerator[None, None]:
    """每个测试前清理测试数据和限流状态"""
    from core.db.mongodb import mongodb

    # 清理已有测试用户
    try:
        await mongodb.database.users.delete_many({"username": {"$regex": "^test_"}})
    except Exception:
        pass

    # 清理限流器状态
    try:
        from core.security.rate_limiter import _local_rate_limit_store

        _local_rate_limit_store.clear()
    except Exception:
        pass

    yield

    # 测试后也清理
    try:
        await mongodb.database.users.delete_many({"username": {"$regex": "^test_"}})
    except Exception:
        pass

    try:
        from core.security.rate_limiter import _local_rate_limit_store

        _local_rate_limit_store.clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def bypass_rate_limiter() -> Generator[None, None, None]:
    """绕过限流器"""
    from unittest.mock import AsyncMock, patch

    with patch(
        "core.security.rate_limiter.RateLimiter.is_allowed",
        new_callable=AsyncMock,
        return_value=(True, 0),
    ):
        yield
