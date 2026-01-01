"""
核心配置管理
使用 Pydantic Settings 进行类型安全的配置管理
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基础配置
    APP_NAME: str = "股票分析平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"

    # API 配置
    API_V1_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS 配置 - 接受字符串或列表类型
    CORS_ORIGINS: str | list[str] = "http://localhost:5173,http://localhost:3000"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # JWT 配置
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production-min-32-chars"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MongoDB 配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "stock_analysis"
    MONGODB_MAX_POOL_SIZE: int = 10
    MONGODB_MIN_POOL_SIZE: int = 1
    MONGODB_MAX_IDLE_TIME_MS: int = 10000
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 30000  # 增加到 30 秒
    MONGODB_SOCKET_TIMEOUT_MS: int = 60000  # 增加到 60 秒

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50  # 增加连接池大小
    REDIS_SOCKET_TIMEOUT: int = 10  # 增加超时时间到 10 秒
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 10  # 增加连接超时到 10 秒

    # 安全配置
    PASSWORD_MIN_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12

    # 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD_SECONDS: int = 60

    # 登录安全配置
    LOGIN_MAX_ATTEMPTS: int = 5  # 最大失败次数
    LOGIN_BLOCK_DURATION: int = 1800  # 封禁时长（秒）30分钟
    LOGIN_FAIL_WINDOW: int = 300  # 失败计数窗口（秒）5分钟

    # IP 信任配置
    IP_TRUST_THRESHOLD: int = 5  # 成功登录次数阈值
    IP_TRUST_EXPIRE_DAYS: int = 30  # 信任记录过期天数

    # 图形验证码配置
    CAPTCHA_ENABLED: bool = True
    CAPTCHA_EXPIRE_SECONDS: int = 300  # 验证码过期时间（秒）
    CAPTCHA_TOLERANCE: int = 5  # 滑动误差范围（像素）
    CAPTCHA_RATE_LIMIT: int = 10  # 生成频率限制（次/分钟）

    # 邮箱验证码配置
    EMAIL_CODE_ENABLED: bool = False  # 是否启用邮箱验证
    EMAIL_CODE_LENGTH: int = 6  # 验证码长度
    EMAIL_CODE_EXPIRE_SECONDS: int = 300  # 验证码过期时间（秒）
    EMAIL_CODE_COOLDOWN: int = 60  # 发送冷却时间（秒）
    EMAIL_CODE_RATE_LIMIT: int = 1  # 发送频率限制（次/分钟）

    # 注册安全配置
    REGISTER_MAX_ATTEMPTS: int = 3  # 每小时最大注册次数（按IP）
    REGISTER_WINDOW_SECONDS: int = 3600  # 注册计数窗口（秒）

    # 用户审核配置
    REQUIRE_APPROVAL: bool = True  # 是否需要管理员审核新注册用户

    @property
    def cors_origins_list(self) -> list[str]:
        """获取 CORS origins 列表"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.ENVIRONMENT == "testing"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
