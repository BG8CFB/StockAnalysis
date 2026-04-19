"""
MCP 自定义异常

定义 MCP 相关的所有异常类型。
"""


class MCPError(Exception):
    """MCP 基础异常"""

    pass


class MCPConnectionError(MCPError):
    """MCP 连接错误"""

    pass


class MCPTimeoutError(MCPError):
    """MCP 超时错误"""

    pass


class MCPProtocolError(MCPError):
    """MCP 协议错误"""

    pass


class MCPUnavailableError(MCPError):
    """MCP 服务器不可用错误"""

    pass


class MCPToolError(MCPError):
    """MCP 工具调用错误"""

    pass


class MCPAuthenticationError(MCPError):
    """MCP 认证错误"""

    pass


class MCPConfigurationError(MCPError):
    """MCP 配置错误"""

    pass
