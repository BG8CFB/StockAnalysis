"""
系统问题诊断日志增强脚本

用于增强错误日志，帮助定位问题根源。
"""

import logging
import traceback
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


def log_with_context(error_category: str) -> Callable[..., Any]:
    """
    为函数添加详细上下文日志的装饰器

    Args:
        error_category: 错误分类，用于日志分类
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # 详细的错误日志
                logger.error(
                    f"[{error_category}] Error in {func.__name__}: "
                    f"{type(e).__name__}: {str(e)}\n"
                    f"Args: {args}\n"
                    f"Kwargs: {kwargs}\n"
                    f"Traceback:\n{traceback.format_exc()}",
                    extra={
                        "error_category": error_category,
                        "function_name": func.__name__,
                        "error_type": type(e).__name__,
                    },
                )
                raise

        return wrapper

    return decorator


# 监控指标（可以用 Prometheus 或其他监控系统集成）
class SystemMetrics:
    """系统监控指标"""

    # 数据源相关指标
    YAHOO_RATE_LIMIT_HITS = 0
    DATA_SOURCE_FAILURES = {
        "yahoo": 0,
        "akshare": 0,
        "tushare": 0,
    }

    # 配置验证相关指标
    CONFIG_VALIDATION_FAILURES = {
        "phase1": 0,
        "phase2": 0,
        "phase3": 0,
        "phase4": 0,
    }

    # 缓存解析相关指标
    CACHE_PARSE_ERRORS = 0

    # 数据适配器错误
    ADAPTER_NONE_TYPE_ERRORS = 0

    @classmethod
    def increment_rate_limit_hit(cls, source: str) -> None:
        """增加速率限制命中次数"""
        if source in cls.DATA_SOURCE_FAILURES:
            cls.DATA_SOURCE_FAILURES[source] += 1
            if source == "yahoo":
                cls.YAHOO_RATE_LIMIT_HITS += 1

    @classmethod
    def increment_config_validation_failure(cls, phase: str) -> None:
        """增加配置验证失败次数"""
        if phase in cls.CONFIG_VALIDATION_FAILURES:
            cls.CONFIG_VALIDATION_FAILURES[phase] += 1

    @classmethod
    def increment_cache_parse_error(cls) -> None:
        """增加缓存解析错误次数"""
        cls.CACHE_PARSE_ERRORS += 1

    @classmethod
    def increment_adapter_none_type_error(cls) -> None:
        """增加适配器 NoneType 错误次数"""
        cls.ADAPTER_NONE_TYPE_ERRORS += 1

    @classmethod
    def get_metrics_summary(cls) -> dict[str, Any]:
        """获取指标摘要"""
        return {
            "yahoo_rate_limit_hits": cls.YAHOO_RATE_LIMIT_HITS,
            "data_source_failures": cls.DATA_SOURCE_FAILURES,
            "config_validation_failures": cls.CONFIG_VALIDATION_FAILURES,
            "cache_parse_errors": cls.CACHE_PARSE_ERRORS,
            "adapter_none_type_errors": cls.ADAPTER_NONE_TYPE_ERRORS,
        }


# 使用示例
if __name__ == "__main__":
    print("系统问题诊断日志增强脚本已加载")
    print(f"当前指标: {SystemMetrics.get_metrics_summary()}")
