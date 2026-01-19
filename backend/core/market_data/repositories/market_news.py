
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import pymongo
from pymongo import IndexModel, ASCENDING, DESCENDING

from core.db.mongodb import mongodb
from core.market_data.models.stock_other import MarketNews

logger = logging.getLogger(__name__)


class MarketNewsRepository:
    """市场新闻仓库"""

    def __init__(self):
        self.db = mongodb.database
        self.collection = self.db.market_news
        self._create_indexes()

    def _create_indexes(self):
        """创建索引"""
        try:
            indexes = [
                IndexModel([("news_id", ASCENDING)], unique=True),
                IndexModel([("datetime", DESCENDING)]),
                IndexModel([("symbol", ASCENDING)]),
                IndexModel([("data_source", ASCENDING)]),
            ]
            self.collection.create_indexes(indexes)
        except Exception as e:
            logger.error(f"Failed to create indexes for market_news: {e}")

    async def upsert_news(self, news: MarketNews) -> bool:
        """
        更新或插入新闻
        
        Args:
            news: 新闻对象
            
        Returns:
            bool: 是否成功
        """
        try:
            news_dict = news.model_dump()
            # 确保 updated_at 是 datetime 对象
            news_dict["updated_at"] = datetime.now()
            
            await self.collection.update_one(
                {"news_id": news.news_id},
                {"$set": news_dict},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert news {news.news_id}: {e}")
            return False

    async def get_latest_news(self, limit: int = 100) -> List[MarketNews]:
        """
        获取最新新闻
        
        Args:
            limit: 限制数量
            
        Returns:
            新闻列表
        """
        try:
            cursor = self.collection.find().sort("datetime", DESCENDING).limit(limit)
            news_list = []
            async for doc in cursor:
                news_list.append(MarketNews(**doc))
            return news_list
        except Exception as e:
            logger.error(f"Failed to get latest news: {e}")
            return []

    async def get_by_symbol(self, symbol: str, limit: int = 50) -> List[MarketNews]:
        """
        获取个股相关新闻
        
        Args:
            symbol: 股票代码
            limit: 限制数量
            
        Returns:
            新闻列表
        """
        try:
            cursor = self.collection.find({"symbol": symbol}).sort("datetime", DESCENDING).limit(limit)
            news_list = []
            async for doc in cursor:
                news_list.append(MarketNews(**doc))
            return news_list
        except Exception as e:
            logger.error(f"Failed to get news for {symbol}: {e}")
            return []
