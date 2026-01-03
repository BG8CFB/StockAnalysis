"""
配置相关数据模型

包含智能体配置、用户设置等模型。
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator, field_serializer


# =============================================================================
# MCP 服务器配置模型
# =============================================================================

class MCPServerConfig(BaseModel):
    """MCP 服务器配置（支持容错策略）"""
    name: str = Field(..., description="服务器名称")
    required: bool = Field(default=True, description="是否必需（必需服务器失败将阻止任务启动）")

    @classmethod
    def from_str(cls, server_name: str) -> "MCPServerConfig":
        """从字符串创建配置（向后兼容）"""
        return cls(name=server_name, required=True)

    @classmethod
    def from_list(cls, server_names: List[str]) -> List["MCPServerConfig"]:
        """从字符串列表创建配置列表（向后兼容）"""
        return [cls.from_str(name) for name in server_names]


# =============================================================================
# 智能体配置模型
# =============================================================================

class AgentConfig(BaseModel):
    """单个智能体配置（完整版，含提示词）

    role_definition 可选，以支持精简模式（不暴露提示词给普通用户）
    """
    slug: str = Field(..., min_length=1, max_length=50, description="唯一标识符")
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    role_definition: Optional[str] = Field(None, min_length=1, max_length=10000, description="角色定义（系统提示词）")
    when_to_use: str = Field(..., max_length=500, description="使用场景说明")
    enabled_mcp_servers: List[MCPServerConfig] = Field(
        default_factory=list,
        description="启用的 MCP 服务器（支持配置必需性）"
    )
    enabled_local_tools: List[str] = Field(default_factory=list, description="启用的本地工具")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator('enabled_mcp_servers', mode='before')
    @classmethod
    def convert_mcp_servers(cls, v):
        """向后兼容：自动将字符串/字典列表转换为 MCPServerConfig 列表"""
        if not v:
            return []
        # 如果已经是 MCPServerConfig 列表，直接返回
        if isinstance(v, list) and len(v) > 0:
            if isinstance(v[0], MCPServerConfig):
                return v
            # 如果是字符串列表，转换
            if isinstance(v[0], str):
                return MCPServerConfig.from_list(v)
            # 如果是字典列表，尝试解析
            if isinstance(v[0], dict):
                try:
                    return [MCPServerConfig(**item) for item in v]
                except Exception:
                    pass
        return v

    @field_serializer('enabled_mcp_servers')
    def serialize_mcp_servers(self, value: List[MCPServerConfig]) -> List[str]:
        """序列化时将 MCPServerConfig 对象转换为字符串列表（前端兼容）"""
        if not value:
            return []
        result = []
        for server in value:
            if isinstance(server, MCPServerConfig):
                result.append(server.name)
            elif isinstance(server, str):
                result.append(server)
            elif isinstance(server, dict):
                result.append(server.get('name', ''))
        return result


class AgentConfigSlim(BaseModel):
    """单个智能体配置（精简版，不含提示词）

    用于分析页面，不暴露敏感的 role_definition。
    普通用户不应看到系统提示词，避免泄露业务逻辑。
    """
    slug: str = Field(..., min_length=1, max_length=50, description="唯一标识符")
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    when_to_use: str = Field(..., max_length=500, description="使用场景说明")
    enabled_mcp_servers: List[MCPServerConfig] = Field(
        default_factory=list,
        description="启用的 MCP 服务器（支持配置必需性）"
    )
    enabled_local_tools: List[str] = Field(default_factory=list, description="启用的本地工具")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator('enabled_mcp_servers', mode='before')
    @classmethod
    def convert_mcp_servers(cls, v):
        """向后兼容：自动将字符串/字典列表转换为 MCPServerConfig 列表"""
        if not v:
            return []
        # 如果已经是 MCPServerConfig 列表，直接返回
        if isinstance(v, list) and len(v) > 0:
            if isinstance(v[0], MCPServerConfig):
                return v
            # 如果是字符串列表，转换
            if isinstance(v[0], str):
                return MCPServerConfig.from_list(v)
            # 如果是字典列表，尝试解析
            if isinstance(v[0], dict):
                try:
                    return [MCPServerConfig(**item) for item in v]
                except Exception:
                    pass
        return v

    @field_serializer('enabled_mcp_servers')
    def serialize_mcp_servers(self, value: List[MCPServerConfig]) -> List[str]:
        """序列化时将 MCPServerConfig 对象转换为字符串列表（前端兼容）"""
        if not value:
            return []
        result = []
        for server in value:
            if isinstance(server, MCPServerConfig):
                result.append(server.name)
            elif isinstance(server, str):
                result.append(server)
            elif isinstance(server, dict):
                result.append(server.get('name', ''))
        return result


class PhaseConfigBase(BaseModel):
    """阶段配置基础模型（不含model_id，模型选择与智能体配置分离）"""
    enabled: bool = Field(default=True, description="是否启用该阶段")
    max_rounds: int = Field(default=1, ge=0, le=10, description="最大轮次（辩论/讨论）")
    agents: List[AgentConfig] = Field(default_factory=list, description="智能体列表")

    # 第一阶段专用
    max_concurrency: Optional[int] = Field(None, ge=1, le=10, description="智能体最大并发数")


class PhaseConfigBaseSlim(BaseModel):
    """阶段配置基础模型（精简版，不含提示词）"""
    enabled: bool = Field(default=True, description="是否启用该阶段")
    max_rounds: int = Field(default=1, ge=0, le=10, description="最大轮次（辩论/讨论）")
    agents: List[AgentConfigSlim] = Field(default_factory=list, description="智能体列表（精简版）")

    # 第一阶段专用
    max_concurrency: Optional[int] = Field(None, ge=1, le=10, description="智能体最大并发数")


class Phase1Config(PhaseConfigBase):
    """第一阶段配置"""
    max_concurrency: int = Field(default=3, ge=1, le=10, description="智能体最大并发数")


class Phase1ConfigSlim(PhaseConfigBaseSlim):
    """第一阶段配置（精简版）"""
    max_concurrency: int = Field(default=3, ge=1, le=10, description="智能体最大并发数")


class Phase2Config(PhaseConfigBase):
    """第二阶段配置（辩论）"""
    pass


class Phase2ConfigSlim(PhaseConfigBaseSlim):
    """第二阶段配置（精简版）"""
    pass


class Phase3Config(PhaseConfigBase):
    """第三阶段配置（风险评估）"""
    pass


class Phase3ConfigSlim(PhaseConfigBaseSlim):
    """第三阶段配置（精简版）"""
    pass


class Phase4Config(PhaseConfigBase):
    """第四阶段配置（总结）"""
    pass


class Phase4ConfigSlim(PhaseConfigBaseSlim):
    """第四阶段配置（精简版）"""
    pass


# =============================================================================
# 用户智能体配置模型
# =============================================================================

class UserAgentConfigCreate(BaseModel):
    """创建用户智能体配置请求"""
    phase1: Phase1Config
    phase2: Optional[Phase2Config] = None
    phase3: Optional[Phase3Config] = None
    phase4: Optional[Phase4Config] = None


class UserAgentConfigUpdate(BaseModel):
    """更新用户智能体配置请求"""
    phase1: Optional[Phase1Config] = None
    phase2: Optional[Phase2Config] = None
    phase3: Optional[Phase3Config] = None
    phase4: Optional[Phase4Config] = None


class UserAgentConfigResponse(BaseModel):
    """用户智能体配置响应"""
    id: str
    user_id: str
    is_public: bool = False
    is_customized: bool = False
    phase1: Phase1Config
    phase2: Optional[Phase2Config]
    phase3: Optional[Phase3Config]
    phase4: Optional[Phase4Config]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "UserAgentConfigResponse":
        """从数据库数据创建响应对象"""
        import logging
        logger = logging.getLogger(__name__)

        def parse_phase(phase_data: Dict[str, Any], phase_class) -> PhaseConfigBase:
            """解析阶段配置，处理可能的None值"""
            # 过滤掉None值
            clean_data = {}
            for key, value in phase_data.items():
                if value is not None:
                    clean_data[key] = value

            # Debug log
            logger.debug(f"Parsing phase with class {phase_class.__name__}")
            logger.debug(f"Phase data: {phase_data}")
            logger.debug(f"Clean data: {clean_data}")

            return phase_class(**clean_data)

        def convert_mcp_servers_to_strings(phase_config):
            """将 MCPServerConfig 对象列表转换为字符串列表（前端兼容）"""
            if not phase_config or not hasattr(phase_config, 'agents'):
                return phase_config

            for agent in phase_config.agents:
                if hasattr(agent, 'enabled_mcp_servers') and agent.enabled_mcp_servers:
                    # 将 MCPServerConfig 对象转换为字符串
                    agent.enabled_mcp_servers = [
                        server.name if isinstance(server, MCPServerConfig) else server
                        for server in agent.enabled_mcp_servers
                    ]

            return phase_config

        # 解析phase1 (也使用parse_phase来过滤None值)
        phase1_data = data.get("phase1", {})
        logger.debug(f"Phase1 data from DB: {phase1_data}")
        phase1 = parse_phase(phase1_data, Phase1Config)
        phase1 = convert_mcp_servers_to_strings(phase1)

        # 解析其他阶段
        phase2 = parse_phase(data.get("phase2", {}), Phase2Config) if data.get("phase2") else None
        if phase2:
            phase2 = convert_mcp_servers_to_strings(phase2)

        phase3 = parse_phase(data.get("phase3", {}), Phase3Config) if data.get("phase3") else None
        if phase3:
            phase3 = convert_mcp_servers_to_strings(phase3)

        phase4 = parse_phase(data.get("phase4", {}), Phase4Config) if data.get("phase4") else None
        if phase4:
            phase4 = convert_mcp_servers_to_strings(phase4)

        return cls(
            id=str(data["_id"]),
            user_id=data["user_id"],
            is_public=data.get("is_public", False),
            is_customized=data.get("is_customized", False),
            phase1=phase1,
            phase2=phase2,
            phase3=phase3,
            phase4=phase4,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


# =============================================================================
# TradingAgents 用户设置模型
# =============================================================================

class TradingAgentsSettings(BaseModel):
    """TradingAgents 模块的用户设置"""

    # AI 模型配置
    data_collection_model_id: str = Field(default="", description="数据收集阶段模型ID")
    debate_model_id: str = Field(default="", description="辩论阶段模型ID")

    # 辩论配置
    default_debate_rounds: int = Field(default=3, ge=0, le=10, description="默认辩论轮次")
    max_debate_rounds: int = Field(default=5, ge=0, le=10, description="最大辩论轮次")

    # 超时配置
    phase_timeout_minutes: int = Field(default=30, ge=5, le=120, description="单阶段超时（分钟）")
    agent_timeout_minutes: int = Field(default=10, ge=1, le=60, description="单智能体超时（分钟）")
    tool_timeout_seconds: int = Field(default=30, ge=10, le=300, description="工具调用超时（秒）")

    # 其他配置
    task_expiry_hours: int = Field(default=24, ge=1, le=168, description="任务过期时间（小时）")
    archive_days: int = Field(default=30, ge=7, le=365, description="报告归档天数")
    enable_loop_detection: bool = Field(default=True, description="启用工具循环检测")
    enable_progress_events: bool = Field(default=True, description="启用实时进度推送")


class TradingAgentsSettingsResponse(BaseModel):
    """TradingAgents 设置响应"""
    id: str
    user_id: str
    settings: TradingAgentsSettings
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "TradingAgentsSettingsResponse":
        """从数据库数据创建响应对象"""
        settings_data = data.get("settings", {})
        settings = TradingAgentsSettings(**settings_data)

        return cls(
            id=str(data["_id"]),
            user_id=data["user_id"],
            settings=settings,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


__all__ = [
    # MCP 服务器配置
    "MCPServerConfig",
    # 智能体配置
    "AgentConfig",
    "AgentConfigSlim",
    "PhaseConfigBase",
    "PhaseConfigBaseSlim",
    "Phase1Config",
    "Phase1ConfigSlim",
    "Phase2Config",
    "Phase2ConfigSlim",
    "Phase3Config",
    "Phase3ConfigSlim",
    "Phase4Config",
    "Phase4ConfigSlim",
    # 用户智能体配置
    "UserAgentConfigCreate",
    "UserAgentConfigUpdate",
    "UserAgentConfigResponse",
    # 用户设置
    "TradingAgentsSettings",
    "TradingAgentsSettingsResponse",
]
