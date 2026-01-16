"""
数据源调用监控装饰器

自动记录所有数据源API调用的成功/失败状态到数据库。

使用方式：
    @monitor_api_call(market="A_STOCK", data_type="daily_quote", source_id="tushare")
    async def get_daily_quotes(self, symbol: str, ...):
        ...
"""

import logging
import functools
from typing import Callable, Optional, Any, Dict
from datetime import datetime
from contextlib import asynccontextmanager

from core.market_data.models.datasource import (
    DataSourceStatus,
    DataSourceType,
)
from core.market_data.repositories.datasource import (
    DataSourceStatusRepository,
)

logger = logging.getLogger(__name__)


# 全局监控服务实例（延迟加载）
_monitor_service = None


def _get_monitor_service():
    """获取监控服务实例"""
    global _monitor_service
    if _monitor_service is None:
        from core.market_data.services.source_monitor_service import SourceMonitorService
        _monitor_service = SourceMonitorService()
    return _monitor_service


def monitor_api_call(
    market: str,
    data_type: str,
    source_id: Optional[str] = None,
    check_type: str = "api_call"
):
    """
    API调用监控装饰器

    自动记录API调用的成功/失败状态到数据库。

    Args:
        market: 市场类型 (A_STOCK/US_STOCK/HK_STOCK)
        data_type: 数据类型 (daily_quote/financials/etc)
        source_id: 数据源ID (如果为None，从self.source_id获取)
        check_type: 检查类型标识

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 获取source_id（如果未提供）
            actual_source_id = source_id
            if actual_source_id is None:
                actual_source_id = getattr(self, 'source_id', None)
                if actual_source_id is None:
                    # 从类名推断source_id
                    class_name = self.__class__.__name__.lower()
                    if 'tushare' in class_name:
                        actual_source_id = 'tushare'
                    elif 'akshare' in class_name:
                        actual_source_id = 'akshare'
                    elif 'yahoo' in class_name:
                        actual_source_id = 'yahoo'
                    elif 'alpha' in class_name or 'vantage' in class_name:
                        actual_source_id = 'alpha_vantage'
                    else:
                        actual_source_id = 'unknown'

            start_time = datetime.now()
            error_info = None

            try:
                # 执行原方法
                result = await func(self, *args, **kwargs)

                # 记录成功
                response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                await _record_api_success(
                    market=market,
                    data_type=data_type,
                    source_id=actual_source_id,
                    response_time_ms=response_time_ms,
                    check_type=check_type
                )

                return result

            except Exception as e:
                # 记录失败
                response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                error_info = {
                    "code": type(e).__name__,
                    "message": str(e)
                }

                await _record_api_failure(
                    market=market,
                    data_type=data_type,
                    source_id=actual_source_id,
                    response_time_ms=response_time_ms,
                    error=error_info,
                    check_type=check_type
                )

                # 重新抛出异常
                raise

        return wrapper
    return decorator


async def _record_api_success(
    market: str,
    data_type: str,
    source_id: str,
    response_time_ms: int,
    check_type: str = "api_call"
):
    """记录API调用成功"""
    try:
        monitor_service = _get_monitor_service()
        await monitor_service.handle_recovery(
            market=market,
            data_type=data_type,
            source_id=source_id,
            response_time_ms=response_time_ms
        )
        logger.debug(f"API success recorded: {source_id}/{data_type}")
    except Exception as e:
        # 避免监控失败影响正常业务
        logger.warning(f"Failed to record API success: {e}")


async def _record_api_failure(
    market: str,
    data_type: str,
    source_id: str,
    response_time_ms: int,
    error: Dict[str, Any],
    check_type: str = "api_call"
):
    """记录API调用失败"""
    try:
        monitor_service = _get_monitor_service()
        result = await monitor_service.handle_failure(
            market=market,
            data_type=data_type,
            source_id=source_id,
            error=error,
            check_type=check_type
        )
        logger.info(f"API failure recorded: {source_id}/{data_type} - {result}")
    except Exception as e:
        # 避免监控失败影响正常业务
        logger.warning(f"Failed to record API failure: {e}")


@asynccontextmanager
async def monitor_api_context(
    market: str,
    data_type: str,
    source_id: str,
    check_type: str = "api_call"
):
    """
    API调用监控上下文管理器

    用于手动监控API调用的成功/失败状态。

    使用方式：
        async with monitor_api_context("A_STOCK", "daily_quote", "tushare"):
            result = await some_api_call()
    """
    start_time = datetime.now()
    error_info = None
    success = False

    try:
        yield
        success = True
    except Exception as e:
        error_info = {
            "code": type(e).__name__,
            "message": str(e)
        }
        raise
    finally:
        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        if success:
            await _record_api_success(
                market=market,
                data_type=data_type,
                source_id=source_id,
                response_time_ms=response_time_ms,
                check_type=check_type
            )
        else:
            await _record_api_failure(
                market=market,
                data_type=data_type,
                source_id=source_id,
                response_time_ms=response_time_ms,
                error=error_info,
                check_type=check_type
            )
