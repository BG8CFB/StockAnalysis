"""
监控告警模块

定义告警事件类型、触发器、通道和处理器。
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from core.db.mongodb import mongodb
from modules.trading_agents.api.websocket_manager import get_ws_manager

logger = logging.getLogger(__name__)


# =============================================================================
# 告警事件类型
# =============================================================================

class AlertEventType(str, Enum):
    """告警事件类型"""
    TOOL_LOOP = "tool_loop"           # 工具循环检测
    QUOTA_EXHAUSTED = "quota_exhausted" # 配额耗尽
    MCP_UNAVAILABLE = "mcp_unavailable" # MCP 服务器不可用
    TASK_TIMEOUT = "task_timeout"     # 任务超时
    BATCH_FAILURE = "batch_failure"   # 批量任务失败
    TOKEN_ANOMALY = "token_anomaly"   # Token 异常消耗
    MODEL_ERROR = "model_error"       # 模型调用错误
    TASK_FAILED = "task_failed"       # 任务失败


class AlertSeverity(str, Enum):
    """告警严重程度"""
    INFO = "info"       # 信息
    WARNING = "warning" # 警告
    ERROR = "error"     # 错误
    CRITICAL = "critical" # 严重


# =============================================================================
# 告警事件数据模型
# =============================================================================

@dataclass
class AlertEvent:
    """告警事件"""
    event_type: AlertEventType
    severity: AlertSeverity
    title: str
    description: str
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


# =============================================================================
# 告警触发器
# =============================================================================

class AlertTrigger:
    """
    告警触发器基类

    检测特定条件并触发告警。
    """

    def __init__(self, event_type: AlertEventType, severity: AlertSeverity):
        self.event_type = event_type
        self.severity = severity

    async def check_and_trigger(
        self,
        **context
    ) -> Optional[AlertEvent]:
        """
        检查条件并触发告警

        Args:
            **context: 检查上下文

        Returns:
            告警事件或 None
        """
        raise NotImplementedError


class ToolLoopTrigger(AlertTrigger):
    """工具循环检测触发器"""

    def __init__(self):
        super().__init__(AlertEventType.TOOL_LOOP, AlertSeverity.WARNING)

    async def check_and_trigger(
        self,
        task_id: str,
        user_id: str,
        tool_name: str,
        loop_count: int,
        **context
    ) -> Optional[AlertEvent]:
        if loop_count >= 3:
            return AlertEvent(
                event_type=self.event_type,
                severity=self.severity,
                title=f"工具循环检测触发",
                description=f"任务 {task_id} 中工具 {tool_name} 连续调用 {loop_count} 次",
                user_id=user_id,
                task_id=task_id,
                metadata={"tool_name": tool_name, "loop_count": loop_count}
            )
        return None


class QuotaExhaustedTrigger(AlertTrigger):
    """配额耗尽触发器"""

    def __init__(self):
        super().__init__(AlertEventType.QUOTA_EXHAUSTED, AlertSeverity.ERROR)

    async def check_and_trigger(
        self,
        user_id: str,
        model_id: str,
        **context
    ) -> Optional[AlertEvent]:
        # 检查配额是否耗尽
        from modules.trading_agents.manager.concurrency import get_concurrency_manager
        concurrency = get_concurrency_manager()
        has_quota = await concurrency.try_acquire_public_quota(user_id)

        if not has_quota:
            return AlertEvent(
                event_type=self.event_type,
                severity=self.severity,
                title=f"公共模型配额耗尽",
                description=f"用户 {user_id} 的公共模型配额已耗尽，请稍后重试",
                user_id=user_id,
                metadata={"model_id": model_id}
            )
        # 释放配额（因为只是检查）
        await concurrency.release_public_quota(user_id)
        return None


class TaskTimeoutTrigger(AlertTrigger):
    """任务超时触发器"""

    def __init__(self):
        super().__init__(AlertEventType.TASK_TIMEOUT, AlertSeverity.WARNING)

    async def check_and_trigger(
        self,
        task_id: str,
        user_id: str,
        stock_code: str,
        duration_hours: float,
        **context
    ) -> Optional[AlertEvent]:
        if duration_hours >= 24:
            return AlertEvent(
                event_type=self.event_type,
                severity=self.severity,
                title=f"任务执行超时",
                description=f"任务 {task_id} ({stock_code}) 已执行 {duration_hours:.1f} 小时",
                user_id=user_id,
                task_id=task_id,
                metadata={"stock_code": stock_code, "duration_hours": duration_hours}
            )
        return None


class BatchFailureTrigger(AlertTrigger):
    """批量任务失败触发器"""

    def __init__(self):
        super().__init__(AlertEventType.BATCH_FAILURE, AlertSeverity.ERROR)

    async def check_and_trigger(
        self,
        batch_id: str,
        user_id: str,
        failed_count: int,
        total_count: int,
        **context
    ) -> Optional[AlertEvent]:
        failure_rate = failed_count / total_count if total_count > 0 else 0
        if failure_rate >= 0.5:  # 失败率超过 50%
            return AlertEvent(
                event_type=self.event_type,
                severity=self.severity,
                title=f"批量任务失败率过高",
                description=f"批量任务 {batch_id} 失败率: {failure_rate*100:.1f}% ({failed_count}/{total_count})",
                user_id=user_id,
                metadata={"batch_id": batch_id, "failed_count": failed_count, "total_count": total_count}
            )
        return None


class TokenAnomalyTrigger(AlertTrigger):
    """Token 异常消耗触发器"""

    def __init__(self):
        super().__init__(AlertEventType.TOKEN_ANOMALY, AlertSeverity.WARNING)

    async def check_and_trigger(
        self,
        task_id: str,
        user_id: str,
        token_usage: int,
        expected_max: int,
        **context
    ) -> Optional[AlertEvent]:
        if token_usage > expected_max * 2:  # 超过预期的 2 倍
            return AlertEvent(
                event_type=self.event_type,
                severity=self.severity,
                title=f"Token 消耗异常",
                description=f"任务 {task_id} 消耗 {token_usage} tokens，超过预期 {expected_max} 的 2 倍",
                user_id=user_id,
                task_id=task_id,
                metadata={"token_usage": token_usage, "expected_max": expected_max}
            )
        return None


class ModelErrorTrigger(AlertTrigger):
    """模型调用错误触发器"""

    def __init__(self):
        super().__init__(AlertEventType.MODEL_ERROR, AlertSeverity.ERROR)

    async def check_and_trigger(
        self,
        task_id: str,
        user_id: str,
        model_id: str,
        error_message: str,
        retry_count: int,
        **context
    ) -> Optional[AlertEvent]:
        if retry_count >= 3:
            return AlertEvent(
                event_type=self.event_type,
                severity=self.severity,
                title=f"模型调用失败",
                description=f"任务 {task_id} 调用模型 {model_id} 失败 {retry_count} 次: {error_message}",
                user_id=user_id,
                task_id=task_id,
                metadata={"model_id": model_id, "error_message": error_message, "retry_count": retry_count}
            )
        return None


# =============================================================================
# 告警通道
# =============================================================================

class AlertChannel:
    """
    告警通道基类

    将告警事件发送到特定通道。
    """

    async def send(self, alert: AlertEvent) -> bool:
        """
        发送告警

        Args:
            alert: 告警事件

        Returns:
            是否发送成功
        """
        raise NotImplementedError


class LogAlertChannel(AlertChannel):
    """日志告警通道"""

    async def send(self, alert: AlertEvent) -> bool:
        log_func = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(alert.severity, logger.warning)

        log_func(
            f"[告警] {alert.title}: {alert.description} | "
            f"类型={alert.event_type}, 用户={alert.user_id}, 任务={alert.task_id}"
        )
        return True


class WebSocketAlertChannel(AlertChannel):
    """WebSocket 告警通道"""

    def __init__(self):
        self.ws_manager = None

    async def send(self, alert: AlertEvent) -> bool:
        if self.ws_manager is None:
            self.ws_manager = get_ws_manager()

        if alert.user_id:
            # 发送给特定用户
            await self.ws_manager.broadcast_to_user(
                user_id=alert.user_id,
                event_type="alert",
                data={
                    "type": alert.event_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "description": alert.description,
                    "task_id": alert.task_id,
                    "timestamp": alert.timestamp.isoformat(),
                }
            )
        return True


# =============================================================================
# 告警管理器
# =============================================================================

class AlertManager:
    """
    告警管理器

    管理告警触发器、通道和事件处理。
    """

    def __init__(self):
        self.triggers: Dict[AlertEventType, List[AlertTrigger]] = {}
        self.channels: List[AlertChannel] = []
        self._handlers: Dict[AlertEventType, List[Callable]] = {}

        # 注册默认触发器
        self._register_default_triggers()

        # 注册默认通道
        self.channels.append(LogAlertChannel())
        self.channels.append(WebSocketAlertChannel())

    def _register_default_triggers(self):
        """注册默认触发器"""
        self.triggers[AlertEventType.TOOL_LOOP] = [ToolLoopTrigger()]
        self.triggers[AlertEventType.QUOTA_EXHAUSTED] = [QuotaExhaustedTrigger()]
        self.triggers[AlertEventType.TASK_TIMEOUT] = [TaskTimeoutTrigger()]
        self.triggers[AlertEventType.BATCH_FAILURE] = [BatchFailureTrigger()]
        self.triggers[AlertEventType.TOKEN_ANOMALY] = [TokenAnomalyTrigger()]
        self.triggers[AlertEventType.MODEL_ERROR] = [ModelErrorTrigger()]

    def register_trigger(self, trigger: AlertTrigger):
        """注册自定义触发器"""
        if trigger.event_type not in self.triggers:
            self.triggers[trigger.event_type] = []
        self.triggers[trigger.event_type].append(trigger)

    def register_channel(self, channel: AlertChannel):
        """注册告警通道"""
        self.channels.append(channel)

    def register_handler(self, event_type: AlertEventType, handler: Callable):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def check_and_alert(
        self,
        event_type: AlertEventType,
        **context
    ) -> Optional[AlertEvent]:
        """
        检查条件并触发告警

        Args:
            event_type: 事件类型
            **context: 检查上下文

        Returns:
            触发的告警事件或 None
        """
        triggers = self.triggers.get(event_type, [])
        for trigger in triggers:
            alert = await trigger.check_and_trigger(**context)
            if alert:
                await self._process_alert(alert)
                return alert
        return None

    async def create_alert(
        self,
        event_type: AlertEventType,
        severity: AlertSeverity,
        title: str,
        description: str,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AlertEvent:
        """
        直接创建告警

        Args:
            event_type: 事件类型
            severity: 严重程度
            title: 标题
            description: 描述
            user_id: 用户 ID
            task_id: 任务 ID
            metadata: 额外元数据

        Returns:
            创建的告警事件
        """
        alert = AlertEvent(
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            user_id=user_id,
            task_id=task_id,
            metadata=metadata or {},
        )
        await self._process_alert(alert)
        return alert

    async def _process_alert(self, alert: AlertEvent):
        """处理告警事件"""
        # 保存到数据库
        await self._save_alert(alert)

        # 发送到所有通道
        for channel in self.channels:
            try:
                await channel.send(alert)
            except Exception as e:
                logger.error(f"告警通道发送失败: {e}")

        # 调用注册的处理器
        handlers = self._handlers.get(alert.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")

    async def _save_alert(self, alert: AlertEvent):
        """保存告警到数据库"""
        try:
            await mongodb.database.alerts.insert_one({
                "event_type": alert.event_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "user_id": alert.user_id,
                "task_id": alert.task_id,
                "metadata": alert.metadata,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at,
            })
        except Exception as e:
            logger.error(f"保存告警失败: {e}")

    async def get_user_alerts(
        self,
        user_id: str,
        limit: int = 50,
        unresolved_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取用户告警

        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            unresolved_only: 是否只返回未解决的告警

        Returns:
            告警列表
        """
        query = {"user_id": user_id}
        if unresolved_only:
            query["resolved"] = False

        cursor = mongodb.database.alerts.find(query).sort("timestamp", -1).limit(limit)
        alerts = []
        async for doc in cursor:
            alerts.append({
                "id": str(doc["_id"]),
                "event_type": doc["event_type"],
                "severity": doc["severity"],
                "title": doc["title"],
                "description": doc["description"],
                "timestamp": doc["timestamp"],
                "resolved": doc["resolved"],
                "metadata": doc.get("metadata", {}),
            })
        return alerts

    async def resolve_alert(self, alert_id: str) -> bool:
        """
        解决告警

        Args:
            alert_id: 告警 ID

        Returns:
            是否成功
        """
        try:
            from bson import ObjectId
            result = await mongodb.database.alerts.update_one(
                {"_id": ObjectId(alert_id)},
                {"$set": {"resolved": True, "resolved_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return False


# =============================================================================
# 全局告警管理器实例
# =============================================================================

_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
