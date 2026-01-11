"""
用户自选股Repository
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from core.database import mongodb
from modules.market_data.models.watchlist import (
    WatchlistStock,
    UserWatchlist,
)

logger = logging.getLogger(__name__)


class UserWatchlistRepository:
    """用户自选股Repository"""

    def __init__(self):
        self.collection_name = "user_watchlists"
        self._collection: Optional[AsyncIOMotorDatabase] = None

    @property
    def collection(self) -> AsyncIOMotorDatabase:
        if self._collection is None:
            self._collection = mongodb.get_collection(self.collection_name)
        return self._collection

    async def get_user_watchlist(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的自选股列表"""
        return await self.collection.find_one({"user_id": user_id})

    async def add_stock(
        self,
        user_id: str,
        symbol: str,
        market: str,
        notes: Optional[str] = None
    ) -> None:
        """添加股票到自选"""
        # 检查是否已存在
        existing = await self.collection.find_one({
            "user_id": user_id,
            "stocks.symbol": symbol
        })

        stock_data = {
            "symbol": symbol,
            "market": market,
            "added_at": datetime.now(),
            "notes": notes,
            "sync_status": "pending"
        }

        if existing:
            # 更新现有股票
            await self.collection.update_one(
                {"user_id": user_id, "stocks.symbol": symbol},
                {
                    "$set": {
                        "stocks.$": stock_data,
                        "updated_at": datetime.now()
                    }
                }
            )
        else:
            # 添加新股票
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$push": {"stocks": stock_data},
                    "$set": {"updated_at": datetime.now()}
                },
                upsert=True
            )

    async def remove_stock(self, user_id: str, symbol: str) -> bool:
        """从自选中删除股票"""
        result = await self.collection.update_one(
            {"user_id": user_id},
            {
                "$pull": {"stocks": {"symbol": symbol}},
                "$set": {"updated_at": datetime.now()}
            }
        )
        return result.modified_count > 0

    async def update_stock_sync_status(
        self,
        user_id: str,
        symbol: str,
        sync_status: str,
        sync_result: Optional[Dict[str, Any]] = None
    ) -> None:
        """更新股票同步状态"""
        await self.collection.update_one(
            {"user_id": user_id, "stocks.symbol": symbol},
            {
                "$set": {
                    "stocks.$.sync_status": sync_status,
                    "stocks.$.last_sync_at": datetime.now(),
                    "stocks.$.sync_result": sync_result,
                    "updated_at": datetime.now()
                }
            }
        )

    async def get_syncing_stocks(self, user_id: str) -> List[Dict[str, Any]]:
        """获取正在同步的股票列表"""
        watchlist = await self.get_user_watchlist(user_id)
        if not watchlist:
            return []

        return [
            stock for stock in watchlist.get("stocks", [])
            if stock.get("sync_status") in ["pending", "syncing"]
        ]
