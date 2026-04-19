"""
测试安全模块：密码管理和 JWT 令牌管理
"""

from datetime import timedelta

import pytest

from core.auth.security import JWTManager, PasswordManager


class TestPasswordManager:
    """密码管理器测试"""

    def test_hash_password_returns_bcrypt_hash(self) -> None:
        """测试密码哈希生成"""
        hashed = PasswordManager.hash_password("test123")
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60

    def test_hash_password_different_salts(self) -> None:
        """测试相同密码产生不同哈希"""
        hash1 = PasswordManager.hash_password("same_password")
        hash2 = PasswordManager.hash_password("same_password")
        assert hash1 != hash2

    def test_verify_password_correct(self) -> None:
        """测试正确密码验证"""
        hashed = PasswordManager.hash_password("correct_password")
        assert PasswordManager.verify_password("correct_password", hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """测试错误密码验证"""
        hashed = PasswordManager.hash_password("correct_password")
        assert PasswordManager.verify_password("wrong_password", hashed) is False

    def test_verify_password_empty_hash(self) -> None:
        """测试空哈希不崩溃"""
        assert PasswordManager.verify_password("test", "") is False

    def test_verify_password_invalid_hash(self) -> None:
        """测试无效哈希不崩溃"""
        assert PasswordManager.verify_password("test", "not_a_hash") is False

    def test_hash_password_too_long(self) -> None:
        """测试过长密码被拒绝"""
        long_password = "a" * 73
        with pytest.raises(ValueError, match="密码过长"):
            PasswordManager.hash_password(long_password)

    def test_hash_password_max_length(self) -> None:
        """测试最大长度密码被接受（72字节）"""
        max_password = "a" * 72
        hashed = PasswordManager.hash_password(max_password)
        assert PasswordManager.verify_password(max_password, hashed) is True


class TestJWTManager:
    """JWT 令牌管理器测试"""

    def test_create_access_token(self) -> None:
        """测试创建访问令牌"""
        data = {"sub": "user123", "user_id": "uid456"}
        token = JWTManager.create_access_token(data)
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_create_access_token_with_expiry(self) -> None:
        """测试自定义过期时间的访问令牌"""
        data = {"sub": "user123"}
        token = JWTManager.create_access_token(data, expires_delta=timedelta(minutes=60))
        payload = JWTManager.decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_create_refresh_token(self) -> None:
        """测试创建刷新令牌"""
        data = {"sub": "user123"}
        token = JWTManager.create_refresh_token(data)
        payload = JWTManager.decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_decode_valid_token(self) -> None:
        """测试解码有效令牌"""
        data = {"sub": "user123", "user_id": "uid456"}
        token = JWTManager.create_access_token(data)
        payload = JWTManager.decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["user_id"] == "uid456"
        assert "exp" in payload

    def test_decode_invalid_token(self) -> None:
        """测试解码无效令牌"""
        payload = JWTManager.decode_token("invalid.token.here")
        assert payload is None

    def test_decode_tampered_token(self) -> None:
        """测试解码篡改的令牌"""
        token = JWTManager.create_access_token({"sub": "user123"})
        tampered = token[:-5] + "xxxxx"
        payload = JWTManager.decode_token(tampered)
        assert payload is None

    def test_verify_access_token_type(self) -> None:
        """测试验证访问令牌类型"""
        data = {"sub": "user123"}
        token = JWTManager.create_access_token(data)
        payload = JWTManager.verify_token(token, "access")
        assert payload is not None
        assert payload["sub"] == "user123"

    def test_verify_token_type_mismatch(self) -> None:
        """测试令牌类型不匹配"""
        data = {"sub": "user123"}
        # 创建访问令牌但期望刷新令牌
        token = JWTManager.create_access_token(data)
        payload = JWTManager.verify_token(token, "refresh")
        assert payload is None

    def test_verify_refresh_token_type(self) -> None:
        """测试验证刷新令牌类型"""
        data = {"sub": "user123"}
        token = JWTManager.create_refresh_token(data)
        payload = JWTManager.verify_token(token, "refresh")
        assert payload is not None
        assert payload["type"] == "refresh"
