"""
MCP 数据模型

定义 MCP 服务器配置相关的 Pydantic 模型。
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# 枚举定义
# =============================================================================

class MCPServerStatusEnum(str, Enum):
    """MCP 服务器状态枚举"""
    AVAILABLE = "available"     # 可用
    UNAVAILABLE = "unavailable" # 不可用
    UNKNOWN = "unknown"         # 未知


class TransportModeEnum(str, Enum):
    """MCP 传输模式枚举

    支持官方 langchain-mcp-adapters 的所有传输模式：
    - stdio: 标准输入输出（用于本地进程）
    - sse: Server-Sent Events（已废弃，建议使用 streamable_http）
    - http/streamable_http: Streamable HTTP（推荐）
    - websocket: WebSocket
    """
    STDIO = "stdio"                     # 标准输入输出
    SSE = "sse"                         # Server-Sent Events
    HTTP = "http"                       # HTTP (映射到 streamable_http)
    STREAMABLE_HTTP = "streamable_http" # Streamable HTTP (推荐)
    WEBSOCKET = "websocket"             # WebSocket


class AuthTypeEnum(str, Enum):
    """MCP 认证类型枚举"""
    NONE = "none"               # 无认证
    BEARER = "bearer"           # Bearer Token
    BASIC = "basic"             # Basic Auth


# =============================================================================
# MCP 服务器配置模型
# =============================================================================

class MCPServerConfigBase(BaseModel):
    """MCP 服务器配置基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="服务器名称")
    transport: TransportModeEnum = Field(..., description="传输模式")

    # stdio 模式配置
    command: Optional[str] = Field(None, description="启动命令")
    args: Optional[List[str]] = Field(default_factory=list, description="命令参数")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="环境变量")

    # http/sse/websocket 模式配置
    url: Optional[str] = Field(None, description="服务器 URL")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP 请求头")

    # 认证配置（兼容旧版本，建议使用 headers）
    auth_type: AuthTypeEnum = Field(default=AuthTypeEnum.NONE, description="认证类型")
    auth_token: Optional[str] = Field(None, description="认证令牌")

    auto_approve: List[str] = Field(default_factory=list, description="自动批准的工具列表")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator("env")
    @classmethod
    def validate_env(cls, v: Optional[Dict[str, str]]) -> Dict[str, str]:
        """验证环境变量格式"""
        if v is None:
            return {}
        # 确保是 JSON 可序列化的
        try:
            import json
            json.dumps(v)
        except TypeError:
            raise ValueError("环境变量必须可序列化为 JSON")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: Optional[Dict[str, str]]) -> Dict[str, str]:
        """验证 HTTP headers 格式"""
        if v is None:
            return {}
        # 确保是 JSON 可序列化的
        try:
            import json
            json.dumps(v)
        except TypeError:
            raise ValueError("Headers 必须可序列化为 JSON")
        return v


class MCPServerConfigCreate(MCPServerConfigBase):
    """创建 MCP 服务器配置请求"""
    is_system: bool = Field(default=False, description="是否为系统级配置")


class MCPServerConfigUpdate(BaseModel):
    """更新 MCP 服务器配置请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    transport: Optional[TransportModeEnum] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[AuthTypeEnum] = None
    auth_token: Optional[str] = None
    auto_approve: Optional[List[str]] = None
    enabled: Optional[bool] = None


class MCPServerConfigResponse(MCPServerConfigBase):
    """MCP 服务器配置响应"""
    id: str
    is_system: bool
    owner_id: Optional[str]
    status: MCPServerStatusEnum
    last_check_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "MCPServerConfigResponse":
        """从数据库数据创建响应对象"""
        return cls(
            id=str(data["_id"]),
            name=data["name"],
            transport=TransportModeEnum(data["transport"]),
            command=data.get("command"),
            args=data.get("args", []),
            env=data.get("env", {}),
            url=data.get("url"),
            headers=data.get("headers", {}),
            auth_type=AuthTypeEnum(data.get("auth_type", "none")),
            auth_token=data.get("auth_token"),
            auto_approve=data.get("auto_approve", []),
            enabled=data["enabled"],
            is_system=data.get("is_system", False),
            owner_id=data.get("owner_id"),
            status=MCPServerStatusEnum(data.get("status", "unknown")),
            last_check_at=data.get("last_check_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


# =============================================================================
# 连接测试模型
# =============================================================================

class ConnectionTestResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str
    latency_ms: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


# =============================================================================
# 工具信息模型
# =============================================================================

class MCPToolInfo(BaseModel):
    """MCP 工具信息"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    server_id: str = Field(..., description="所属服务器 ID")
    server_name: str = Field(..., description="所属服务器名称")
