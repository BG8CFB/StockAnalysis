"""
MCP Tool Interceptors（官方标准实现）

注意：当前拦截器系统需要重构以适配官方 Hooks 接口。
官方文档: https://docs.langchain.com/oss/python/langchain/mcp#interceptors
官方 Hooks 接口参考: langchain_mcp_adapters.hooks
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# 官方推荐的 Tool Interceptors
# =============================================================================


async def logging_interceptor(
    request: Any,
    handler: Callable,
) -> Any:
    """
    日志拦截器 - 记录所有 MCP 工具调用（官方标准）

    Args:
        request: MCP 工具调用请求
        handler: 下一个处理器（实际工具调用）

    Returns:
        工具调用结果
    """
    tool_name = getattr(request, "name", "unknown")
    server_name = getattr(request, "server_name", "unknown")
    args = getattr(request, "args", {})

    start_time = datetime.now()
    logger.info(
        f"[MCP Interceptor] 调用工具: server={server_name}, tool={tool_name}, " f"args={args}"
    )

    try:
        # 调用实际工具
        result = await handler(request)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"[MCP Interceptor] 工具成功: server={server_name}, tool={tool_name}, "
            f"duration={duration:.2f}s"
        )

        return result

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"[MCP Interceptor] 工具失败: server={server_name}, tool={tool_name}, "
            f"error={e}, duration={duration:.2f}s",
            exc_info=True,
        )
        raise


async def retry_interceptor(
    request: Any,
    handler: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Any:
    """
    重试拦截器 - 自动重试失败的工具调用（官方标准）

    Args:
        request: MCP 工具调用请求
        handler: 下一个处理器
        max_retries: 最大重试次数
        delay: 初始重试延迟（秒）
        backoff_factor: 退避因子（每次重试延迟翻倍）

    Returns:
        工具调用结果
    """
    tool_name = getattr(request, "name", "unknown")
    last_error = None

    for attempt in range(max_retries):
        try:
            return await handler(request)

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = delay * (backoff_factor**attempt)
                logger.warning(
                    f"[MCP Interceptor] 工具调用失败，{wait_time}s 后重试: "
                    f"tool={tool_name}, attempt={attempt + 1}/{max_retries}, "
                    f"error={e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"[MCP Interceptor] 工具调用失败，已达最大重试次数: "
                    f"tool={tool_name}, max_retries={max_retries}"
                )

    raise last_error  # type: ignore[misc]


async def inject_user_context_interceptor(
    request: Any,
    handler: Callable,
    user_id: Optional[str] = None,
    user_context: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    用户上下文注入拦截器 - 注入用户信息到工具参数（官方标准）

    Args:
        request: MCP 工具调用请求
        handler: 下一个处理器
        user_id: 用户 ID
        user_context: 额外的用户上下文信息

    Returns:
        工具调用结果
    """
    # 注入 user_id 到工具参数
    if user_id and hasattr(request, "args"):
        args = getattr(request, "args", {})
        if args is None:
            setattr(request, "args", {})
            args = getattr(request, "args")
        args["user_id"] = user_id

    # 注入额外上下文
    if user_context and hasattr(request, "args"):
        args = getattr(request, "args", {})
        if args is None:
            setattr(request, "args", {})
            args = getattr(request, "args")
        args.update(user_context)

    logger.debug(
        f"[MCP Interceptor] 注入用户上下文: user_id={user_id}, "
        f"context_keys={list(user_context or {})}"
    )

    return await handler(request)


async def timeout_interceptor(
    request: Any,
    handler: Callable,
    timeout: float = 30.0,
) -> Any:
    """
    超时拦截器 - 为工具调用设置超时（官方标准）

    Args:
        request: MCP 工具调用请求
        handler: 下一个处理器
        timeout: 超时时间（秒）

    Returns:
        工具调用结果

    Raises:
        asyncio.TimeoutError: 工具调用超时
    """
    tool_name = getattr(request, "name", "unknown")

    try:
        return await asyncio.wait_for(handler(request), timeout=timeout)

    except asyncio.TimeoutError:
        logger.error(f"[MCP Interceptor] 工具调用超时: tool={tool_name}, timeout={timeout}s")
        raise asyncio.TimeoutError(f"工具 {tool_name} 调用超时（{timeout}s）")


