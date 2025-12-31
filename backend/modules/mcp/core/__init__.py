"""
MCP 核心功能模块

基于 langchain-mcp-adapters 官方推荐实现：
- 适配器（adapter）
- 拦截器（interceptors）
- 会话管理（session）
- 异常定义（exceptions）
"""

# 适配器
from .adapter import (
    build_stdio_connection,
    build_sse_connection,
    build_streamable_http_connection,
    build_websocket_connection,
    get_mcp_tools,
    create_mcp_client,
    get_mcp_tools_multi_server,
    build_auth_headers,
    map_transport_mode,
)

# 拦截器
from .interceptors import (
    logging_interceptor,
    retry_interceptor,
    inject_user_context_interceptor,
    timeout_interceptor,
    require_authentication_interceptor,
    fallback_interceptor,
    InterceptorBuilder,
    get_default_interceptors,
    get_production_interceptors,
    get_secure_interceptors,
)

# 会话管理
from .session import (
    mcp_session_context,
    load_tools_with_session,
    load_resources_with_session,
    load_prompt_with_session,
)

# 异常
from .exceptions import (
    MCPConnectionError,
    MCPTimeoutError,
    MCPProtocolError,
    MCPUnavailableError,
)

__all__ = [
    # 适配器
    "build_stdio_connection",
    "build_sse_connection",
    "build_streamable_http_connection",
    "build_websocket_connection",
    "get_mcp_tools",
    "create_mcp_client",
    "get_mcp_tools_multi_server",
    "build_auth_headers",
    "map_transport_mode",

    # 拦截器
    "logging_interceptor",
    "retry_interceptor",
    "inject_user_context_interceptor",
    "timeout_interceptor",
    "require_authentication_interceptor",
    "fallback_interceptor",
    "InterceptorBuilder",
    "get_default_interceptors",
    "get_production_interceptors",
    "get_secure_interceptors",

    # 会话管理
    "mcp_session_context",
    "load_tools_with_session",
    "load_resources_with_session",
    "load_prompt_with_session",

    # 异常
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPProtocolError",
    "MCPUnavailableError",
]
