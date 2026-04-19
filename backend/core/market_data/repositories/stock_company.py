"""
公司信息 Repository
"""

import logging
from typing import Any, Dict, List, Optional

from core.market_data.models import (
    MarketType,
    StockCompany,
)

from .base import BaseRepository

logger = logging.getLogger(__name__)


class StockCompanyRepository(BaseRepository):
    """公司详细信息 Repository"""

    def __init__(self) -> None:
        super().__init__("stock_companies")

    async def create_indexes(self) -> None:
        """创建索引"""
        await self.create_index([("symbol", 1)], unique=True)
        await self.create_index([("market", 1)])
        await self.create_index([("industry", 1)])
        await self.create_index([("company_name", 1)])

    async def upsert_company(self, company: StockCompany) -> int:
        """
        新增或更新公司信息

        Args:
            company: 公司信息对象

        Returns:
            文档ID
        """
        filter_query = {"symbol": company.symbol}
        data = company.model_dump()

        return await self.upsert_one(filter_query, data)

    async def upsert_many(self, companies: List[StockCompany]) -> List[int]:
        """
        批量新增或更新公司信息

        Args:
            companies: 公司信息列表

        Returns:
            修改数量列表
        """
        results = []
        for company in companies:
            count = await self.upsert_company(company)
            results.append(count)
        return results

    async def get_company(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取公司信息

        Args:
            symbol: 股票代码

        Returns:
            公司信息，未找到返回None
        """
        filter_query = {"symbol": symbol}
        return await self.find_one(filter_query)

    async def get_company_by_name(
        self, company_name: str, market: Optional[MarketType] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据公司名称查询

        Args:
            company_name: 公司名称
            market: 市场类型（可选）

        Returns:
            公司信息，未找到返回None
        """
        filter_query = {"company_name": company_name}
        if market:
            filter_query["market"] = market.value

        return await self.find_one(filter_query)

    async def get_companies_by_industry(
        self, industry: str, market: Optional[MarketType] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取指定行业的公司列表

        Args:
            industry: 行业名称
            market: 市场类型（可选）
            limit: 返回数量限制

        Returns:
            公司信息列表
        """
        filter_query = {"industry": industry}
        if market:
            filter_query["market"] = market.value

        return await self.find_many(filter_query, limit=limit)

    async def get_companies_by_sector(
        self, sector: str, market: Optional[MarketType] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取指定板块的公司列表

        Args:
            sector: 板块名称
            market: 市场类型（可选）
            limit: 返回数量限制

        Returns:
            公司信息列表
        """
        filter_query = {"sector": sector}
        if market:
            filter_query["market"] = market.value

        return await self.find_many(filter_query, limit=limit)

    async def get_companies_by_market(
        self, market: MarketType, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取指定市场的公司列表

        Args:
            market: 市场类型
            skip: 跳过数量
            limit: 返回数量限制

        Returns:
            公司信息列表
        """
        filter_query = {"market": market.value}
        return await self.find_many(filter_query, skip=skip, limit=limit)

    async def search_companies(
        self, keyword: str, market: Optional[MarketType] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索公司信息（公司名称或股票代码）

        Args:
            keyword: 搜索关键词
            market: 市场类型（可选）
            limit: 返回数量限制

        Returns:
            匹配的公司信息列表
        """
        filter_query: Dict[str, Any] = {
            "$or": [
                {"company_name": {"$regex": keyword, "$options": "i"}},
                {"symbol": {"$regex": keyword, "$options": "i"}},
            ]
        }
        if market:
            filter_query["market"] = market.value

        return await self.find_many(filter_query, limit=limit)

    async def get_industry_list(self, market: Optional[MarketType] = None) -> List[str]:
        """
        获取所有行业列表

        Args:
            market: 市场类型（可选）

        Returns:
            行业名称列表
        """
        filter_query: Dict[str, Any] = {"industry": {"$ne": None}}
        if market:
            filter_query["market"] = market.value

        results = await self.aggregate(
            [{"$match": filter_query}, {"$group": {"_id": "$industry"}}, {"$sort": {"_id": 1}}]
        )

        return [r["_id"] for r in results if r["_id"]]

    async def get_sector_list(self, market: Optional[MarketType] = None) -> List[str]:
        """
        获取所有板块列表

        Args:
            market: 市场类型（可选）

        Returns:
            板块名称列表
        """
        filter_query: Dict[str, Any] = {"sector": {"$ne": None}}
        if market:
            filter_query["market"] = market.value

        results = await self.aggregate(
            [{"$match": filter_query}, {"$group": {"_id": "$sector"}}, {"$sort": {"_id": 1}}]
        )

        return [r["_id"] for r in results if r["_id"]]

    async def get_company_count(
        self, market: Optional[MarketType] = None, industry: Optional[str] = None
    ) -> int:
        """
        统计公司数量

        Args:
            market: 市场类型（可选）
            industry: 行业（可选）

        Returns:
            公司数量
        """
        filter_query = {}
        if market:
            filter_query["market"] = market.value
        if industry:
            filter_query["industry"] = industry

        return await self.count_documents(filter_query)

    async def get_industry_distribution(
        self, market: Optional[MarketType] = None
    ) -> List[Dict[str, Any]]:
        """
        获取行业分布统计

        Args:
            market: 市场类型（可选）

        Returns:
            行业分布列表，包含行业名称和公司数量
        """
        filter_query: Dict[str, Any] = {}
        if market:
            filter_query["market"] = market.value

        pipeline: List[Dict[str, Any]] = [
            {"$match": filter_query},
            {"$group": {"_id": "$industry", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]

        return await self.aggregate(pipeline)

    async def update_company(self, symbol: str, updates: Dict[str, Any]) -> int:
        """
        更新公司信息

        Args:
            symbol: 股票代码
            updates: 更新的字段

        Returns:
            修改的文档数量
        """
        filter_query = {"symbol": symbol}
        result = await self.collection.update_one(filter_query, {"$set": updates})
        return result.modified_count

    async def delete_company(self, symbol: str) -> int:
        """
        删除公司信息

        Args:
            symbol: 股票代码

        Returns:
            删除的文档数量
        """
        filter_query = {"symbol": symbol}
        result = await self.collection.delete_one(filter_query)
        return result.deleted_count

    async def get_business_description(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取公司业务描述

        Args:
            symbol: 股票代码

        Returns:
            业务描述
        """
        filter_query = {"symbol": symbol}
        projection = {"business": 1, "company_name": 1}
        result = await self.find_one(filter_query, projection)
        return result.get("business") if result else None

    async def get_capital_structure(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取公司股本结构

        Args:
            symbol: 股票代码

        Returns:
            股本结构
        """
        filter_query = {"symbol": symbol}
        projection = {"capital_structure": 1, "company_name": 1}
        result = await self.find_one(filter_query, projection)
        return result.get("capital_structure") if result else None

    async def get_contact_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取公司联系方式

        Args:
            symbol: 股票代码

        Returns:
            联系方式
        """
        filter_query = {"symbol": symbol}
        projection = {"contact": 1, "company_name": 1}
        result = await self.find_one(filter_query, projection)
        return result.get("contact") if result else None

    async def get_new_listings(
        self, days: int = 30, market: Optional[MarketType] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取近期新上市公司

        Args:
            days: 近多少天
            market: 市场类型（可选）
            limit: 返回数量限制

        Returns:
            公司信息列表
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime("%Y%m%d")

        filter_query: Dict[str, Any] = {"listing_date": {"$gte": cutoff_str}}
        if market:
            filter_query["market"] = market.value

        return await self.find_many(filter_query, sort=[("listing_date", -1)], limit=limit)

    async def get_industry_summary(self, industry: str) -> Dict[str, Any]:
        """
        获取行业汇总信息

        Args:
            industry: 行业名称

        Returns:
            行业汇总信息
        """
        pipeline: List[Dict[str, Any]] = [
            {"$match": {"industry": industry}},
            {
                "$group": {
                    "_id": "$industry",
                    "count": {"$sum": 1},
                    "total_capital": (
                        {"$sum": "$capital_structure.total_share_capital"}
                        if "$capital_structure.total_share_capital"
                        else {"$sum": 0}
                    ),
                }
            },
        ]

        results = await self.aggregate(pipeline)
        return results[0] if results else {}
