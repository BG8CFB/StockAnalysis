"""
市场分类与数据源分组管理服务

MongoDB 集合 market_categories / datasource_groupings 的 CRUD 操作。
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.db.mongodb import mongodb
from core.market_data.category_models import (
    DataSourceGroupingCreateRequest,
    DataSourceGroupingResponse,
    DataSourceOrderItem,
    MarketCategoryCreateRequest,
    MarketCategoryResponse,
)

logger = logging.getLogger(__name__)

CATEGORY_COLLECTION = "market_categories"
GROUPING_COLLECTION = "datasource_groupings"


class MarketCategoryService:
    """市场分类与数据源分组管理服务"""

    # ========================================================================
    # 市场分类
    # ========================================================================

    async def _get_category_collection(self):
        return mongodb.get_collection(CATEGORY_COLLECTION)

    async def list_categories(self) -> List[MarketCategoryResponse]:
        """获取所有分类"""
        collection = await self._get_category_collection()
        cursor = collection.find({}).sort("sort_order", 1)
        docs = await cursor.to_list(length=None)
        return [
            MarketCategoryResponse(
                id=doc.get("category_id", str(doc["_id"])),
                name=doc["name"],
                display_name=doc["display_name"],
                description=doc.get("description"),
                enabled=doc.get("enabled", True),
                sort_order=doc.get("sort_order"),
            )
            for doc in docs
        ]

    async def create_category(self, data: MarketCategoryCreateRequest) -> str:
        """创建分类"""
        collection = await self._get_category_collection()

        # 检查是否已存在
        existing = await collection.find_one({"category_id": data.id})
        if existing:
            raise ValueError(f"分类 '{data.id}' 已存在")

        now = datetime.now(timezone.utc)
        doc = {
            "category_id": data.id,
            "name": data.name,
            "display_name": data.display_name,
            "description": data.description,
            "enabled": data.enabled,
            "sort_order": data.sort_order,
            "created_at": now,
            "updated_at": now,
        }

        await collection.insert_one(doc)
        return data.id

    async def update_category(self, category_id: str, updates: Dict) -> bool:
        """更新分类"""
        collection = await self._get_category_collection()
        update_fields = {"updated_at": datetime.now(timezone.utc)}
        update_fields.update(updates)

        result = await collection.update_one(
            {"category_id": category_id},
            {"$set": update_fields},
        )
        return result.matched_count > 0

    async def delete_category(self, category_id: str) -> bool:
        """删除分类"""
        collection = await self._get_category_collection()
        result = await collection.delete_one({"category_id": category_id})
        # 同时删除关联的分组
        grouping_col = await self._get_grouping_collection()
        await grouping_col.delete_many({"market_category_id": category_id})
        return result.deleted_count > 0

    async def reorder_datasources(self, category_id: str, items: List[DataSourceOrderItem]) -> bool:
        """更新分类内数据源排序"""
        grouping_col = await self._get_grouping_collection()
        for item in items:
            await grouping_col.update_one(
                {"data_source_name": item.name, "market_category_id": category_id},
                {"$set": {"priority": item.priority}},
            )
        return True

    # ========================================================================
    # 数据源分组
    # ========================================================================

    async def _get_grouping_collection(self):
        return mongodb.get_collection(GROUPING_COLLECTION)

    async def list_groupings(self) -> List[DataSourceGroupingResponse]:
        """获取所有分组"""
        collection = await self._get_grouping_collection()
        cursor = collection.find({}).sort("market_category_id", 1)
        docs = await cursor.to_list(length=None)
        return [
            DataSourceGroupingResponse(
                data_source_name=doc["data_source_name"],
                market_category_id=doc["market_category_id"],
                priority=doc.get("priority", 1),
                enabled=doc.get("enabled", True),
            )
            for doc in docs
        ]

    async def add_grouping(self, data: DataSourceGroupingCreateRequest) -> bool:
        """添加数据源到分类"""
        collection = await self._get_grouping_collection()

        existing = await collection.find_one({
            "data_source_name": data.data_source_name,
            "market_category_id": data.market_category_id,
        })
        if existing:
            raise ValueError(
                f"数据源 '{data.data_source_name}' 已在分类 '{data.market_category_id}' 中"
            )

        doc = {
            "data_source_name": data.data_source_name,
            "market_category_id": data.market_category_id,
            "priority": data.priority,
            "enabled": data.enabled,
            "created_at": datetime.now(timezone.utc),
        }
        await collection.insert_one(doc)
        return True

    async def remove_grouping(self, data_source_name: str, category_id: str) -> bool:
        """从分类中移除数据源"""
        collection = await self._get_grouping_collection()
        result = await collection.delete_one({
            "data_source_name": data_source_name,
            "market_category_id": category_id,
        })
        return result.deleted_count > 0

    async def update_grouping(
        self, data_source_name: str, category_id: str, updates: Dict
    ) -> bool:
        """更新分组关系"""
        collection = await self._get_grouping_collection()
        result = await collection.update_one(
            {"data_source_name": data_source_name, "market_category_id": category_id},
            {"$set": updates},
        )
        return result.matched_count > 0


# 全局单例
_market_category_service: Optional[MarketCategoryService] = None


def get_market_category_service() -> MarketCategoryService:
    """获取市场分类服务单例"""
    global _market_category_service
    if _market_category_service is None:
        _market_category_service = MarketCategoryService()
    return _market_category_service
