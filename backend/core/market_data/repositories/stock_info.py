"""
股票信息 Repository
"""

import logging
from typing import List, Optional
from datetime import datetime

from core.market_data.repositories.base import BaseRepository
from core.market_data.models import StockInfo, MarketType
from core.config import MONGODB_BULK_WRITE_BATCH_SIZE

logger = logging.getLogger(__name__)

# MongoDB 批量操作大小限制（从配置读取）
BULK_WRITE_BATCH_SIZE = MONGODB_BULK_WRITE_BATCH_SIZE


class StockInfoRepository(BaseRepository):
    """股票信息Repository"""

    def __init__(self):
        super().__init__("stock_info")

    async def init_indexes(self) -> None:
        """初始化索引"""
        await self.create_index([("symbol", 1)], unique=True)
        await self.create_index([("market", 1)])
        await self.create_index([("exchange", 1)])

    async def upsert_stock_info(self, stock_info: StockInfo) -> int:
        """
        更新或插入股票信息

        Args:
            stock_info: 股票信息对象

        Returns:
            修改的文档数量（0=新增, 1=更新）
        """
        filter_query = {"symbol": stock_info.symbol}
        data = stock_info.model_dump()
        return await self.upsert_one(filter_query, data)

    async def get_by_symbol(self, symbol: str) -> Optional[dict]:
        """
        根据股票代码查询

        Args:
            symbol: 股票代码

        Returns:
            股票信息字典，未找到返回None
        """
        return await self.find_one({"symbol": symbol})

    async def get_by_market(
        self,
        market: MarketType,
        status: str = "L",
        limit: Optional[int] = None
    ) -> List[dict]:
        """
        根据市场类型查询

        Args:
            market: 市场类型
            status: 上市状态
            limit: 返回数量限制（None表示不限制）

        Returns:
            股票信息列表
        """
        filter_query = {"market": market.value, "status": status}
        # limit=0 表示不限制，None 也转换为 0
        limit_value = limit if limit is not None else 0
        return await self.find_many(filter_query, limit=limit_value)

    async def get_all_symbols(self, market: Optional[MarketType] = None) -> List[str]:
        """
        获取所有股票代码

        Args:
            market: 可选的市场类型筛选

        Returns:
            股票代码列表
        """
        filter_query = {}
        if market:
            filter_query["market"] = market.value

        # 只返回symbol字段
        cursor = self.collection.find(filter_query, {"symbol": 1})
        results = await cursor.to_list(length=None)
        return [doc["symbol"] for doc in results]

    async def batch_upsert(self, stock_list: List[StockInfo]) -> int:
        """
        批量更新或插入股票信息

        使用 MongoDB bulk_write 操作提高性能，减少数据库往返次数。

        Args:
            stock_list: 股票信息列表

        Returns:
            处理的文档数量
        """
        if not stock_list:
            return 0

        from pymongo import UpdateOne

        operations = []
        for stock_info in stock_list:
            filter_query = {"symbol": stock_info.symbol}
            data = {"$set": stock_info.model_dump()}
            operations.append(UpdateOne(filter_query, data, upsert=True))

        # 批量执行操作（每次最多 BULK_WRITE_BATCH_SIZE 条）
        total_count = 0
        for i in range(0, len(operations), BULK_WRITE_BATCH_SIZE):
            batch = operations[i:i + BULK_WRITE_BATCH_SIZE]
            result = await self.collection.bulk_write(batch, ordered=False)
            total_count += result.upserted_count + result.modified_count

        logger.info(f"Batch upserted {total_count} stock info records")
        return total_count
