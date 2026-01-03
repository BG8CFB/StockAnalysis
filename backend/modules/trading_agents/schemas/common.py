"""
通用数据模型

包含枚举定义、通用响应模型、WebSocket 事件模型等。
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any

from pydantic import BaseModel


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


# =============================================================================
# WebSocket 事件模型
# =============================================================================

class EventTypeEnum(str, Enum):
    """WebSocket 事件类型枚举"""
    TASK_STARTED = "task_started"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    TOOL_DISABLED = "tool_disabled"
    REPORT_GENERATED = "report_generated"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_STOPPED = "task_stopped"


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


__all__ = [
    # 枚举
    "RecommendationEnum",
    "RiskLevelEnum",
    "TaskStatusEnum",
    # WebSocket 事件
    "EventTypeEnum",
    "TaskEvent",
    # 通用响应
    "MessageResponse",
    "ConnectionTestResponse",
]
