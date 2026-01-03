"""
任务相关数据模型

包含任务创建、响应等模型。
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from .common import RecommendationEnum, TaskStatusEnum


# =============================================================================
# 分析任务阶段配置模型
# =============================================================================

class Stage1Config(BaseModel):
    """第一阶段配置"""
    enabled: bool = Field(default=True, description="是否启用第一阶段")
    selected_agents: List[str] = Field(default_factory=list, description="选中的智能体标识符列表")


class DebateConfig(BaseModel):
    """辩论配置"""
    enabled: bool = Field(default=True, description="是否启用辩论")
    rounds: int = Field(default=3, ge=0, le=10, description="辩论轮次")


class Stage2Config(BaseModel):
    """第二阶段配置"""
    enabled: bool = Field(default=True, description="是否启用第二阶段")
    debate: DebateConfig = Field(default_factory=DebateConfig, description="辩论配置")


class Stage3Config(BaseModel):
    """第三阶段配置"""
    enabled: bool = Field(default=True, description="是否启用第三阶段")
    debate: DebateConfig = Field(default_factory=DebateConfig, description="辩论配置")


class Stage4Config(BaseModel):
    """第四阶段配置"""
    enabled: bool = Field(default=True, description="是否启用第四阶段（强制启用）")


class AnalysisStagesConfig(BaseModel):
    """分析任务阶段配置"""
    stage1: Stage1Config = Field(default_factory=Stage1Config, description="第一阶段配置")
    stage2: Stage2Config = Field(default_factory=Stage2Config, description="第二阶段配置")
    stage3: Stage3Config = Field(default_factory=Stage3Config, description="第三阶段配置")
    stage4: Stage4Config = Field(default_factory=Stage4Config, description="第四阶段配置")


# =============================================================================
# 任务创建模型
# =============================================================================

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


# =============================================================================
# 统一任务创建模型
# =============================================================================

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


# =============================================================================
# 任务响应模型
# =============================================================================

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


__all__ = [
    # 阶段配置
    "Stage1Config",
    "DebateConfig",
    "Stage2Config",
    "Stage3Config",
    "Stage4Config",
    "AnalysisStagesConfig",
    # 任务创建
    "AnalysisTaskCreate",
    "BatchTaskCreate",
    "UnifiedTaskCreate",
    # 任务响应
    "AnalysisTaskResponse",
    "BatchTaskResponse",
    "UnifiedTaskResponse",
]
