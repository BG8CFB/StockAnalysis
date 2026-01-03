"""
TradingAgents 数据模型

拆分后的数据模型模块，按功能组织：
- common.py: 通用模型（枚举、WebSocket 事件、通用响应）
- task.py: 任务相关模型
- report.py: 报告相关模型
- config.py: 配置相关模型（智能体配置、用户设置）
"""

# 从 common 导入
from .common import (
    RecommendationEnum,
    RiskLevelEnum,
    TaskStatusEnum,
    EventTypeEnum,
    TaskEvent,
    MessageResponse,
    ConnectionTestResponse,
)

# 从 task 导入
from .task import (
    Stage1Config,
    DebateConfig,
    Stage2Config,
    Stage3Config,
    Stage4Config,
    AnalysisStagesConfig,
    AnalysisTaskCreate,
    BatchTaskCreate,
    UnifiedTaskCreate,
    AnalysisTaskResponse,
    BatchTaskResponse,
    UnifiedTaskResponse,
)

# 从 report 导入
from .report import (
    AnalysisReportResponse,
    ReportSummaryResponse,
)

# 从 config 导入
from .config import (
    MCPServerConfig,
    AgentConfig,
    AgentConfigSlim,
    PhaseConfigBase,
    PhaseConfigBaseSlim,
    Phase1Config,
    Phase1ConfigSlim,
    Phase2Config,
    Phase2ConfigSlim,
    Phase3Config,
    Phase3ConfigSlim,
    Phase4Config,
    Phase4ConfigSlim,
    UserAgentConfigCreate,
    UserAgentConfigUpdate,
    UserAgentConfigResponse,
    TradingAgentsSettings,
    TradingAgentsSettingsResponse,
)

__all__ = [
    # common
    "RecommendationEnum",
    "RiskLevelEnum",
    "TaskStatusEnum",
    "EventTypeEnum",
    "TaskEvent",
    "MessageResponse",
    "ConnectionTestResponse",
    # task
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
    # report
    "AnalysisReportResponse",
    "ReportSummaryResponse",
    # config
    "MCPServerConfig",
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
    "TradingAgentsSettings",
    "TradingAgentsSettingsResponse",
]
