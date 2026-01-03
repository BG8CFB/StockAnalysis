"""
工具调用超时处理扩展

为工具注册表添加超时处理逻辑，默认 30 秒超时。
"""
import asyncio
import logging
from typing import Dict, Any

from modules.trading_agents.exceptions import ToolTimeoutException

logger = logging.getLogger(__name__)


async def call_tool_with_timeout(
    tool_name: str,
    handler: callable,
    arguments: Dict[str, Any],
    timeout: float = 30.0
) -> Any:
    """
    带超时处理的工具调用

    Args:
        tool_name: 工具名称
        handler: 工具处理函数
        arguments: 工具参数
        timeout: 超时时间（秒），默认 30 秒

    Returns:
        工具执行结果

    Raises:
        ToolTimeoutException: 工具调用超时
    """
    try:
        result = await asyncio.wait_for(
            _execute_handler(handler, arguments),
            timeout=timeout
        )
        logger.info(f"工具调用成功: {tool_name}")
        return result
    except asyncio.TimeoutError:
        logger.error(f"工具调用超时: {tool_name}, 超时={timeout}秒")
        raise ToolTimeoutException(
            tool_name=tool_name,
            timeout=timeout
        )
    except Exception as e:
        logger.error(f"工具调用失败: {tool_name}, 错误={e}")
        raise


async def _execute_handler(handler: callable, arguments: Dict[str, Any]) -> Any:
    """
    执行工具处理函数

    Args:
        handler: 工具处理函数
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    result = handler(**arguments)
    # 如果是协程，await
    if asyncio.iscoroutine(result):
        result = await result
    return result

