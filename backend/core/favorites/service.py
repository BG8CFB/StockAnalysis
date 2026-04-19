"""
用户自选股 CRUD 服务

操作 MongoDB user_favorites 集合，按 user_id 隔离数据。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from core.market_data.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FavoriteRepository(BaseRepository):
    """自选股 Repository"""

    def __init__(self) -> None:
        super().__init__("user_favorites")

    async def ensure_indexes(self) -> None:
        """创建索引"""
        await self.create_index([("user_id", 1)])
        await self.create_index([("user_id", 1), ("stock_code", 1)], unique=True)
        await self.create_index([("user_id", 1), ("market", 1)])

    async def list_favorites(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户自选股列表"""
        return await self.find_many(
            {"user_id": user_id},
            sort=[("added_at", -1)],
        )

    async def add_favorite(self, data: Dict[str, Any]) -> bool:
        """添加自选股（upsert）"""
        filter_q = {
            "user_id": data["user_id"],
            "stock_code": data["stock_code"],
        }
        data["updated_at"] = datetime.now()
        result = await self.upsert_one(
            filter_q,
            data,
            set_on_insert={"added_at": datetime.now()},
        )
        return result > 0

    async def update_favorite(
        self,
        user_id: str,
        stock_code: str,
        updates: Dict[str, Any],
    ) -> bool:
        """更新自选股信息"""
        updates["updated_at"] = datetime.now()
        result = await self.collection.update_one(
            {"user_id": user_id, "stock_code": stock_code},
            {"$set": updates},
        )
        return result.modified_count > 0 or result.matched_count > 0

    async def remove_favorite(self, user_id: str, stock_code: str) -> bool:
        """删除自选股"""
        result = await self.collection.delete_one(
            {"user_id": user_id, "stock_code": stock_code},
        )
        return result.deleted_count > 0

    async def check_favorite(self, user_id: str, stock_code: str) -> bool:
        """检查是否已收藏"""
        doc = await self.find_one({"user_id": user_id, "stock_code": stock_code})
        return doc is not None

    async def get_all_tags(self, user_id: str) -> List[str]:
        """获取用户所有唯一标签"""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags"}},
            {"$sort": {"_id": 1}},
        ]
        results = await self.aggregate(pipeline)  # type: ignore[arg-type]
        return [r["_id"] for r in results]

    async def get_all_stocks_for_sync(self, user_id: str) -> List[Dict[str, Any]]:
        """获取所有自选股用于实时行情同步"""
        return await self.find_many(
            {"user_id": user_id},
            projection={"stock_code": 1, "market": 1, "stock_name": 1},
        )
