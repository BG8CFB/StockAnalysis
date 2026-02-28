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
# 安全要求：SECRET_KEY 必须至少 32 字符，生产环境必须使用环境变量设置
_secret_key_default = "dev-secret-key-change-in-production-at-least-64-characters-long-for-security"
SECRET_KEY: str = os.getenv("SECRET_KEY", _secret_key_default)
# 开发环境检查
if SECRET_KEY == _secret_key_default and os.getenv("ENVIRONMENT", "development") == "production":
    raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
if len(SECRET_KEY) < 32:
    raise ValueError(f"SECRET_KEY 长度不足，当前 {len(SECRET_KEY)} 字符，至少需要 32 字符")

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

# 可信代理 IP 列表（逗号分隔），只有来自这些 IP 的 X-Forwarded-For 才被信任
# 示例：TRUSTED_PROXIES=127.0.0.1,10.0.0.1
_trusted_proxies_raw = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
TRUSTED_PROXIES: set = {ip.strip() for ip in _trusted_proxies_raw.split(",") if ip.strip()}

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

# 市场数据源配置
TUSHARE_TOKEN: Optional[str] = os.getenv("TUSHARE_TOKEN")

# 数据源限流配置
DATA_SOURCE_RATE_LIMIT_WINDOW: int = int(os.getenv("DATA_SOURCE_RATE_LIMIT_WINDOW", "60"))
DATA_SOURCE_RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("DATA_SOURCE_RATE_LIMIT_MAX_REQUESTS", "1"))

# 数据源路由器配置
DATA_SOURCE_MAX_FAILURES: int = int(os.getenv("DATA_SOURCE_MAX_FAILURES", "3"))
DATA_SOURCE_HEALTH_CHECK_INTERVAL: int = int(os.getenv("DATA_SOURCE_HEALTH_CHECK_INTERVAL", "300"))

# MongoDB 批量操作配置
MONGODB_BULK_WRITE_BATCH_SIZE: int = int(os.getenv("MONGODB_BULK_WRITE_BATCH_SIZE", "1000"))

# 支持的市场类型列表
SUPPORTED_MARKETS: list = ["A_STOCK", "US_STOCK", "HK_STOCK"]

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

# 解析 CORS_ALLOW_METHODS 和 CORS_ALLOW_HEADERS
# 支持格式: "*", "GET,POST", 或 JSON 数组 '["GET","POST"]'
def _parse_cors_list(env_value: str, default: list) -> list:
    """解析 CORS 配置列表"""
    if not env_value:
        return default
    env_value = env_value.strip()
    # 通配符
    if env_value == "*":
        return ["*"]
    # JSON 数组格式
    if env_value.startswith("[") and env_value.endswith("]"):
        import json
        try:
            return json.loads(env_value)
        except json.JSONDecodeError:
            pass
    # 逗号分隔格式
    return [item.strip() for item in env_value.split(",")]

CORS_ALLOW_METHODS: list = _parse_cors_list(os.getenv("CORS_ALLOW_METHODS"), ["*"])
CORS_ALLOW_HEADERS: list = _parse_cors_list(os.getenv("CORS_ALLOW_HEADERS"), ["*"])


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

    # 市场数据源
    TUSHARE_TOKEN: Optional[str] = TUSHARE_TOKEN

    # 数据源限流配置
    DATA_SOURCE_RATE_LIMIT_WINDOW: int = DATA_SOURCE_RATE_LIMIT_WINDOW
    DATA_SOURCE_RATE_LIMIT_MAX_REQUESTS: int = DATA_SOURCE_RATE_LIMIT_MAX_REQUESTS

    # 数据源路由器配置
    DATA_SOURCE_MAX_FAILURES: int = DATA_SOURCE_MAX_FAILURES
    DATA_SOURCE_HEALTH_CHECK_INTERVAL: int = DATA_SOURCE_HEALTH_CHECK_INTERVAL

    # MongoDB 批量操作配置
    MONGODB_BULK_WRITE_BATCH_SIZE: int = MONGODB_BULK_WRITE_BATCH_SIZE

    # 支持的市场类型列表
    SUPPORTED_MARKETS: list = SUPPORTED_MARKETS

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
