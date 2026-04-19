"""
测试应用配置模块
"""

from core import config


class TestConfig:
    """配置加载测试"""

    def test_mongodb_url_exists(self) -> None:
        assert config.MONGODB_URL is not None
        assert "mongodb" in config.MONGODB_URL

    def test_database_name_exists(self) -> None:
        assert config.DATABASE_NAME is not None
        assert len(config.DATABASE_NAME) > 0

    def test_redis_url_exists(self) -> None:
        assert config.REDIS_URL is not None
        assert "redis" in config.REDIS_URL

    def test_secret_key_sufficient_length(self) -> None:
        assert len(config.SECRET_KEY) >= 32

    def test_algorithm_default(self) -> None:
        assert config.ALGORITHM == "HS256"

    def test_token_expiry_positive(self) -> None:
        assert config.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert config.REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_bcrypt_rounds_reasonable(self) -> None:
        assert 4 <= config.BCRYPT_ROUNDS <= 20

    def test_password_min_length(self) -> None:
        assert config.PASSWORD_MIN_LENGTH >= 6

    def test_login_security_config(self) -> None:
        assert config.LOGIN_MAX_ATTEMPTS > 0
        assert config.LOGIN_BLOCK_DURATION > 0
        assert config.LOGIN_FAIL_WINDOW > 0
