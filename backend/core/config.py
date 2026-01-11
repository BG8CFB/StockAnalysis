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

# JWT配置
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 密码安全
PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

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

    # JWT
    SECRET_KEY: str = SECRET_KEY
    ALGORITHM: str = ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES: int = ACCESS_TOKEN_EXPIRE_MINUTES

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
