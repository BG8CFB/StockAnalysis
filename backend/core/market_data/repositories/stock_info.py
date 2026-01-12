"""
股票信息 Repository
"""

from typing import List, Optional
from datetime import datetime

from core.market_data.repositories.base import BaseRepository
from core.market_data.models import StockInfo, MarketType


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
        status: str = "L"
    ) -> List[dict]:
        """
        根据市场类型查询

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            股票信息列表
        """
        filter_query = {"market": market.value, "status": status}
        return await self.find_many(filter_query)

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

        Args:
            stock_list: 股票信息列表

        Returns:
            处理的文档数量
        """
        count = 0
        for stock_info in stock_list:
            await self.upsert_stock_info(stock_info)
            count += 1
        return count
