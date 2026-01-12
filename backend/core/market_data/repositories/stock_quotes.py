"""
行情数据 Repository
"""

from typing import List, Optional
from datetime import datetime

from core.market_data.repositories.base import BaseRepository
from core.market_data.models import StockQuote, MarketType


class StockQuoteRepository(BaseRepository):
    """日线行情数据Repository"""

    def __init__(self):
        super().__init__("stock_quotes")

    async def init_indexes(self) -> None:
        """初始化索引"""
        # 复合唯一索引：symbol + trade_date
        await self.create_index([("symbol", 1), ("trade_date", 1), ("data_source", 1)], unique=True)
        await self.create_index([("symbol", 1), ("trade_date", -1)])
        await self.create_index([("market", 1), ("trade_date", -1)])
        await self.create_index([("fetched_at", 1)])

    async def upsert_quote(self, quote: StockQuote) -> int:
        """
        更新或插入行情数据

        Args:
            quote: 行情数据对象

        Returns:
            修改的文档数量（0=新增, 1=更新）
        """
        filter_query = {
            "symbol": quote.symbol,
            "trade_date": quote.trade_date,
            "data_source": quote.data_source
        }
        data = quote.model_dump()
        return await self.upsert_one(filter_query, data)

    async def get_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 0
    ) -> List[dict]:
        """
        查询历史行情

        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            limit: 返回数量限制

        Returns:
            行情数据列表
        """
        filter_query = {"symbol": symbol}

        if start_date and end_date:
            filter_query["trade_date"] = {
                "$gte": start_date,
                "$lte": end_date
            }
        elif start_date:
            filter_query["trade_date"] = {"$gte": start_date}
        elif end_date:
            filter_query["trade_date"] = {"$lte": end_date}

        sort = [("trade_date", -1)]  # 按日期降序

        return await self.find_many(filter_query, sort=sort, limit=limit)

    async def get_latest_quote(self, symbol: str) -> Optional[dict]:
        """
        获取最新行情

        Args:
            symbol: 股票代码

        Returns:
            最新行情数据，未找到返回None
        """
        sort = [("trade_date", -1)]
        results = await self.find_many(
            {"symbol": symbol},
            sort=sort,
            limit=1
        )
        return results[0] if results else None

    async def delete_old_quotes(self, symbol: str, before_date: str) -> int:
        """
        删除指定日期之前的行情数据

        Args:
            symbol: 股票代码
            before_date: 日期（YYYYMMDD），删除此日期之前的数据

        Returns:
            删除的文档数量
        """
        filter_query = {
            "symbol": symbol,
            "trade_date": {"$lt": before_date}
        }
        return await self.delete_many(filter_query)

    async def batch_upsert(self, quotes: List[StockQuote]) -> int:
        """
        批量更新或插入行情数据

        Args:
            quotes: 行情数据列表

        Returns:
            处理的文档数量
        """
        count = 0
        for quote in quotes:
            await self.upsert_quote(quote)
            count += 1
        return count

    async def delete_expired_intraday_quotes(self, cutoff_date: str) -> int:
        """
        删除过期的当日行情数据（仅删除盘中数据，保留收盘数据）

        Args:
            cutoff_date: 截止日期（YYYYMMDD），删除此日期之前的盘中数据

        Returns:
            删除的文档数量
        """
        filter_query = {
            "trade_date": {"$lt": cutoff_date},
            "is_intraday": True  # 仅删除盘中数据
        }
        return await self.delete_many(filter_query)

    async def delete_expired_minute_klines(self, cutoff_date: str) -> int:
        """
        删除过期的分钟K线数据

        Args:
            cutoff_date: 截止日期（YYYYMMDD），删除此日期之前的分钟K线

        Returns:
            删除的文档数量
        """
        # 分钟K线存储在单独的集合中
        from motor.motor_asyncio import AsyncIOMotorCollection
        from core.database import get_database

        db = await get_database()
        kline_collection: AsyncIOMotorCollection = db["stock_minute_klines"]

        filter_query = {
            "trade_date": {"$lt": cutoff_date}
        }
        result = await kline_collection.delete_many(filter_query)
        return result.deleted_count
