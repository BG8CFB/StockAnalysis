"""
应用配置

从环境变量加载配置
"""
import os
from pathlib import Path
from typing import Optional

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库配置
MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME: str = os.getenv("DATABASE_NAME", "stock_analysis")
MONGODB_DATABASE: str = DATABASE_NAME  # 别名
MONGODB_MAX_POOL_SIZE: int = int(os.getenv("MONGODB_MAX_POOL_SIZE", "100"))
MONGODB_MIN_POOL_SIZE: int = int(os.getenv("MONGODB_MIN_POOL_SIZE", "10"))
MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "30000"))
MONGODB_SOCKET_TIMEOUT_MS: int = int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "60000"))

# Redis配置
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
REDIS_SOCKET_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
REDIS_SOCKET_CONNECT_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))

# JWT配置
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# 密码安全
PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

# 登录安全配置
LOGIN_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_BLOCK_DURATION: int = int(os.getenv("LOGIN_BLOCK_DURATION", "1800"))
LOGIN_FAIL_WINDOW: int = int(os.getenv("LOGIN_FAIL_WINDOW", "300"))

# IP 信任配置
IP_TRUST_THRESHOLD: int = int(os.getenv("IP_TRUST_THRESHOLD", "5"))
IP_TRUST_EXPIRE_DAYS: int = int(os.getenv("IP_TRUST_EXPIRE_DAYS", "30"))

# 图形验证码配置
CAPTCHA_ENABLED: bool = os.getenv("CAPTCHA_ENABLED", "true").lower() == "true"
CAPTCHA_EXPIRE_SECONDS: int = int(os.getenv("CAPTCHA_EXPIRE_SECONDS", "300"))
CAPTCHA_TOLERANCE: int = int(os.getenv("CAPTCHA_TOLERANCE", "5"))
CAPTCHA_RATE_LIMIT: int = int(os.getenv("CAPTCHA_RATE_LIMIT", "10"))

# 邮箱验证码配置（预留）
EMAIL_CODE_ENABLED: bool = os.getenv("EMAIL_CODE_ENABLED", "false").lower() == "true"
EMAIL_CODE_LENGTH: int = int(os.getenv("EMAIL_CODE_LENGTH", "6"))
EMAIL_CODE_EXPIRE_SECONDS: int = int(os.getenv("EMAIL_CODE_EXPIRE_SECONDS", "300"))
EMAIL_CODE_COOLDOWN: int = int(os.getenv("EMAIL_CODE_COOLDOWN", "60"))
EMAIL_CODE_RATE_LIMIT: int = int(os.getenv("EMAIL_CODE_RATE_LIMIT", "1"))

# 注册安全配置
REGISTER_MAX_ATTEMPTS: int = int(os.getenv("REGISTER_MAX_ATTEMPTS", "3"))
REGISTER_WINDOW_SECONDS: int = int(os.getenv("REGISTER_WINDOW_SECONDS", "3600"))

# 限流配置
RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_PERIOD_SECONDS: int = int(os.getenv("RATE_LIMIT_PERIOD_SECONDS", "60"))

# CORS配置
CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# API配置
API_ENCRYPTION_KEY: Optional[str] = os.getenv("API_ENCRYPTION_KEY")

# 市场数据源配置
TUSHARE_TOKEN: Optional[str] = os.getenv("TUSHARE_TOKEN")

# 用户审批
REQUIRE_APPROVAL: bool = os.getenv("REQUIRE_APPROVAL", "false").lower() == "true"

# 日志配置
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# 测试配置
TESTING: bool = os.getenv("TESTING", "false").lower() == "true"

# 应用配置
APP_NAME: str = os.getenv("APP_NAME", "StockAnalysis")
APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# CORS 详细配置
CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
CORS_ALLOW_METHODS: list = os.getenv("CORS_ALLOW_METHODS", "[\"*\"]").split(",") if os.getenv("CORS_ALLOW_METHODS") else ["*"]
CORS_ALLOW_HEADERS: list = os.getenv("CORS_ALLOW_HEADERS", "[\"*\"]").split(",") if os.getenv("CORS_ALLOW_HEADERS") else ["*"]