async def require_authentication_interceptor(
    request: Any,
    handler: Callable,
    sensitive_tools: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Any:
    """
    认证检查拦截器 - 敏感工具需要认证（官方标准）

    Args:
        request: MCP 工具调用请求
        handler: 下一个处理器
        sensitive_tools: 需要认证的工具列表
        user_id: 当前用户 ID（未认证时为 None）

    Returns:
        工具调用结果

    Raises:
        PermissionError: 未认证用户尝试调用敏感工具
    """
    tool_name = getattr(request, "name", "unknown")
    sensitive_tools = sensitive_tools or []

    # 检查是否为敏感工具
    if tool_name in sensitive_tools and not user_id:
        logger.warning(f"[MCP Interceptor] 未认证用户尝试调用敏感工具: tool={tool_name}")
        raise PermissionError(f"工具 {tool_name} 需要用户认证才能调用")

    return await handler(request)


async def fallback_interceptor(
    request: Any,
    handler: Callable,
    fallback_result: Any = None,
    fallback_on_errors: Optional[List[type]] = None,
) -> Any:
    """
    降级拦截器 - 工具调用失败时返回降级结果（官方标准）

    Args:
        request: MCP 工具调用请求
        handler: 下一个处理器
        fallback_result: 降级结果
        fallback_on_errors: 触发降级的异常类型列表

    Returns:
        工具调用结果或降级结果
    """
    try:
        return await handler(request)

    except tuple(fallback_on_errors or [Exception]) as e:  # type: ignore[misc]
        tool_name = getattr(request, "name", "unknown")
        logger.warning(
            f"[MCP Interceptor] 工具调用失败，返回降级结果: " f"tool={tool_name}, error={e}"
        )
        return fallback_result


# =============================================================================
# Interceptor 构建器（官方标准）
# =============================================================================


class InterceptorBuilder:
    """
    Interceptor 构建器 - 方便组合多个拦截器（官方标准）

    Example:
        ```python
        builder = InterceptorBuilder()
        builder.add_logging()
        builder.add_retry(max_retries=3)
        builder.add_timeout(timeout=30.0)
        interceptors = builder.build()
        ```
    """

    def __init__(self) -> None:
        """初始化构建器"""
        self._interceptors: List[Callable[..., Any]] = []

    def add_logging(self) -> "InterceptorBuilder":
        """添加日志拦截器"""
        self._interceptors.append(logging_interceptor)
        return self

    def add_retry(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> "InterceptorBuilder":
        """
        添加重试拦截器

        Args:
            max_retries: 最大重试次数
            delay: 初始重试延迟（秒）
            backoff_factor: 退避因子
        """

        async def retry_with_config(request: Any, handler: Callable[..., Any]) -> Any:
            return await retry_interceptor(
                request,
                handler,
                max_retries=max_retries,
                delay=delay,
                backoff_factor=backoff_factor,
            )

        self._interceptors.append(retry_with_config)
        return self

    def add_user_context_injection(
        self,
        user_id: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> "InterceptorBuilder":
        """
        添加用户上下文注入拦截器

        Args:
            user_id: 用户 ID
            user_context: 额外上下文
        """

        async def inject_with_config(request: Any, handler: Callable[..., Any]) -> Any:
            return await inject_user_context_interceptor(
                request,
                handler,
                user_id=user_id,
                user_context=user_context,
            )

        self._interceptors.append(inject_with_config)
        return self

    def add_timeout(self, timeout: float = 30.0) -> "InterceptorBuilder":
        """
        添加超时拦截器

        Args:
            timeout: 超时时间（秒）
        """

        async def timeout_with_config(request: Any, handler: Callable[..., Any]) -> Any:
            return await timeout_interceptor(request, handler, timeout=timeout)

        self._interceptors.append(timeout_with_config)
        return self

    def add_authentication_check(
        self,
        sensitive_tools: List[str],
        user_id: Optional[str] = None,
    ) -> "InterceptorBuilder":
        """
        添加认证检查拦截器

        Args:
            sensitive_tools: 需要认证的工具列表
            user_id: 当前用户 ID
        """

        async def auth_check_with_config(request: Any, handler: Callable[..., Any]) -> Any:
            return await require_authentication_interceptor(
                request,
                handler,
                sensitive_tools=sensitive_tools,
                user_id=user_id,
            )

        self._interceptors.append(auth_check_with_config)
        return self

    def add_fallback(
        self,
        fallback_result: Any = None,
        fallback_on_errors: Optional[List[type]] = None,
    ) -> "InterceptorBuilder":
        """
        添加降级拦截器

        Args:
            fallback_result: 降级结果
            fallback_on_errors: 触发降级的异常类型
        """

        async def fallback_with_config(request: Any, handler: Callable[..., Any]) -> Any:
            return await fallback_interceptor(
                request,
                handler,
                fallback_result=fallback_result,
                fallback_on_errors=fallback_on_errors,
            )

        self._interceptors.append(fallback_with_config)
        return self

    def add_custom(
        self,
        interceptor: Callable,
    ) -> "InterceptorBuilder":
        """
        添加自定义拦截器

        Args:
            interceptor: 自定义拦截器函数
        """
        self._interceptors.append(interceptor)
        return self

    def build(self) -> List[Callable]:
        """
        构建拦截器列表

        Returns:
            拦截器列表（按添加顺序）
        """
        return self._interceptors.copy()


# =============================================================================
# 预定义的 Interceptor 组合（官方推荐配置）
# =============================================================================


def get_default_interceptors() -> List[Callable]:
    """
    获取默认 Interceptors（官方推荐配置）

    包含：
    - 日志记录
    - 超时控制（30秒）

    适用场景：开发环境、简单工具调用

    Returns:
        拦截器列表
    """
    builder = InterceptorBuilder()
    builder.add_logging()
    builder.add_timeout(timeout=30.0)
    return builder.build()


def get_production_interceptors(
    max_retries: int = 3,
    timeout: float = 60.0,
) -> List[Callable]:
    """
    获取生产环境 Interceptors（官方推荐配置）

    包含：
    - 日志记录
    - 重试机制（3次）
    - 超时控制（60秒）

    适用场景：生产环境、关键业务流程

    Args:
        max_retries: 最大重试次数
        timeout: 超时时间（秒）

    Returns:
        拦截器列表
    """
    builder = InterceptorBuilder()
    builder.add_logging()
    builder.add_retry(max_retries=max_retries)
    builder.add_timeout(timeout=timeout)
    return builder.build()


def get_secure_interceptors(
    sensitive_tools: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    max_retries: int = 3,
    timeout: float = 30.0,
) -> List[Callable]:
    """
    获取安全增强 Interceptors（官方推荐配置）

    包含：
    - 日志记录
    - 重试机制
    - 认证检查（敏感工具）
    - 用户上下文注入
    - 超时控制

    适用场景：需要权限控制、敏感操作

    Args:
        sensitive_tools: 需要认证的工具列表
        user_id: 当前用户 ID
        max_retries: 最大重试次数
        timeout: 超时时间（秒）

    Returns:
        拦截器列表
    """
    builder = InterceptorBuilder()
    builder.add_logging()
    builder.add_retry(max_retries=max_retries)
    builder.add_authentication_check(
        sensitive_tools=sensitive_tools or [],
        user_id=user_id,
    )
    builder.add_timeout(timeout=timeout)
    return builder.build()
