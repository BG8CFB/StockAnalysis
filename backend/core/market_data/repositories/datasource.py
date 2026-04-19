"""
数据源配置和状态监控 Repository
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.market_data.models.datasource import (
    DataSourceHealthStatus,
    DataSourceStatus,
    DataSourceStatusHistory,
    DataSourceType,
    SystemDataSourceConfig,
    UserDataSourceConfig,
)

from .base import BaseRepository

logger = logging.getLogger(__name__)


class SystemDataSourceRepository(BaseRepository):
    """系统公共数据源配置 Repository"""

    def __init__(self) -> None:
        super().__init__("system_data_sources")

    async def create_indexes(self) -> None:
        """创建索引"""
        await self.create_index([("source_id", 1), ("market", 1)], unique=True)
        await self.create_index([("enabled", 1), ("priority", 1)])

    async def upsert_config(self, config: SystemDataSourceConfig) -> int:
        """
        新增或更新系统数据源配置

        Args:
            config: 数据源配置

        Returns:
            修改的文档数量（0=新增, 1=更新）
        """
        filter_query = {"source_id": config.source_id, "market": config.market}
        data = config.model_dump()
        data["updated_at"] = datetime.now()

        return await self.upsert_one(filter_query, data)

    async def get_config(self, source_id: str, market: str) -> Optional[Dict[str, Any]]:
        """
        获取数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            配置数据，未找到返回None
        """
        filter_query = {"source_id": source_id, "market": market}
        return await self.find_one(filter_query)

    async def get_enabled_configs(
        self, market: str, enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取启用的数据源配置列表，按优先级排序

        Args:
            market: 市场类型
            enabled_only: 是否只返回启用的配置

        Returns:
            配置列表
        """
        filter_query = {"market": market, "enabled": enabled_only}
        return await self.find_many(filter_query, sort=[("priority", 1)])

    async def update_test_status(
        self, source_id: str, market: str, status: str, error: Optional[str] = None
    ) -> int:
        """
        更新测试状态

        Args:
            source_id: 数据源标识
            market: 市场类型
            status: 测试状态 (success/failed)
            error: 错误信息

        Returns:
            修改的文档数量
        """
        filter_query = {"source_id": source_id, "market": market}
        data = {"last_tested_at": datetime.now(), "test_status": status, "last_error": error}
        result = await self.collection.update_one(filter_query, {"$set": data})
        return result.modified_count

    async def update_config(self, source_id: str, market: str, updates: Dict[str, Any]) -> int:
        """
        更新数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型
            updates: 更新的字段

        Returns:
            修改的文档数量
        """
        filter_query = {"source_id": source_id, "market": market}
        updates["updated_at"] = datetime.now()
        result = await self.collection.update_one(filter_query, {"$set": updates})
        return result.modified_count

    async def delete_config(self, source_id: str, market: str) -> int:
        """
        删除数据源配置

        Args:
            source_id: 数据源标识
            market: 市场类型

        Returns:
            删除的文档数量
        """
        filter_query = {"source_id": source_id, "market": market}
        result = await self.collection.delete_one(filter_query)
        return result.deleted_count


