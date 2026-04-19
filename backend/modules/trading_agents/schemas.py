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

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

from core.ai.model.schemas import ConnectionTestResponse

# =============================================================================
# 通用辅助函数
# =============================================================================


def parse_datetime(value: Any) -> Optional[datetime]:
    """
    解析 datetime，兼容多种格式

    支持格式：
    - Python datetime 对象（直接返回）
    - MongoDB 扩展 JSON 格式: {'$date': '2026-01-13T06:59:30.154Z'}
    - ISO 8601 字符串

    Args:
        value: 输入值

    Returns:
        datetime 对象，解析失败返回 None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, dict) and "$date" in value:
        # MongoDB 扩展 JSON 格式
        try:

            from dateutil import parser  # type: ignore[import-untyped]

            return parser.isoparse(value["$date"])  # type: ignore[no-any-return]
        except Exception:
            return None
    if isinstance(value, str):
        # ISO 8601 字符串
        try:
            from dateutil import parser  # type: ignore[import-untyped]

            return parser.isoparse(value)  # type: ignore[no-any-return]
        except Exception:
            return None
    return None


# =============================================================================
# 枚举定义
# =============================================================================


class RecommendationEnum(str, Enum):
    """推荐结果枚举"""

    BUY = "买入"  # 建议买入
    SELL = "卖出"  # 建议卖出
    HOLD = "持有"  # 建议持有


class RiskLevelEnum(str, Enum):
    """风险等级枚举"""

    HIGH = "高"  # 高风险
    MEDIUM = "中"  # 中等风险
    LOW = "低"  # 低风险


class TaskStatusEnum(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    STOPPED = "stopped"  # 已停止（中途人工干预）
    EXPIRED = "expired"  # 已过期（24小时未完成）


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


# =============================================================================
# MCP 服务器配置模型
# =============================================================================


class MCPServerConfig(BaseModel):
    """MCP 服务器配置（支持容错策略）"""

    name: str = Field(..., description="服务器名称")
    required: bool = Field(default=True, description="是否必需（必需服务器失败将阻止任务启动）")


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
    concurrency: int = Field(
        default=3, ge=1, le=3, description="风险评估并发数（1=串行，2=激进和保守一起，3=全部一起）"
    )


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
    market: str = Field(default="A_STOCK", description="股票市场: A_STOCK, US_STOCK, HK_STOCK")
    trade_date: str = Field(..., min_length=1, max_length=20, description="交易日期")
    data_collection_model: Optional[str] = Field(None, description="数据收集阶段模型ID（第一阶段）")
    debate_model: Optional[str] = Field(None, description="辩论和总结阶段模型ID（第二三四阶段）")
    stages: AnalysisStagesConfig = Field(
        default_factory=AnalysisStagesConfig, description="阶段配置"
    )


class BatchTaskCreate(BaseModel):
    """创建批量任务请求"""

    stock_codes: List[str] = Field(..., min_length=1, max_length=50, description="股票代码列表")
    market: str = Field(default="A_STOCK", description="股票市场: A_STOCK, US_STOCK, HK_STOCK")
    trade_date: str = Field(..., min_length=1, max_length=20, description="交易日期")
    data_collection_model: Optional[str] = Field(None, description="数据收集阶段模型ID（第一阶段）")
    debate_model: Optional[str] = Field(None, description="辩论和总结阶段模型ID（第二三四阶段）")
    stages: AnalysisStagesConfig = Field(
        default_factory=AnalysisStagesConfig, description="阶段配置"
    )
    batch_name: Optional[str] = Field(
        None, max_length=100, description="批量任务名称（可选，用于分类和识别批量任务）"
    )


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
        description="股票代码列表（1-50个）。单股分析传入单个元素的列表。",
    )
    market: str = Field(default="A_STOCK", description="股票市场: A_STOCK, US_STOCK, HK_STOCK")
    trade_date: str = Field(..., min_length=1, max_length=20, description="交易日期")
    data_collection_model: Optional[str] = Field(None, description="数据收集阶段模型ID（第一阶段）")
    debate_model: Optional[str] = Field(None, description="辩论和总结阶段模型ID（第二三四阶段）")
    stages: AnalysisStagesConfig = Field(
        default_factory=AnalysisStagesConfig, description="阶段配置"
    )
    batch_name: Optional[str] = Field(
        None, max_length=100, description="批量任务名称（可选，用于分类和识别批量任务）"
    )


class AnalysisTaskResponse(BaseModel):
    """分析任务响应"""

    id: str
    user_id: str
    stock_code: str
    market: str = Field(default="A_STOCK", description="股票市场: A_STOCK, US_STOCK, HK_STOCK")
    trade_date: str
    status: TaskStatusEnum
    current_phase: int
    current_agent: Optional[str]
    progress: float

    # 结果
    reports: Dict[str, str]
    final_report: Optional[str] = Field(None, description="最终报告（方便前端直接访问）")
    final_recommendation: Optional[RecommendationEnum]
    buy_price: Optional[float]
    sell_price: Optional[float]
    risk_level: Optional[str] = Field(None, description="风险等级：高, 中, 低")

    # Token 追踪
    token_usage: Dict[str, int]

    # 错误信息
    error_message: Optional[str]
    error_details: Optional[Dict[str, Any]]

    # 执行记录
    phase_executions: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="阶段执行记录"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="工具调用记录"
    )

    # 时间戳
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expired_at: Optional[datetime]

    # 批量任务关联
    batch_id: Optional[str]
    batch_name: Optional[str] = Field(None, description="批量任务名称")

    @field_serializer("created_at", "started_at", "completed_at", "expired_at")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """序列化 datetime 为 UTC 格式字符串（带 'Z' 后缀）"""
        if dt is None:
            return None
        # 确保 datetime 是 naive 的（无时区信息），然后添加 'Z' 表示 UTC
        if dt.tzinfo is not None:
            # 如果有时区信息，转换为 UTC
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            # naive datetime 被当作 UTC 处理
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "AnalysisTaskResponse":
        """从数据库数据创建响应对象"""
        # 提取 final_report（优先从 reports.final_report，如果不存在则为 None）
        reports = data.get("reports", {})
        final_report = reports.get("final_report") if isinstance(reports, dict) else None

        return cls(
            id=str(data["_id"]),
            user_id=data["user_id"],
            stock_code=data["stock_code"],
            market=data.get("market", "A_STOCK"),
            trade_date=data["trade_date"],
            status=TaskStatusEnum(data["status"]),
            current_phase=data.get("current_phase", 1),
            current_agent=data.get("current_agent"),
            progress=data.get("progress", 0.0),
            reports=reports,
            final_report=final_report,
            final_recommendation=(
                RecommendationEnum(data["final_recommendation"])
                if data.get("final_recommendation")
                else None
            ),
            buy_price=data.get("buy_price"),
            sell_price=data.get("sell_price"),
            risk_level=data.get("risk_level"),
            token_usage=data.get("token_usage", {}),
            error_message=data.get("error_message"),
            error_details=data.get("error_details"),
            created_at=parse_datetime(data.get("created_at")) or datetime.now(timezone.utc),
            started_at=parse_datetime(data.get("started_at")),
            completed_at=parse_datetime(data.get("completed_at")),
            expired_at=parse_datetime(data.get("expired_at")),
            batch_id=data.get("batch_id"),
            batch_name=data.get("batch_name"),
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
            message=f"已创建单股分析任务，任务ID: {task_id}",
        )

    @classmethod
    def for_batch_task(cls, batch_id: str, stock_codes: List[str]) -> "UnifiedTaskResponse":
        """创建批量任务响应"""
        return cls(
            task_id=None,
            batch_id=batch_id,
            stock_codes=stock_codes,
            total_count=len(stock_codes),
            message=f"已创建批量分析任务，批量ID: {batch_id}，共 {len(stock_codes)} 个股票",
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
            recommendation=(
                RecommendationEnum(data["recommendation"]) if data.get("recommendation") else None
            ),
            buy_price=data.get("buy_price"),
            sell_price=data.get("sell_price"),
            token_usage=data.get("token_usage", {}),
            created_at=parse_datetime(data.get("created_at")) or datetime.now(timezone.utc),
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

    # 配置支持字段别名（驼峰命名与蛇形命名兼容）
    model_config = {"populate_by_name": True}

    slug: str = Field(..., min_length=1, max_length=50, description="唯一标识符")
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    # 支持驼峰命名 (roleDefinition) 和蛇形命名 (role_definition)
    role_definition: Optional[str] = Field(
        None,
        min_length=1,
        max_length=10000,
        description="角色定义（系统提示词）",
        alias="roleDefinition",
    )
    # 支持驼峰命名 (whenToUse) 和蛇形命名 (when_to_use)
    when_to_use: Optional[str] = Field(
        default="", max_length=500, description="使用场景说明", alias="whenToUse"
    )
    enabled_mcp_servers: List[MCPServerConfig] = Field(
        default_factory=list, description="启用的 MCP 服务器（支持配置必需性）"
    )
    enabled_local_tools: List[str] = Field(default_factory=list, description="启用的本地工具")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator("enabled_mcp_servers", mode="before")
    @classmethod
    def convert_mcp_servers(cls, v: Any) -> Any:
        """向后兼容：自动将字符串/字典列表转换为 MCPServerConfig 列表"""
        if not v:
            return []
        # 如果已经是 MCPServerConfig 列表，直接返回
        if isinstance(v, list) and len(v) > 0:
            if isinstance(v[0], MCPServerConfig):
                return v
            # 如果是字符串列表，转换
            if isinstance(v[0], str):
                return [MCPServerConfig(name=name, required=True) for name in v]
            # 如果是字典列表，尝试解析
            if isinstance(v[0], dict):
                try:
                    return [MCPServerConfig(**item) for item in v]
                except Exception:
                    pass
        return v

    @field_serializer("enabled_mcp_servers")
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
                result.append(server.get("name", ""))
        return result


class AgentConfigSlim(BaseModel):
    """单个智能体配置（精简版，不含提示词）

    用于分析页面，不暴露敏感的 role_definition。
    普通用户不应看到系统提示词，避免泄露业务逻辑。
    """

    # 配置支持字段别名（驼峰命名与蛇形命名兼容）
    model_config = {"populate_by_name": True}

    slug: str = Field(..., min_length=1, max_length=50, description="唯一标识符")
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    # 支持驼峰命名 (whenToUse) 和蛇形命名 (when_to_use)
    when_to_use: Optional[str] = Field(
        default="", max_length=500, description="使用场景说明", alias="whenToUse"
    )
    enabled_mcp_servers: List[MCPServerConfig] = Field(
        default_factory=list, description="启用的 MCP 服务器（支持配置必需性）"
    )
    enabled_local_tools: List[str] = Field(default_factory=list, description="启用的本地工具")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator("enabled_mcp_servers", mode="before")
    @classmethod
    def convert_mcp_servers(cls, v: Any) -> Any:
        """向后兼容：自动将字符串/字典列表转换为 MCPServerConfig 列表"""
        if not v:
            return []
        if isinstance(v, list) and len(v) > 0:
            if isinstance(v[0], MCPServerConfig):
                return v
            if isinstance(v[0], str):
                return [MCPServerConfig(name=name, required=True) for name in v]
            if isinstance(v[0], dict):
                try:
                    return [MCPServerConfig(**item) for item in v]
                except Exception:
                    pass
        return v

    @field_serializer("enabled_mcp_servers")
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
                result.append(server.get("name", ""))
        return result


class PhaseConfigBase(BaseModel):
    """阶段配置基础模型（包含公共字段）"""

    enabled: bool = Field(default=True, description="是否启用该阶段")
    agents: List[AgentConfig] = Field(default_factory=list, description="智能体列表")


class PhaseConfigBaseSlim(BaseModel):
    """阶段配置基础模型（精简版，不含提示词）"""

    enabled: bool = Field(default=True, description="是否启用该阶段")
    agents: List[AgentConfigSlim] = Field(default_factory=list, description="智能体列表（精简版）")


class Phase1Config(PhaseConfigBase):
    """第一阶段配置（信息收集与基础分析）"""

    max_concurrency: int = Field(default=3, ge=1, le=10, description="智能体最大并发数")


class Phase1ConfigSlim(PhaseConfigBaseSlim):
    """第一阶段配置（精简版）"""

    max_concurrency: int = Field(default=3, ge=1, le=10, description="智能体最大并发数")


class Phase2Config(PhaseConfigBase):
    """第二阶段配置（多空博弈与投资决策）"""

    debate_rounds: Optional[int] = Field(None, ge=1, le=10, description="辩论轮数")


class Phase2ConfigSlim(PhaseConfigBaseSlim):
    """第二阶段配置（精简版）"""

    debate_rounds: Optional[int] = Field(None, ge=1, le=10, description="辩论轮数")


class Phase3Config(PhaseConfigBase):
    """第三阶段配置（策略风格与风险评估）"""

    pass


class Phase3ConfigSlim(PhaseConfigBaseSlim):
    """第三阶段配置（精简版）"""

    pass


class Phase4Config(PhaseConfigBase):
    """第四阶段配置（总结智能体 - 必须执行）"""

    enabled: bool = Field(default=True, description="第四阶段必须执行（固定为true）")

    # 禁止修改 enabled 的验证
    @field_validator("enabled")
    @classmethod
    def phase4_must_be_enabled(cls, v: bool) -> bool:
        if not v:
            raise ValueError("第四阶段（总结智能体）必须启用，不能禁用")
        return v


class Phase4ConfigSlim(PhaseConfigBaseSlim):
    """第四阶段配置（精简版）"""

    enabled: bool = Field(default=True, description="第四阶段必须执行（固定为true）")


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
        from typing import Type

        _logger = logging.getLogger(__name__)

        def parse_phase(
            phase_data: Dict[str, Any], phase_class: Type[PhaseConfigBase]
        ) -> PhaseConfigBase:
            """解析阶段配置，处理可能的None值"""
            # 过滤掉None值
            clean_data: Dict[str, Any] = {}
            for key, value in phase_data.items():
                if value is not None:
                    clean_data[key] = value

            return phase_class(**clean_data)

        # 解析phase1 (也使用parse_phase来过滤None值)
        phase1_data = data.get("phase1", {})
        phase1_parsed = parse_phase(phase1_data, Phase1Config)
        phase1: Phase1Config = Phase1Config(**phase1_parsed.model_dump())

        # 解析其他阶段
        phase2: Optional[Phase2Config] = None
        if data.get("phase2"):
            phase2_parsed = parse_phase(data.get("phase2", {}), Phase2Config)
            phase2 = Phase2Config(**phase2_parsed.model_dump())

        phase3: Optional[Phase3Config] = None
        if data.get("phase3"):
            phase3_parsed = parse_phase(data.get("phase3", {}), Phase3Config)
            phase3 = Phase3Config(**phase3_parsed.model_dump())

        phase4: Optional[Phase4Config] = None
        if data.get("phase4"):
            phase4_parsed = parse_phase(data.get("phase4", {}), Phase4Config)
            phase4 = Phase4Config(**phase4_parsed.model_dump())

        return cls(
            id=str(data["_id"]),
            user_id=data["user_id"],
            is_public=data.get("is_public", False),
            is_customized=data.get("is_customized", False),
            phase1=phase1,
            phase2=phase2,
            phase3=phase3,
            phase4=phase4,
            created_at=parse_datetime(data.get("created_at")) or datetime.now(timezone.utc),
            updated_at=parse_datetime(data.get("updated_at")) or datetime.now(timezone.utc),
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
            created_at=parse_datetime(data.get("created_at")) or datetime.now(timezone.utc),
            updated_at=parse_datetime(data.get("updated_at")) or datetime.now(timezone.utc),
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
