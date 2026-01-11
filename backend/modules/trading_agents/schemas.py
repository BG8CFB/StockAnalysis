"""
TradingAgents 数据模型

包含所有 Pydantic 模型定义：
- 枚举定义（推荐、风险、状态、事件）
- WebSocket 事件模型
- 任务相关模型（创建、响应、阶段配置）
- 报告相关模型
- 智能体配置模型
- 用户设置模型
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field, field_validator, field_serializer


# =============================================================================
# 枚举定义
# =============================================================================

class RecommendationEnum(str, Enum):
    """推荐结果枚举"""
    BUY = "买入"      # 建议买入
    SELL = "卖出"     # 建议卖出
    HOLD = "持有"     # 建议持有


class RiskLevelEnum(str, Enum):
    """风险等级枚举"""
    HIGH = "高"       # 高风险
    MEDIUM = "中"     # 中等风险
    LOW = "低"        # 低风险


class TaskStatusEnum(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"         # 待执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
    STOPPED = "stopped"         # 已停止（中途人工干预）
    EXPIRED = "expired"         # 已过期（24小时未完成）


class EventTypeEnum(str, Enum):
    """WebSocket 事件类型枚举"""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_STOPPED = "task_stopped"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_AGENTS = "phase_agents"
    CONCURRENT_GROUP_STARTED = "concurrent_group_started"
    CONCURRENT_GROUP_COMPLETED = "concurrent_group_completed"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_MESSAGE = "agent_message"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    TOOL_DISABLED = "tool_disabled"
    REPORT_GENERATED = "report_generated"
    AGENT_TRACES = "agent_traces"


# =============================================================================
# WebSocket 事件模型
# =============================================================================

class TaskEvent(BaseModel):
    """任务事件"""
    event_type: EventTypeEnum
    task_id: str
    timestamp: datetime
    data: Dict[str, Any]


# =============================================================================
# 通用响应模型
# =============================================================================

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True


# ConnectionTestResponse 已迁移到核心 AI 模块
from core.ai.model.schemas import ConnectionTestResponse


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
# 任务相关模型
# =============================================================================

class Stage1Config(BaseModel):
    """第一阶段配置"""
    enabled: bool = Field(default=True, description="是否启用第一阶段")
    selected_agents: List[str] = Field(default_factory=list, description="选中的智能体标识符列表")


class DebateConfig(BaseModel):
    """辩论配置"""
    enabled: bool = Field(default=True, description="是否启用辩论")
    rounds: int = Field(default=3, ge=0, le=10, description="辩论轮次")
    concurrency: int = Field(default=1, ge=1, le=2, description="辩论并发数（1=串行，2=并行）")


class Stage2Config(BaseModel):
    """第二阶段配置"""
    enabled: bool = Field(default=True, description="是否启用第二阶段")
    debate: DebateConfig = Field(default_factory=DebateConfig, description="辩论配置")


class Stage3Config(BaseModel):
    """第三阶段配置"""
    enabled: bool = Field(default=True, description="是否启用第三阶段")
    debate: DebateConfig = Field(default_factory=DebateConfig, description="辩论配置")
    concurrency: int = Field(default=3, ge=1, le=3, description="风险评估并发数（1=串行，2=激进和保守一起，3=全部一起）")


class Stage4Config(BaseModel):
    """第四阶段配置"""
    enabled: bool = Field(default=True, description="是否启用第四阶段（强制启用）")


class AnalysisStagesConfig(BaseModel):
    """分析任务阶段配置"""
    stage1: Stage1Config = Field(default_factory=Stage1Config, description="第一阶段配置")
    stage2: Stage2Config = Field(default_factory=Stage2Config, description="第二阶段配置")
    stage3: Stage3Config = Field(default_factory=Stage3Config, description="第三阶段配置")
    stage4: Stage4Config = Field(default_factory=Stage4Config, description="第四阶段配置")


class AnalysisTaskCreate(BaseModel):
    """创建分析任务请求"""
    stock_code: str = Field(..., min_length=1, max_length=20, description="股票代码")
    market: str = Field(default="a_share", description="股票市场：a_share, hong_kong, us")
    trade_date: str = Field(..., min_length=1, max_length=20, description="交易日期")
    data_collection_model: Optional[str] = Field(None, description="数据收集阶段模型ID（第一阶段）")
    debate_model: Optional[str] = Field(None, description="辩论和总结阶段模型ID（第二三四阶段）")
    stages: AnalysisStagesConfig = Field(default_factory=AnalysisStagesConfig, description="阶段配置")


class BatchTaskCreate(BaseModel):
    """创建批量任务请求"""
    stock_codes: List[str] = Field(..., min_length=1, max_length=50, description="股票代码列表")
    market: str = Field(default="a_share", description="股票市场：a_share, hong_kong, us")
    trade_date: str = Field(..., min_length=1, max_length=20, description="交易日期")
    data_collection_model: Optional[str] = Field(None, description="数据收集阶段模型ID（第一阶段）")
    debate_model: Optional[str] = Field(None, description="辩论和总结阶段模型ID（第二三四阶段）")
    stages: AnalysisStagesConfig = Field(default_factory=AnalysisStagesConfig, description="阶段配置")


class UnifiedTaskCreate(BaseModel):
    """统一任务创建请求（支持单股和批量）

    兼容单股和批量分析：
    - 单股：传入单个股票代码或只有一个元素的列表
    - 批量：传入多个股票代码的列表
    """
    stock_codes: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="股票代码列表（1-50个）。单股分析传入单个元素的列表。"
    )
    market: str = Field(default="a_share", description="股票市场：a_share, hong_kong, us")
    trade_date: str = Field(..., min_length=1, max_length=20, description="交易日期")
    data_collection_model: Optional[str] = Field(None, description="数据收集阶段模型ID（第一阶段）")
    debate_model: Optional[str] = Field(None, description="辩论和总结阶段模型ID（第二三四阶段）")
    stages: AnalysisStagesConfig = Field(default_factory=AnalysisStagesConfig, description="阶段配置")


class AnalysisTaskResponse(BaseModel):
    """分析任务响应"""
    id: str
    user_id: str
    stock_code: str
    trade_date: str
    status: TaskStatusEnum
    current_phase: int
    current_agent: Optional[str]
    progress: float

    # 结果
    reports: Dict[str, str]
    final_recommendation: Optional[RecommendationEnum]
    buy_price: Optional[float]
    sell_price: Optional[float]

    # Token 追踪
    token_usage: Dict[str, int]

    # 错误信息
    error_message: Optional[str]
    error_details: Optional[Dict[str, Any]]

    # 时间戳
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expired_at: Optional[datetime]

    # 批量任务关联
    batch_id: Optional[str]

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "AnalysisTaskResponse":
        """从数据库数据创建响应对象"""
        return cls(
            id=str(data["_id"]),
            user_id=data["user_id"],
            stock_code=data["stock_code"],
            trade_date=data["trade_date"],
            status=TaskStatusEnum(data["status"]),
            current_phase=data.get("current_phase", 1),
            current_agent=data.get("current_agent"),
            progress=data.get("progress", 0.0),
            reports=data.get("reports", {}),
            final_recommendation=RecommendationEnum(data["final_recommendation"]) if data.get("final_recommendation") else None,
            buy_price=data.get("buy_price"),
            sell_price=data.get("sell_price"),
            token_usage=data.get("token_usage", {}),
            error_message=data.get("error_message"),
            error_details=data.get("error_details"),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            expired_at=data.get("expired_at"),
            batch_id=data.get("batch_id"),
        )


class BatchTaskResponse(BaseModel):
    """批量任务响应"""
    id: str
    user_id: str
    stock_codes: List[str]
    total_count: int
    completed_count: int
    failed_count: int
    status: TaskStatusEnum
    created_at: datetime
    completed_at: Optional[datetime]


class UnifiedTaskResponse(BaseModel):
    """统一任务创建响应（支持单股和批量）

    根据创建的任务数量返回：
    - 单股：返回 task_id，batch_id 为 null
    - 批量：返回 batch_id，task_id 为 null
    """
    task_id: Optional[str] = Field(None, description="单个任务ID（单股分析时返回）")
    batch_id: Optional[str] = Field(None, description="批量任务ID（批量分析时返回）")
    stock_codes: List[str] = Field(..., description="涉及的股票代码列表")
    total_count: int = Field(..., description="任务总数（单股为1，批量为股票数量）")
    message: str = Field(..., description="操作结果描述")

    @classmethod
    def for_single_task(cls, task_id: str, stock_code: str) -> "UnifiedTaskResponse":
        """创建单个任务响应"""
        return cls(
            task_id=task_id,
            batch_id=None,
            stock_codes=[stock_code],
            total_count=1,
            message=f"已创建单股分析任务，任务ID: {task_id}"
        )

    @classmethod
    def for_batch_task(cls, batch_id: str, stock_codes: List[str]) -> "UnifiedTaskResponse":
        """创建批量任务响应"""
        return cls(
            task_id=None,
            batch_id=batch_id,
            stock_codes=stock_codes,
            total_count=len(stock_codes),
            message=f"已创建批量分析任务，批量ID: {batch_id}，共 {len(stock_codes)} 个股票"
        )


# =============================================================================
# 报告相关模型
# =============================================================================

class AnalysisReportResponse(BaseModel):
    """分析报告响应"""
    id: str
    task_id: str
    user_id: str
    stock_code: str
    trade_date: str
    report_type: str
    report_content: str
    recommendation: Optional[RecommendationEnum]
    buy_price: Optional[float]
    sell_price: Optional[float]
    token_usage: Dict[str, int]
    created_at: datetime

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "AnalysisReportResponse":
        """从数据库数据创建响应对象"""
        return cls(
            id=str(data["_id"]),
            task_id=data["task_id"],
            user_id=data["user_id"],
            stock_code=data["stock_code"],
            trade_date=data["trade_date"],
            report_type=data["report_type"],
            report_content=data["report_content"],
            recommendation=RecommendationEnum(data["recommendation"]) if data.get("recommendation") else None,
            buy_price=data.get("buy_price"),
            sell_price=data.get("sell_price"),
            token_usage=data.get("token_usage", {}),
            created_at=data["created_at"],
        )


class ReportSummaryResponse(BaseModel):
    """报告汇总统计响应"""
    total_reports: int
    buy_count: int
    sell_count: int
    hold_count: int
    avg_buy_price: Optional[float] = None
    avg_sell_price: Optional[float] = None
    recommendation_distribution: Dict[str, int] = {}
    total_token_usage: int = 0


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

            # Debug log (临时关闭以避免日志过多)
            # logger.debug(f"Parsing phase with class {phase_class.__name__}")
            # logger.debug(f"Phase data: {phase_data}")
            # logger.debug(f"Clean data: {clean_data}")

            return phase_class(**clean_data)

        # 解析phase1 (也使用parse_phase来过滤None值)
        phase1_data = data.get("phase1", {})
        # logger.debug(f"Phase1 data from DB: {phase1_data}")  # 临时关闭
        phase1 = parse_phase(phase1_data, Phase1Config)
        # 注意：不再手动转换，保留 MCPServerConfig 对象供内部使用
        # API 响应时会通过 field_serializer 自动转换为字符串列表

        # 解析其他阶段
        phase2 = parse_phase(data.get("phase2", {}), Phase2Config) if data.get("phase2") else None
        phase3 = parse_phase(data.get("phase3", {}), Phase3Config) if data.get("phase3") else None
        phase4 = parse_phase(data.get("phase4", {}), Phase4Config) if data.get("phase4") else None

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


# =============================================================================
# 导出所有模型
# =============================================================================

__all__ = [
    # 枚举
    "RecommendationEnum",
    "RiskLevelEnum",
    "TaskStatusEnum",
    "EventTypeEnum",
    # WebSocket 事件
    "TaskEvent",
    # 通用响应
    "MessageResponse",
    "ConnectionTestResponse",
    # MCP 服务器配置
    "MCPServerConfig",
    # 任务相关
    "Stage1Config",
    "DebateConfig",
    "Stage2Config",
    "Stage3Config",
    "Stage4Config",
    "AnalysisStagesConfig",
    "AnalysisTaskCreate",
    "BatchTaskCreate",
    "UnifiedTaskCreate",
    "AnalysisTaskResponse",
    "BatchTaskResponse",
    "UnifiedTaskResponse",
    # 报告相关
    "AnalysisReportResponse",
    "ReportSummaryResponse",
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
    "UserAgentConfigCreate",
    "UserAgentConfigUpdate",
    "UserAgentConfigResponse",
    # 用户设置
    "TradingAgentsSettings",
    "TradingAgentsSettingsResponse",
]
