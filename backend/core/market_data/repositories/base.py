"""
基础 Repository 类

提供通用的数据访问方法
"""

import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)


class BaseRepository:
    """基础 Repository 类"""

    def __init__(self, collection_name: str):
        """
        初始化 Repository

        Args:
            collection_name: MongoDB集合名称
        """
        self.collection_name = collection_name
        self._collection: Optional[AsyncIOMotorCollection] = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """获取集合"""
        if self._collection is None:
            self._collection = mongodb.get_collection(self.collection_name)
        return self._collection

    async def create_index(self, keys: List[tuple], unique: bool = False) -> str:
        """
        创建索引

        Args:
            keys: 索引键列表，如 [("symbol", 1), ("trade_date", -1)]
            unique: 是否唯一索引

        Returns:
            索引名称
        """
        try:
            index_name = await self.collection.create_index(keys, unique=unique)
            logger.info(f"Created index {index_name} on {self.collection_name}")
            return index_name
        except Exception as e:
            logger.error(f"Failed to create index on {self.collection_name}: {e}")
            raise

    async def insert_one(self, data: Dict[str, Any]) -> str:
        """
        插入单条数据

        Args:
            data: 数据字典

        Returns:
            插入的文档ID
        """
        try:
            result = await self.collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to insert into {self.collection_name}: {e}")
            raise

    async def insert_many(self, data_list: List[Dict[str, Any]]) -> List[str]:
        """
        批量插入数据

        Args:
            data_list: 数据字典列表

        Returns:
            插入的文档ID列表
        """
        try:
            result = await self.collection.insert_many(data_list)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            logger.error(f"Failed to insert many into {self.collection_name}: {e}")
            raise

    async def upsert_one(
        self,
        filter_query: Dict[str, Any],
        data: Dict[str, Any],
        set_on_insert: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        更新或插入单条数据

        Args:
            filter_query: 查询条件
            data: 要更新的数据
            set_on_insert: 插入时设置的额外字段

        Returns:
            修改的文档数量（0=新增, 1=更新）
        """
        try:
            update_doc = {"$set": data}
            if set_on_insert:
                update_doc["$setOnInsert"] = set_on_insert

            result = await self.collection.update_one(filter_query, update_doc, upsert=True)
            # 如果是新增操作，result.modified_count为0，但result.upserted_id有值
            return 1 if result.modified_count > 0 or result.upserted_id else 0
        except Exception as e:
            logger.error(f"Failed to upsert into {self.collection_name}: {e}")
            raise

    async def find_one(
        self,
        filter_query: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None,
        sort: Optional[List[tuple]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        查询单条数据

        Args:
            filter_query: 查询条件
            projection: 投影字段（包含或排除）
            sort: 排序，如 [("updated_at", -1)]，返回排序后的第一条

        Returns:
            查询结果，未找到返回None
        """
        try:
            # 如果指定了排序，使用 find_many + limit(1) 实现
            if sort:
                cursor = self.collection.find(filter_query, projection)
                cursor = cursor.sort(sort).limit(1)
                results = await cursor.to_list(length=1)
                return results[0] if results else None

            # 普通查询
            if projection:
                return await self.collection.find_one(filter_query, projection)
            return await self.collection.find_one(filter_query)
        except Exception as e:
            logger.error(f"Failed to find in {self.collection_name}: {e}")
            raise

    async def find_many(
        self,
        filter_query: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None,
        sort: Optional[List[tuple]] = None,
        limit: int = 0,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        查询多条数据

        Args:
            filter_query: 查询条件
            projection: 投影字段
            sort: 排序，如 [("trade_date", -1)]
            limit: 返回数量限制，0表示不限制
            skip: 跳过数量

        Returns:
            查询结果列表
        """
        try:
            cursor = self.collection.find(filter_query, projection)

            if sort:
                cursor = cursor.sort(sort)
            if skip > 0:
                cursor = cursor.skip(skip)
            if limit > 0:
                cursor = cursor.limit(limit)

            # 设置合理上限，防止一次性加载海量数据导致 OOM
            max_limit = max(limit, 10000) if limit > 0 else 10000
            return await cursor.to_list(length=max_limit)
        except Exception as e:
            logger.error(f"Failed to find many in {self.collection_name}: {e}")
            raise

    async def count_documents(self, filter_query: Dict[str, Any]) -> int:
        """
        统计文档数量

        Args:
            filter_query: 查询条件

        Returns:
            文档数量
        """
        try:
            return await self.collection.count_documents(filter_query)
        except Exception as e:
            logger.error(f"Failed to count in {self.collection_name}: {e}")
            raise

    async def delete_many(self, filter_query: Dict[str, Any]) -> int:
        """
        删除多条数据

        Args:
            filter_query: 查询条件

        Returns:
            删除的文档数量
        """
        try:
            result = await self.collection.delete_many(filter_query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete many from {self.collection_name}: {e}")
            raise

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        聚合查询

        Args:
            pipeline: 聚合管道

        Returns:
            聚合结果列表
        """
        try:
            cursor = self.collection.aggregate(pipeline)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Failed to aggregate on {self.collection_name}: {e}")
            raise