class Settings:
    """设置类（兼容旧代码）"""

    # 密码
    PASSWORD_MIN_LENGTH: int = PASSWORD_MIN_LENGTH
    BCRYPT_ROUNDS: int = BCRYPT_ROUNDS

    # 登录安全配置
    LOGIN_MAX_ATTEMPTS: int = LOGIN_MAX_ATTEMPTS
    LOGIN_BLOCK_DURATION: int = LOGIN_BLOCK_DURATION
    LOGIN_FAIL_WINDOW: int = LOGIN_FAIL_WINDOW

    # IP 信任配置
    IP_TRUST_THRESHOLD: int = IP_TRUST_THRESHOLD
    IP_TRUST_EXPIRE_DAYS: int = IP_TRUST_EXPIRE_DAYS

    # 图形验证码配置
    CAPTCHA_ENABLED: bool = CAPTCHA_ENABLED
    CAPTCHA_EXPIRE_SECONDS: int = CAPTCHA_EXPIRE_SECONDS
    CAPTCHA_TOLERANCE: int = CAPTCHA_TOLERANCE
    CAPTCHA_RATE_LIMIT: int = CAPTCHA_RATE_LIMIT

    # 邮箱验证码配置（预留）
    EMAIL_CODE_ENABLED: bool = EMAIL_CODE_ENABLED
    EMAIL_CODE_LENGTH: int = EMAIL_CODE_LENGTH
    EMAIL_CODE_EXPIRE_SECONDS: int = EMAIL_CODE_EXPIRE_SECONDS
    EMAIL_CODE_COOLDOWN: int = EMAIL_CODE_COOLDOWN
    EMAIL_CODE_RATE_LIMIT: int = EMAIL_CODE_RATE_LIMIT

    # 注册安全配置
    REGISTER_MAX_ATTEMPTS: int = REGISTER_MAX_ATTEMPTS
    REGISTER_WINDOW_SECONDS: int = REGISTER_WINDOW_SECONDS

    # 限流配置
    RATE_LIMIT_ENABLED: bool = RATE_LIMIT_ENABLED
    RATE_LIMIT_REQUESTS: int = RATE_LIMIT_REQUESTS
    RATE_LIMIT_PERIOD_SECONDS: int = RATE_LIMIT_PERIOD_SECONDS

    # JWT
    SECRET_KEY: str = SECRET_KEY
    ALGORITHM: str = ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES: int = ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS: int = REFRESH_TOKEN_EXPIRE_DAYS

    # 数据库
    MONGODB_URL: str = MONGODB_URL
    DATABASE_NAME: str = DATABASE_NAME
    MONGODB_DATABASE: str = MONGODB_DATABASE
    MONGODB_MAX_POOL_SIZE: int = MONGODB_MAX_POOL_SIZE
    MONGODB_MIN_POOL_SIZE: int = MONGODB_MIN_POOL_SIZE
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = MONGODB_SERVER_SELECTION_TIMEOUT_MS
    MONGODB_SOCKET_TIMEOUT_MS: int = MONGODB_SOCKET_TIMEOUT_MS

    # Redis
    REDIS_URL: str = REDIS_URL
    REDIS_MAX_CONNECTIONS: int = REDIS_MAX_CONNECTIONS
    REDIS_SOCKET_TIMEOUT: int = REDIS_SOCKET_TIMEOUT
    REDIS_SOCKET_CONNECT_TIMEOUT: int = REDIS_SOCKET_CONNECT_TIMEOUT

    # CORS
    CORS_ORIGINS: list = CORS_ORIGINS

    # API
    API_ENCRYPTION_KEY: Optional[str] = API_ENCRYPTION_KEY

    # 市场数据源
    TUSHARE_TOKEN: Optional[str] = TUSHARE_TOKEN

    # 用户审批
    REQUIRE_APPROVAL: bool = REQUIRE_APPROVAL

    # 日志
    LOG_LEVEL: str = LOG_LEVEL

    # 测试
    TESTING: bool = TESTING

    # 应用配置
    APP_NAME: str = APP_NAME
    APP_VERSION: str = APP_VERSION
    DEBUG: bool = DEBUG
    HOST: str = HOST
    PORT: int = PORT

    # CORS 详细配置
    CORS_ALLOW_CREDENTIALS: bool = CORS_ALLOW_CREDENTIALS
    CORS_ALLOW_METHODS: list = CORS_ALLOW_METHODS
    CORS_ALLOW_HEADERS: list = CORS_ALLOW_HEADERS


# 全局设置实例
settings = Settings()
