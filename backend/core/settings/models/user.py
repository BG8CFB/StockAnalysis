"""
统一用户配置管理数据模型

整合所有用户配置到一个统一的结构中，包括：
- 核心设置（UI 主题、语言、时区）
- 通知设置
- TradingAgents 模块设置
- 配额信息
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from core.db.models import PyObjectId

logger = logging.getLogger(__name__)


# =============================================================================
# 核心设置
# =============================================================================


class CoreSettings(BaseModel):
    """核心 UI 设置"""

    theme: str = Field(default="light", description="主题：light, dark, auto")
    language: str = Field(default="zh-CN", description="语言")
    timezone: str = Field(default="Asia/Shanghai", description="时区")

    # 兼容旧字段
    watchlist: list = Field(default_factory=list, description="自选股列表")


# =============================================================================
# 通知设置
# =============================================================================


class NotificationSettings(BaseModel):
    """通知设置"""

    enabled: bool = Field(default=True, description="是否启用通知")
    email_alerts: bool = Field(default=False, description="邮件提醒")
    browser_notifications: bool = Field(default=True, description="浏览器通知")
    task_completed: bool = Field(default=True, description="任务完成通知")
    task_failed: bool = Field(default=True, description="任务失败通知")
    quota_warning: bool = Field(default=True, description="配额预警通知")


# =============================================================================
# TradingAgents 模块设置
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

    # 流程默认配置
    default_phase1_agents: list = Field(
        default_factory=list,
        description="第一阶段默认选中的智能体 slug 列表"
    )
    default_phase2_enabled: bool = Field(default=True, description="第二阶段默认是否启用")
    default_phase3_enabled: bool = Field(default=False, description="第三阶段默认是否启用")

    # 其他配置
    task_expiry_hours: int = Field(default=24, ge=1, le=168, description="任务过期时间（小时）")
    archive_days: int = Field(default=30, ge=7, le=365, description="报告归档天数")
    enable_loop_detection: bool = Field(default=True, description="启用工具循环检测")
    enable_progress_events: bool = Field(default=True, description="启用实时进度推送")


# =============================================================================
# 配额信息
# =============================================================================


class UserQuotaInfo(BaseModel):
    """用户配额信息"""

    tasks_used: int = Field(default=0, ge=0, description="本月已使用任务数")
    tasks_limit: int = Field(default=100, ge=0, description="每月任务限制")
    reports_count: int = Field(default=0, ge=0, description="总报告数")
    reports_limit: int = Field(default=1000, ge=0, description="报告总数限制")
    storage_used_mb: float = Field(default=0.0, ge=0, description="已用存储（MB）")
    storage_limit_mb: int = Field(default=500, ge=0, description="存储限制（MB）")
    concurrent_tasks: int = Field(default=0, ge=0, description="当前并发任务数")
    concurrent_limit: int = Field(default=5, ge=0, description="并发任务限制")

    @property
    def tasks_remaining(self) -> int:
        """剩余任务数"""
        return max(0, self.tasks_limit - self.tasks_used)

    @property
    def tasks_usage_percent(self) -> float:
        """任务使用百分比"""
        if self.tasks_limit == 0:
            return 0.0
        return (self.tasks_used / self.tasks_limit) * 100

    @property
    def storage_usage_percent(self) -> float:
        """存储使用百分比"""
        if self.storage_limit_mb == 0:
            return 0.0
        return (self.storage_used_mb / self.storage_limit_mb) * 100

    @property
    def is_near_quota_limit(self) -> bool:
        """是否接近配额限制（80%）"""
        return self.tasks_usage_percent >= 80 or self.storage_usage_percent >= 80


# =============================================================================
# 统一用户配置
# =============================================================================


class UserSettings(BaseModel):
    """统一用户配置"""

    user_id: PyObjectId

    # 各模块配置
    core_settings: CoreSettings = Field(default_factory=CoreSettings)
    notification_settings: NotificationSettings = Field(default_factory=NotificationSettings)
    trading_agents_settings: TradingAgentsSettings = Field(default_factory=TradingAgentsSettings)

    # 配额信息
    quota_info: UserQuotaInfo = Field(default_factory=UserQuotaInfo)

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# 请求/响应模型
# =============================================================================


class CoreSettingsUpdate(BaseModel):
    """更新核心设置请求"""

    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    watchlist: Optional[list] = None


class NotificationSettingsUpdate(BaseModel):
    """更新通知设置请求"""

    enabled: Optional[bool] = None
    email_alerts: Optional[bool] = None
    browser_notifications: Optional[bool] = None
    task_completed: Optional[bool] = None
    task_failed: Optional[bool] = None
    quota_warning: Optional[bool] = None


class TradingAgentsSettingsUpdate(BaseModel):
    """更新 TradingAgents 设置请求"""

    data_collection_model_id: Optional[str] = None
    debate_model_id: Optional[str] = None
    default_debate_rounds: Optional[int] = None
    max_debate_rounds: Optional[int] = None
    phase_timeout_minutes: Optional[int] = None
    agent_timeout_minutes: Optional[int] = None
    tool_timeout_seconds: Optional[int] = None
    task_expiry_hours: Optional[int] = None
    archive_days: Optional[int] = None
    enable_loop_detection: Optional[bool] = None
    enable_progress_events: Optional[bool] = None
    # 流程默认配置
    default_phase1_agents: Optional[list] = None
    default_phase2_enabled: Optional[bool] = None
    default_phase3_enabled: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    """用户配置响应"""

    id: str
    user_id: str
    core_settings: CoreSettings
    notification_settings: NotificationSettings
    trading_agents_settings: TradingAgentsSettings
    quota_info: UserQuotaInfo
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "UserSettingsResponse":
        """
        从数据库数据创建响应对象

        处理可能存在的无效数据：
        - 确保 concurrent_tasks >= 0（修复历史负数问题）
        - 确保其他数值字段 >= 0
        - 处理缓存数据缺失 _id 的情况
        - 处理 MongoDB 扩展 JSON 格式的 datetime
        """
        # 检查必要字段
        if "user_id" not in data:
            # 尝试从 _id 推断或抛出更明确的错误
            # 这里抛出 ValueError 会被上层捕获并回退到数据库查询
            raise ValueError("缓存数据缺少 user_id 字段，这可能是旧版缓存数据")

        # 辅助函数：处理 datetime 字段（兼容 MongoDB 扩展 JSON 格式）
        def parse_datetime(value: Any) -> datetime:
            """解析 datetime，兼容 Python datetime 和 MongoDB 扩展 JSON 格式"""
            if isinstance(value, datetime):
                return value
            if isinstance(value, dict) and "$date" in value:
                # MongoDB 扩展 JSON 格式: {'$date': '2026-01-13T06:59:30.154Z'}
                from datetime import datetime as dt
                from dateutil import parser

                return parser.isoparse(value["$date"])
            # 默认返回当前时间
            return datetime.utcnow()

        # 获取并清理 quota_info 数据
        quota_data = data.get("quota_info", {})

        # 兼容缓存数据：如果没有 _id，使用生成的 UUID
        doc_id = data.get("_id")
        if doc_id is None:
            import uuid

            doc_id = str(uuid.uuid4())

        # 处理缺失 user_id 的情况（兼容旧版缓存）
        user_id = data.get("user_id")
        if user_id is None:
            logger.error("缓存数据缺少 user_id 字段，这可能是旧版缓存数据")
            raise ValueError(
                "Invalid cached data: missing user_id field. Please clear cache and reload."
            )

        # 修复可能存在的负数值（确保 >= 0）
        if "concurrent_tasks" in quota_data and quota_data["concurrent_tasks"] < 0:
            quota_data["concurrent_tasks"] = 0
        if "tasks_used" in quota_data and quota_data["tasks_used"] < 0:
            quota_data["tasks_used"] = 0
        if "reports_count" in quota_data and quota_data["reports_count"] < 0:
            quota_data["reports_count"] = 0
        if "storage_used_mb" in quota_data and quota_data["storage_used_mb"] < 0:
            quota_data["storage_used_mb"] = 0.0

        return cls(
            id=str(doc_id),
            user_id=str(user_id),
            core_settings=CoreSettings(**data.get("core_settings", {})),
            notification_settings=NotificationSettings(**data.get("notification_settings", {})),
            trading_agents_settings=TradingAgentsSettings(
                **data.get("trading_agents_settings", {})
            ),
            quota_info=UserQuotaInfo(**quota_data),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )


# =============================================================================
# 配置导入导出模型
# =============================================================================


class SettingsExport(BaseModel):
    """配置导出格式（不包含敏感信息）"""

    version: str = Field(default="1.0", description="配置版本")
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    core_settings: CoreSettings
    notification_settings: NotificationSettings
    trading_agents_settings: TradingAgentsSettings
    # 不包含 quota_info（配额信息不应导出）


class SettingsImport(BaseModel):
    """配置导入请求"""

    version: str = Field(..., description="配置版本")
    core_settings: Optional[CoreSettings] = None
    notification_settings: Optional[NotificationSettings] = None
    trading_agents_settings: Optional[TradingAgentsSettings] = None
    merge_strategy: str = Field(
        default="merge", description="合并策略：merge=合并, replace=完全覆盖"
    )
