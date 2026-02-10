"""
统一日志配置

日志分层策略:
- 终端 (StreamHandler): INFO 级别，显示请求、错误、简单状态
- 文件 (RotatingFileHandler): DEBUG 级别，存储详细的调试信息，自动轮转

日志级别使用规范:
- ERROR: 影响功能的错误，需要立即关注 ❌
- WARNING: 潜在问题，不影响当前功能但需注意 ⚠️
- INFO: 关键业务流程节点，生产环境可见 ✅
- DEBUG: 开发调试信息，写入文件，生产环境默认关闭 🔍
"""
import asyncio
import functools
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from core.config import settings
from core.colored_formatter import get_formatter

F = TypeVar("F", bound=Callable[..., Any])


class SafeStreamHandler(logging.StreamHandler):
    """安全的 StreamHandler，在流关闭时不会抛出异常"""

    def __init__(self, stream=None, encoding=None):
        """初始化处理器"""
        if stream is None:
            stream = sys.stdout

        # 尝试使用 encoding 参数（Python 3.9+）
        if encoding:
            try:
                super().__init__(stream, encoding=encoding)
                return
            except TypeError:
                pass

        super().__init__(stream)

    def emit(self, record: logging.LogRecord) -> None:
        """安全地输出日志"""
        try:
            if self.stream is None or (hasattr(self.stream, 'closed') and self.stream.closed):
                return
            super().emit(record)
        except (ValueError, OSError):
            pass
        except Exception:
            pass


class ContextFilter(logging.Filter):
    """添加上下文信息的日志过滤器"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.app_name = settings.APP_NAME
        return True


def setup_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> None:
    """配置应用日志系统

    配置两个处理器:
    1. 终端处理器: INFO 级别，输出到 stdout
    2. 文件处理器: DEBUG 级别，写入日志文件

    Args:
        level: 日志级别 (DEBUG, INFO, WARN, ERROR)
        log_format: 自定义日志格式 (已废弃，使用彩色格式器)
    """
    # 确定日志级别
    if level is None:
        level = "DEBUG" if settings.DEBUG else "INFO"

    # 获取彩色格式器
    formatter = get_formatter(debug_mode=settings.DEBUG)

    # 获取原始输出流
    stdout_stream = sys.__stdout__ or sys.stdout

    # ==================== 终端处理器 ====================
    # 级别: INFO，显示请求、错误、简单状态
    console_handler = SafeStreamHandler(stdout_stream)
    try:
        console_handler = SafeStreamHandler(stdout_stream, encoding='utf-8')
    except TypeError:
        console_handler = SafeStreamHandler(stdout_stream)

    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)  # 终端只显示 INFO 及以上

    # ==================== 文件处理器 ====================
    # 级别: DEBUG，存储详细的调试信息，自动轮转
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 根据环境确定日志文件名
    env_name = "development" if settings.DEBUG else "production"

    # 使用 RotatingFileHandler 实现日志轮转
    # maxBytes=10MB, backupCount=5 (保留5个备份文件)
    file_handler = RotatingFileHandler(
        log_dir / f"app_{env_name}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # 文件记录 DEBUG 及以上

    # ==================== 配置根日志器 ====================
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 根日志器设为 DEBUG，允许所有级别通过

    # 清除已存在的 handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # 添加处理器
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 添加上下文过滤器
    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)

    # 配置第三方库日志级别
    _setup_third_party_loggers()

    # 记录日志系统启动
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成 - 终端: INFO+, 文件: DEBUG+ (logs/app_{env_name}.log)")


def _setup_third_party_loggers() -> None:
    """配置第三方库日志级别

    第三方库日志默认设为 WARNING，减少噪音
    """
    # 数据库相关 - WARNING
    for name in ["motor", "pymongo", "pymongo.topology", "pymongo.server", "pymongo.monitoring"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Redis - WARNING
    for name in ["redis", "hiredis"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    # HTTP 客户端 - WARNING
    for name in ["httpx", "httpcore"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    # 任务调度 - INFO
    logging.getLogger("apscheduler").setLevel(logging.INFO)

    # Web 框架 - WARNING (减少噪音，只显示真正的警告和错误)
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.WARNING)
    # 确保 uvicorn 日志传播到根日志器
    uvicorn_logger.propagate = True

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.WARNING)
    uvicorn_access.propagate = True

    # AI SDK - WARNING
    for name in ["openai", "anthropic"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    # WebSocket - WARNING
    logging.getLogger("websockets").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)


# 日志装饰器（用于记录函数调用）
def log_function_call(logger: Optional[logging.Logger] = None) -> Callable[[F], F]:
    """记录函数调用的装饰器"""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _logger = logger or logging.getLogger(func.__module__)
            func_name = f"{func.__module__}.{func.__qualname__}"
            _logger.debug(f"调用函数: {func_name}")
            try:
                result = await func(*args, **kwargs)
                _logger.debug(f"函数完成: {func_name}")
                return result
            except Exception as e:
                _logger.error(f"函数异常: {func_name}, error={e}", exc_info=True)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            _logger = logger or logging.getLogger(func.__module__)
            func_name = f"{func.__module__}.{func.__qualname__}"
            _logger.debug(f"调用函数: {func_name}")
            try:
                result = func(*args, **kwargs)
                _logger.debug(f"函数完成: {func_name}")
                return result
            except Exception as e:
                _logger.error(f"函数异常: {func_name}, error={e}", exc_info=True)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper  # type: ignore[return-value]

    return decorator
