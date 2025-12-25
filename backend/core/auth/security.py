"""
安全工具：JWT 和密码处理
"""
from datetime import datetime, timedelta
from typing import Optional
import logging

import bcrypt
from jose import JWTError, jwt

from core.config import settings

# 设置日志
logger = logging.getLogger(__name__)

class PasswordManager:
    """密码管理器"""

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        # bcrypt 限制密码最大72字节，需要截断超长密码
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]

        # 使用 bcrypt 生成哈希，使用配置中的 rounds
        salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        plain_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)


class JWTManager:
    """JWT 令牌管理器"""

    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        # 使用系统本地时间（自动适配容器时区）
        now = datetime.now().astimezone()
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        logger.debug(f"Creating access token. Now: {now}, Expire: {expire}, TZ: {now.tzinfo}")
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        # 使用系统本地时间（自动适配容器时区）
        now = datetime.now().astimezone()
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            
        logger.debug(f"Creating refresh token. Now: {now}, Expire: {expire}, TZ: {now.tzinfo}")
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """解码令牌"""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.warning(f"Token decode failed: {str(e)}")
            return None

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
        """验证令牌"""
        payload = JWTManager.decode_token(token)
        if payload is None:
            return None
        if payload.get("type") != token_type:
            logger.warning(f"Token type mismatch. Expected {token_type}, got {payload.get('type')}")
            return None
        return payload


# 全局实例
password_manager = PasswordManager()
jwt_manager = JWTManager()
