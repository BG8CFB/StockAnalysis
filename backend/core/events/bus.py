from typing import Dict, List, Callable, Any, Type
import asyncio
import logging
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Event(BaseModel):
    """基础事件模型"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()
    source_module: str = "core"


class EventBus:
    """事件总线 - 模块间通信的核心"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.info(f"Unsubscribed from event: {event_type}")
            except ValueError:
                logger.warning(f"Callback not found for event: {event_type}")

    async def publish(self, event_type: str, data: Dict[str, Any], source_module: str = "core"):
        """发布事件"""
        event = Event(
            event_type=event_type,
            data=data,
            source_module=source_module
        )

        # 记录事件历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # 异步通知所有订阅者
        if event_type in self._subscribers:
            tasks = []
            for callback in self._subscribers[event_type]:
                try:
                    tasks.append(callback(event))
                except Exception as e:
                    logger.error(f"Error preparing callback for event {event_type}: {e}")

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Published event: {event_type} from {source_module}")

    def get_event_history(self, event_type: str = None) -> List[Event]:
        """获取事件历史"""
        if event_type:
            return [event for event in self._event_history if event.event_type == event_type]
        return self._event_history.copy()

    def get_subscribed_events(self) -> List[str]:
        """获取已订阅的事件类型"""
        return list(self._subscribers.keys())


# 全局事件总线实例
event_bus = EventBus()