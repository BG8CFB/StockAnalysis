"""
MCP 系统配置数据模型

定义 MCP 系统配置的 Pydantic 模型，用于前端配置管理。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MCPSystemSettingsBase(BaseModel):
    """MCP 系统配置基础模型"""

    # 连接池配置
    pool_personal_max_concurrency: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="个人并发上限（每个用户的个人 MCP 最大并发连接数）"
    )
    pool_public_per_user_max: int = Field(
        default=10,
        ge=1,
        le=100,
        description="公共并发上限（每个用户使用公共 MCP 的最大并发连接数）"
    )
    pool_personal_queue_size: int = Field(
        default=200,
        ge=10,
        le=1000,
        description="个人队列大小（个人 MCP 请求队列最大容量）"
    )
    pool_public_queue_size: int = Field(
        default=50,
        ge=10,
        le=500,
        description="公共队列大小（公共 MCP 请求队列最大容量）"
    )

    # 连接生命周期
    connection_complete_timeout: int = Field(
        default=2,
        ge=1,
        le=300,
        description="完成超时时间（任务完成后连接销毁等待时间，秒）"
    )
    connection_failed_timeout: int = Field(
        default=10,
        ge=1,
        le=600,
        description="失败超时时间（任务失败后连接销毁等待时间，秒）"
    )

    # 健康检查
    health_check_enabled: bool = Field(
        default=True,
        description="是否启用自动健康检查"
    )
    health_check_interval: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="健康检查间隔时间（秒）"
    )
    health_check_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="单次健康检查超时时间（秒）"
    )


class MCPSystemSettingsCreate(MCPSystemSettingsBase):
    """创建/更新 MCP 系统配置请求"""
    pass


class MCPSystemSettingsResponse(MCPSystemSettingsBase):
    """MCP 系统配置响应"""
    updated_at: Optional[datetime] = Field(default=None, description="最后更新时间")

    @classmethod
    def from_db(cls, data: dict) -> "MCPSystemSettingsResponse":
        """从数据库数据创建响应对象"""
        return cls(
            pool_personal_max_concurrency=data.get("pool_personal_max_concurrency", 100),
            pool_public_per_user_max=data.get("pool_public_per_user_max", 10),
            pool_personal_queue_size=data.get("pool_personal_queue_size", 200),
            pool_public_queue_size=data.get("pool_public_queue_size", 50),
            connection_complete_timeout=data.get("connection_complete_timeout", 2),
            connection_failed_timeout=data.get("connection_failed_timeout", 10),
            health_check_enabled=data.get("health_check_enabled", True),
            health_check_interval=data.get("health_check_interval", 300),
            health_check_timeout=data.get("health_check_timeout", 30),
            updated_at=data.get("updated_at"),
        )
