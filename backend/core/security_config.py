"""
安全配置模块
提供敏感信息的安全验证和处理
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SecurityConfig:
    """安全配置管理器"""

    @staticmethod
    def get_jwt_secret_key() -> str:
        """
        获取JWT密钥

        安全规则：
        1. 生产环境必须从环境变量读取
        2. 开发环境可以使用默认值，但必须记录警告
        3. 密钥长度必须足够安全
        """
        secret_key = os.getenv("SECRET_KEY")
        environment = os.getenv("ENVIRONMENT", "development")

        if not secret_key:
            if environment == "production":
                error_msg = "SECRET_KEY must be set in production environment"
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                # 开发环境使用默认值，但记录严重警告
                logger.warning(
                    "⚠️  SECURITY WARNING: Using default JWT secret key for development. "
                    "This is INSECURE for production! "
                    "Please set SECRET_KEY environment variable for production use."
                )
                return "development-secret-key-only-for-testing"

        # 验证密钥长度
        if len(secret_key) < 32:
            logger.warning(
                f"JWT secret key length ({len(secret_key)}) may be insufficient for production"
            )

        return secret_key

    @staticmethod
    def get_api_key(service_name: str, required_in_production: bool = True) -> Optional[str]:
        """
        安全地获取API密钥

        Args:
            service_name: 服务名称，用于构建环境变量名
            required_in_production: 生产环境是否必须配置

        Returns:
            API密钥，如果未配置且不需要则返回None
        """
        # 构建环境变量名，例如：ZHIPU_API_KEY, TUSHARE_API_KEY
        env_var_name = f"{service_name.upper()}_API_KEY"
        api_key = os.getenv(env_var_name)
        environment = os.getenv("ENVIRONMENT", "development")

        if not api_key:
            if required_in_production and environment == "production":
                error_msg = f"{env_var_name} must be set in production environment"
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                logger.warning(f"{env_var_name} not set. Some features may be unavailable.")
                return None

        # 记录配置状态但不暴露实际值
        logger.info(f"{service_name} API key configured (length: {len(api_key)})")
        return api_key

    @staticmethod
    def validate_production_config() -> None:
        """验证生产环境配置"""
        required_vars = {
            "SECRET_KEY": "JWT签名密钥",
            "MONGODB_URL": "MongoDB连接地址",
            "REDIS_URL": "Redis连接地址",
            "CORS_ORIGINS": "允许的跨域源",
        }

        environment = os.getenv("ENVIRONMENT", "development")
        if environment != "production":
            logger.info("Development environment detected. Skipping production config validation.")
            return

        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")

        if missing_vars:
            error_msg = "Production environment missing required configuration:\n" + "\n".join(
                missing_vars
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Production configuration validation passed.")

    @staticmethod
    def get_safe_test_credentials() -> dict:
        """
        获取安全的测试凭证

        返回：
            从环境变量读取的测试凭证，或安全的默认值
        """
        environment = os.getenv("ENVIRONMENT", "development")

        # 从环境变量读取，如果没有则使用安全的默认值
        credentials = {
            "username": os.getenv("TEST_ADMIN_USERNAME", "test_admin"),
            "password": os.getenv("TEST_ADMIN_PASSWORD", "test_password_123"),
            "email": os.getenv("TEST_ADMIN_EMAIL", "test_admin@example.com"),
        }

        if environment == "production":
            # 生产环境下，测试凭证必须从环境变量读取
            for key, value in credentials.items():
                if value.startswith("test_"):
                    error_msg = (
                        f"Test credentials must be properly configured in production. "
                        f"Missing: {key}"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

        return credentials
