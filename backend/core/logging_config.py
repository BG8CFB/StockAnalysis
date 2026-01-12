"""
统一日志配置

日志级别使用规范:
- ERROR: 影响功能的错误，需要立即关注 ❌
- WARNING: 潜在问题，不影响当前功能但需注意 ⚠️
- INFO: 关键业务流程节点，生产环境可见 ✅
- DEBUG: 开发调试信息，生产环境默认关闭 🔍

日志输出规范:
- 应用日志: 正常输出，带颜色和符号
- 第三方库日志: 默认 WARNING 级别，避免大量 DEBUG 日志
"""
import asyncio
import functools
import logging
import sys
from typing import Any, Callable, Optional, TypeVar

from core.config import settings
from core.colored_formatter import get_formatter

F = TypeVar("F", bound=Callable[..., Any])


class ContextFilter(logging.Filter):
    """添加上下文信息的日志过滤器"""

    def filter(self, record: logging.LogRecord) -> bool:
        # 添加自定义字段
        record.app_name = settings.APP_NAME
        return True


class LowLevelFilter(logging.Filter):
    """过滤低级别日志的过滤器"""

    def __init__(self, min_level: int = logging.WARNING):
        super().__init__()
        self.min_level = min_level

    def filter(self, record: logging.LogRecord) -> bool:
        """只允许大于等于 min_level 的日志通过"""
        return record.levelno >= self.min_level


def setup_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> None:
    """配置应用日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARN, ERROR)
        log_format: 自定义日志格式 (已废弃，使用彩色格式器)
    """
    # 确定日志级别
    if level is None:
        level = "DEBUG" if settings.DEBUG else "INFO"

    # 获取彩色格式器
    formatter = get_formatter(debug_mode=settings.DEBUG)

    # 控制台处理器 - 使用 UTF-8 编码以支持 emoji 字符
    # 在 Windows 上避免 GBK 编码错误: 'gbk' codec can't encode character
    try:
        # Python 3.9+ 支持 encoding 参数
        console_handler = logging.StreamHandler(sys.stdout, encoding='utf-8')
    except TypeError:
        # Python 3.8 及以下版本不支持 encoding 参数
        # 需要重新配置 stdout 的编码
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
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
    """配置第三方库日志级别

    原则:
    1. 避免输出大量重复的心跳/连接日志 (如 MongoDB heartbeat)
    2. 只输出 WARNING 及以上级别
    3. 对于关键操作可降低到 INFO
    """
    # ==================== 数据库相关 ====================

    # Motor (MongoDB async driver)
    # 设置为 WARNING，避免大量 heartbeat 日志
    motor_logger = logging.getLogger("motor")
    motor_logger.setLevel(logging.WARNING)

    # PyMongo (MongoDB driver)
    # pymongo.topology 输出大量 heartbeat 日志，设置为 WARNING
    pymongo_topology = logging.getLogger("pymongo.topology")
    pymongo_topology.setLevel(logging.WARNING)

    pymongo_server = logging.getLogger("pymongo.server")
    pymongo_server.setLevel(logging.WARNING)

    pymongo_monitoring = logging.getLogger("pymongo.monitoring")
    pymongo_monitoring.setLevel(logging.WARNING)

    # 其他 pymongo 模块
    for name in logging.root.manager.loggerDict:
        if name.startswith("pymongo"):
            logging.getLogger(name).setLevel(logging.WARNING)

    # ==================== Redis ====================

    # Redis 客户端
    redis_logger = logging.getLogger("redis")
    redis_logger.setLevel(logging.WARNING)

    # hiredis (Redis C 扩展)
    hiredis_logger = logging.getLogger("hiredis")
    hiredis_logger.setLevel(logging.WARNING)

    # ==================== HTTP 客户端 ====================

    # HTTPx (如果使用)
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)

    # httpcore (httpx 的底层库)
    httpcore_logger = logging.getLogger("httpcore")
    httpcore_logger.setLevel(logging.WARNING)

    # ==================== 任务调度 ====================

    # APScheduler
    apscheduler_logger = logging.getLogger("apscheduler")
    apscheduler_logger.setLevel(logging.INFO)

    # ==================== Web 框架 ====================

    # Uvicorn (如果通过代码启动)
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.INFO)

    # ==================== 其他常用库 ====================

    # OpenAI SDK
    openai_logger = logging.getLogger("openai")
    openai_logger.setLevel(logging.WARNING)

    # Anthropic SDK
    anthropic_logger = logging.getLogger("anthropic")
    anthropic_logger.setLevel(logging.WARNING)

    # websockets
    websockets_logger = logging.getLogger("websockets")
    websockets_logger.setLevel(logging.WARNING)

    # ==================== 调试模式下的特殊处理 ====================
    if settings.DEBUG:
        # 调试模式下，可以适当降低一些关键库的日志级别
        # 但仍然避免大量的 heartbeat 日志

        # pymongo 仍然保持 WARNING，避免 heartbeat 日志
        # 如果需要调试 MongoDB 连接，可以临时改为 INFO

        pass


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
