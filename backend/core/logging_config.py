"""
统一日志配置

日志级别使用规范:
- ERROR: 影响功能的错误，需要立即关注
- WARN: 潜在问题，不影响当前功能但需注意
- INFO: 关键业务流程节点，生产环境可见
- DEBUG: 开发调试信息，生产环境默认关闭
"""
import asyncio
import functools
import logging
import sys
from typing import Any, Callable, Optional, TypeVar

from core.config import settings

F = TypeVar("F", bound=Callable[..., Any])


class ContextFilter(logging.Filter):
    """添加上下文信息的日志过滤器"""

    def filter(self, record: logging.LogRecord) -> bool:
        # 添加自定义字段
        record.app_name = settings.APP_NAME
        return True


def setup_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> None:
    """配置应用日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARN, ERROR)
        log_format: 自定义日志格式
    """
    # 确定日志级别
    if level is None:
        level = "DEBUG" if settings.DEBUG else "INFO"

    # 日志格式
    if log_format is None:
        log_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
        )
        if not settings.DEBUG:
            # 生产环境使用简洁格式
            log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    formatter = logging.Formatter(
        fmt=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()  # 清除现有处理器
    root_logger.addHandler(console_handler)

    # 添加上下文过滤器
    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)

    # 配置第三方库日志级别
    _setup_third_party_loggers()

    # 记录日志系统启动
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成，级别: {level}")


def _setup_third_party_loggers() -> None:
    """配置第三方库日志级别"""
    # Motor (MongoDB async driver)
    logging.getLogger("motor").setLevel(logging.WARNING)

    # Redis (hiredis)
    logging.getLogger("redis").setLevel(logging.WARNING)

    # HTTPx (如果使用)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # APScheduler
    logging.getLogger("apscheduler").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器

    Args:
        name: 日志记录器名称，通常使用 __name__

    Returns:
        配置好的日志记录器
    """
    return logging.getLogger(name)


# 日志装饰器（用于记录函数调用）
def log_function_call(logger: Optional[logging.Logger] = None) -> Callable[[F], F]:
    """记录函数调用的装饰器

    Usage:
        @log_function_call()
        async def my_function():
            pass

    Args:
        logger: 可选的日志记录器

    Returns:
        装饰器函数
    """

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

        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper  # type: ignore[return-value]

    return decorator