class UserDataSourceRepository(BaseRepository):
    """用户个人数据源配置 Repository"""

    def __init__(self) -> None:
        super().__init__("user_data_sources")

    async def create_indexes(self) -> None:
        """创建索引"""
        await self.create_index([("user_id", 1), ("source_id", 1), ("market", 1)], unique=True)
        await self.create_index([("user_id", 1), ("enabled", 1), ("priority", 1)])

    async def upsert_config(self, config: UserDataSourceConfig) -> int:
        """
        新增或更新用户数据源配置

        Args:
            config: 数据源配置

        Returns:
            修改的文档数量（0=新增, 1=更新）
        """
        filter_query = {
            "user_id": config.user_id,
            "source_id": config.source_id,
            "market": config.market,
        }
        data = config.model_dump()
        data["updated_at"] = datetime.now()

        return await self.upsert_one(filter_query, data)

    async def get_config(
        self, user_id: str, source_id: str, market: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户数据源配置

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型

        Returns:
            配置数据，未找到返回None
        """
        filter_query = {"user_id": user_id, "source_id": source_id, "market": market}
        return await self.find_one(filter_query)

    async def get_user_configs(
        self, user_id: str, market: Optional[str] = None, enabled: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有数据源配置

        Args:
            user_id: 用户ID
            market: 市场类型（可选）
            enabled: 是否启用

        Returns:
            配置列表
        """
        filter_query = {"user_id": user_id, "enabled": enabled}
        if market:
            filter_query["market"] = market

        return await self.find_many(filter_query, sort=[("priority", 1)])

    async def update_test_status(
        self, user_id: str, source_id: str, market: str, status: str, error: Optional[str] = None
    ) -> int:
        """
        更新测试状态

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型
            status: 测试状态
            error: 错误信息

        Returns:
            修改的文档数量
        """
        filter_query = {"user_id": user_id, "source_id": source_id, "market": market}
        data = {"last_tested_at": datetime.now(), "test_status": status, "last_error": error}
        result = await self.collection.update_one(filter_query, {"$set": data})
        return result.modified_count

    async def delete_config(self, user_id: str, source_id: str, market: str) -> int:
        """
        删除用户数据源配置

        Args:
            user_id: 用户ID
            source_id: 数据源标识
            market: 市场类型

        Returns:
            删除的文档数量
        """
        filter_query = {"user_id": user_id, "source_id": source_id, "market": market}
        result = await self.collection.delete_one(filter_query)
        return result.deleted_count


class DataSourceStatusRepository(BaseRepository):
    """数据源健康状态 Repository"""

    def __init__(self) -> None:
        super().__init__("data_source_status")

    async def create_indexes(self) -> None:
        """创建索引"""
        await self.create_index(
            [("market", 1), ("data_type", 1), ("source_type", 1), ("source_id", 1)], unique=True
        )
        await self.create_index([("market", 1), ("data_type", 1), ("status", 1)])
        await self.create_index([("source_id", 1), ("status", 1)])
        await self.create_index([("last_check_at", -1)])

    async def upsert_status(self, status: DataSourceHealthStatus) -> int:
        """
        新增或更新数据源状态

        Args:
            status: 健康状态对象

        Returns:
            修改的文档数量（0=新增, 1=更新）
        """
        filter_query = {
            "market": status.market,
            "data_type": status.data_type,
            "source_type": status.source_type.value,
            "source_id": status.source_id,
        }
        data = status.model_dump()
        data["updated_at"] = datetime.now()

        return await self.upsert_one(filter_query, data)

    async def get_status(
        self,
        market: str,
        data_type: str,
        source_type: DataSourceType,
        source_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取数据源状态

        Args:
            market: 市场类型
            data_type: 数据类型
            source_type: 数据源类型
            source_id: 数据源标识
            user_id: 用户ID

        Returns:
            状态数据，未找到返回None
        """
        filter_query = {
            "market": market,
            "data_type": data_type,
            "source_type": source_type.value,
            "source_id": source_id,
        }
        if user_id:
            filter_query["user_id"] = user_id

        return await self.find_one(filter_query)

    async def get_all_status(
        self,
        market: Optional[str] = None,
        data_type: Optional[str] = None,
        status: Optional[DataSourceStatus] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取所有数据源状态

        Args:
            market: 市场类型（可选）
            data_type: 数据类型（可选）
            status: 状态（可选）

        Returns:
            状态列表
        """
        filter_query = {}
        if market:
            filter_query["market"] = market
        if data_type:
            filter_query["data_type"] = data_type
        if status:
            filter_query["status"] = status.value

        return await self.find_many(filter_query, sort=[("last_check_at", -1)])

    async def get_healthy_sources(
        self, market: str, data_type: str, source_type: DataSourceType = DataSourceType.SYSTEM
    ) -> List[Dict[str, Any]]:
        """
        获取健康的数据源列表

        Args:
            market: 市场类型
            data_type: 数据类型
            source_type: 数据源类型

        Returns:
            健康数据源列表
        """
        filter_query = {
            "market": market,
            "data_type": data_type,
            "source_type": source_type.value,
            "status": DataSourceStatus.HEALTHY.value,
        }
        return await self.find_many(filter_query, sort=[("last_check_at", -1)])

    async def update_status(
        self,
        market: str,
        data_type: str,
        source_type: DataSourceType,
        source_id: str,
        status: DataSourceStatus,
        response_time_ms: Optional[int] = None,
        error: Optional[Dict[str, Any]] = None,
        check_type: str = "manual_check",
        api_endpoints: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        更新数据源状态

        Args:
            market: 市场类型
            data_type: 数据类型
            source_type: 数据源类型
            source_id: 数据源标识
            status: 新状态
            response_time_ms: 响应时间
            error: 错误信息
            check_type: 检查类型
            api_endpoints: 接口明细

        Returns:
            修改的文档数量
        """
        filter_query = {
            "market": market,
            "data_type": data_type,
            "source_type": source_type.value,
            "source_id": source_id,
        }

        updates: Dict[str, Any] = {
            "status": status.value,
            "last_check_at": datetime.now(),
            "last_check_type": check_type,
            "updated_at": datetime.now(),
        }

        if response_time_ms is not None:
            updates["response_time_ms"] = response_time_ms

        if error is not None:
            updates["last_error"] = error
            updates["failure_count"] = 1
        else:
            updates["last_error"] = None
            updates["failure_count"] = 0

        if api_endpoints:
            updates["api_endpoints"] = api_endpoints

        result = await self.collection.update_one(filter_query, {"$set": updates})
        return result.modified_count

    async def increment_failure_count(
        self,
        market: str,
        data_type: str,
        source_type: DataSourceType,
        source_id: str,
        error: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        增加失败计数

        Args:
            market: 市场类型
            data_type: 数据类型
            source_type: 数据源类型
            source_id: 数据源标识
            error: 错误信息

        Returns:
            更新后的状态文档
        """
        filter_query = {
            "market": market,
            "data_type": data_type,
            "source_type": source_type.value,
            "source_id": source_id,
        }

        updates = {
            "$inc": {"failure_count": 1},
            "$set": {
                "last_error": error,
                "last_check_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        }

        result = await self.collection.update_one(filter_query, updates)
        if result.modified_count > 0:
            doc = await self.find_one(filter_query)
            return doc if doc else {}
        return {}

    async def reset_failure_count(
        self, market: str, data_type: str, source_type: DataSourceType, source_id: str
    ) -> int:
        """
        重置失败计数

        Args:
            market: 市场类型
            data_type: 数据类型
            source_type: 数据源类型
            source_id: 数据源标识

        Returns:
            修改的文档数量
        """
        filter_query = {
            "market": market,
            "data_type": data_type,
            "source_type": source_type.value,
            "source_id": source_id,
        }

        updates = {"$set": {"failure_count": 0, "last_error": None, "updated_at": datetime.now()}}

        result = await self.collection.update_one(filter_query, updates)
        return result.modified_count

    async def update_avg_response_time(
        self,
        market: str,
        data_type: str,
        source_type: DataSourceType,
        source_id: str,
        avg_response_time_ms: int,
    ) -> int:
        """
        更新平均响应时间

        Args:
            market: 市场类型
            data_type: 数据类型
            source_type: 数据源类型
            source_id: 数据源标识
            avg_response_time_ms: 平均响应时间

        Returns:
            修改的文档数量
        """
        filter_query = {
            "market": market,
            "data_type": data_type,
            "source_type": source_type.value,
            "source_id": source_id,
        }

        updates = {
            "$set": {"avg_response_time_ms": avg_response_time_ms, "updated_at": datetime.now()}
        }

        result = await self.collection.update_one(filter_query, updates)
        return result.modified_count

    async def get_degraded_sources(self, market: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取降级的数据源列表

        Args:
            market: 市场类型（可选）

        Returns:
            降级数据源列表
        """
        filter_query: Dict[str, Any] = {"is_fallback": True}
        if market:
            filter_query["market"] = market

        return await self.find_many(filter_query, sort=[("last_check_at", -1)])

    async def get_status_summary(self, market: Optional[str] = None) -> Dict[str, Any]:
        """
        获取状态汇总信息

        Args:
            market: 市场类型（可选）

        Returns:
            状态汇总
        """
        filter_query: Dict[str, Any] = {}
        if market:
            filter_query["market"] = market

        pipeline: List[Dict[str, Any]] = [
            {"$match": filter_query},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]

        results = await self.aggregate(pipeline)
        summary = {
            "healthy": 0,
            "degraded": 0,
            "unavailable": 0,
        }

        for item in results:
            status = item["_id"]
            if status in summary:
                summary[status] = item["count"]

        return summary


class DataSourceStatusHistoryRepository(BaseRepository):
    """数据源状态变更历史 Repository"""

    def __init__(self) -> None:
        super().__init__("data_source_status_history")

    async def create_indexes(self) -> None:
        """创建索引"""
        await self.create_index([("timestamp", -1)])
        await self.create_index(
            [("market", 1), ("data_type", 1), ("source_id", 1), ("timestamp", -1)]
        )
        await self.create_index([("source_id", 1), ("event_type", 1), ("timestamp", -1)])

    async def record_event(self, history: DataSourceStatusHistory) -> str:
        """
        记录状态变更事件

        Args:
            history: 历史事件对象

        Returns:
            文档ID
        """
        data = history.model_dump()
        return await self.insert_one(data)

    async def get_history(
        self,
        market: Optional[str] = None,
        data_type: Optional[str] = None,
        source_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取历史记录

        Args:
            market: 市场类型（可选）
            data_type: 数据类型（可选）
            source_id: 数据源标识（可选）
            event_type: 事件类型（可选）
            limit: 返回数量限制

        Returns:
            历史记录列表
        """
        filter_query = {}
        if market:
            filter_query["market"] = market
        if data_type:
            filter_query["data_type"] = data_type
        if source_id:
            filter_query["source_id"] = source_id
        if event_type:
            filter_query["event_type"] = event_type

        return await self.find_many(filter_query, sort=[("timestamp", -1)], limit=limit)

    async def get_source_history(
        self, source_id: str, event_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取特定数据源的历史记录

        Args:
            source_id: 数据源标识
            event_type: 事件类型（可选）
            limit: 返回数量限制

        Returns:
            历史记录列表
        """
        filter_query = {"source_id": source_id}
        if event_type:
            filter_query["event_type"] = event_type

        return await self.find_many(filter_query, sort=[("timestamp", -1)], limit=limit)

    async def get_recent_failures(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最近的失败记录

        Args:
            hours: 时间范围（小时）
            limit: 返回数量限制

        Returns:
            失败记录列表
        """
        since = datetime.now() - timedelta(hours=hours)
        filter_query = {
            "event_type": {"$in": ["api_failed", "status_changed"]},
            "timestamp": {"$gte": since},
        }

        return await self.find_many(filter_query, sort=[("timestamp", -1)], limit=limit)

    async def cleanup_old_history(self, days: int = 90) -> int:
        """
        清理旧的历史记录

        Args:
            days: 保留天数

        Returns:
            删除的文档数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        filter_query = {"timestamp": {"$lt": cutoff_date}}

        return await self.delete_many(filter_query)

    async def get_error_statistics(
        self, source_id: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取错误统计信息

        Args:
            source_id: 数据源标识（可选）
            hours: 时间范围（小时）

        Returns:
            错误统计
        """
        since = datetime.now() - timedelta(hours=hours)
        filter_query: Dict[str, Any] = {"timestamp": {"$gte": since}}
        if source_id:
            filter_query["source_id"] = source_id

        pipeline: List[Dict[str, Any]] = [
            {"$match": filter_query},
            {
                "$group": {
                    "_id": {"source_id": "$source_id", "error_code": "$error_code"},
                    "count": {"$sum": 1},
                    "last_occurrence": {"$max": "$timestamp"},
                }
            },
            {"$sort": {"count": -1}},
        ]

        results = await self.aggregate(pipeline)
        return {"period_hours": hours, "errors": results}
