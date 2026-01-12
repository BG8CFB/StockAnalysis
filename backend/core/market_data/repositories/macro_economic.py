"""
宏观经济数据 Repository
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .base import BaseRepository
from core.market_data.models import MacroEconomic

logger = logging.getLogger(__name__)


class MacroEconomicRepository(BaseRepository):
    """宏观经济数据 Repository"""

    def __init__(self):
        super().__init__("macro_economic")

    async def create_indexes(self):
        """创建索引"""
        await self.create_index(
            [("indicator", 1), ("period", 1)],
            unique=True
        )
        await self.create_index([("indicator", 1), ("period", -1)])
        await self.create_index([("indicator", 1)])
        await self.create_index([("period", -1)])

    async def upsert_macro(self, macro: MacroEconomic) -> str:
        """
        新增或更新宏观经济数据

        Args:
            macro: 宏观经济数据对象

        Returns:
            文档ID
        """
        filter_query = {
            "indicator": macro.indicator,
            "period": macro.period
        }
        data = macro.model_dump()

        return await self.upsert_one(filter_query, data)

    async def upsert_many(self, macros: List[MacroEconomic]) -> List[str]:
        """
        批量新增或更新宏观经济数据

        Args:
            macros: 宏观经济数据列表

        Returns:
            文档ID列表
        """
        ids = []
        for macro in macros:
            doc_id = await self.upsert_macro(macro)
            ids.append(doc_id)
        return ids

    async def get_macro(
        self,
        indicator: str,
        period: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定指标和周期的宏观经济数据

        Args:
            indicator: 指标名称
            period: 周期

        Returns:
            宏观经济数据，未找到返回None
        """
        filter_query = {
            "indicator": indicator,
            "period": period
        }
        return await self.find_one(filter_query)

    async def get_latest_macro(
        self,
        indicator: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定指标的最新数据

        Args:
            indicator: 指标名称

        Returns:
            最新宏观经济数据，未找到返回None
        """
        filter_query = {"indicator": indicator}
        results = await self.find_many(
            filter_query,
            sort=[("period", -1)],
            limit=1
        )
        return results[0] if results else None

    async def get_macro_history(
        self,
        indicator: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取宏观经济数据历史记录

        Args:
            indicator: 指标名称
            start_period: 开始周期
            end_period: 结束周期
            limit: 返回数量限制

        Returns:
            宏观经济数据列表
        """
        filter_query = {"indicator": indicator}
        if start_period:
            filter_query["period"] = {"$gte": start_period}
        if end_period:
            if "period" not in filter_query:
                filter_query["period"] = {}
            filter_query["period"]["$lte"] = end_period

        return await self.find_many(
            filter_query,
            sort=[("period", -1)],
            limit=limit
        )

    async def get_macros_by_indicators(
        self,
        indicators: List[str],
        period: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取多个指标的数据

        Args:
            indicators: 指标名称列表
            period: 指定周期（可选）
            limit: 返回数量限制

        Returns:
            宏观经济数据列表
        """
        filter_query = {"indicator": {"$in": indicators}}
        if period:
            filter_query["period"] = period

        return await self.find_many(
            filter_query,
            sort=[("indicator", 1), ("period", -1)],
            limit=limit
        )

    async def get_shibor(
        self,
        period: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取SHIBOR数据

        Args:
            period: 指定周期（可选）
            limit: 返回数量限制

        Returns:
            SHIBOR数据列表
        """
        filter_query = {"indicator": "shibor"}
        if period:
            filter_query["period"] = period

        return await self.find_many(
            filter_query,
            sort=[("period", -1)],
            limit=limit
        )

    async def get_cpi(
        self,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取CPI数据

        Args:
            start_period: 开始周期
            end_period: 结束周期
            limit: 返回数量限制

        Returns:
            CPI数据列表
        """
        filter_query = {"indicator": "cpi"}
        if start_period:
            filter_query["period"] = {"$gte": start_period}
        if end_period:
            if "period" not in filter_query:
                filter_query["period"] = {}
            filter_query["period"]["$lte"] = end_period

        return await self.find_many(
            filter_query,
            sort=[("period", -1)],
            limit=limit
        )

    async def get_ppi(
        self,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取PPI数据

        Args:
            start_period: 开始周期
            end_period: 结束周期
            limit: 返回数量限制

        Returns:
            PPI数据列表
        """
        filter_query = {"indicator": "ppi"}
        if start_period:
            filter_query["period"] = {"$gte": start_period}
        if end_period:
            if "period" not in filter_query:
                filter_query["period"] = {}
            filter_query["period"]["$lte"] = end_period

        return await self.find_many(
            filter_query,
            sort=[("period", -1)],
            limit=limit
        )

    async def get_pmi(
        self,
        pmi_type: str = "manufacturing",
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取PMI数据

        Args:
            pmi_type: PMI类型 (manufacturing/caixin)
            start_period: 开始周期
            end_period: 结束周期
            limit: 返回数量限制

        Returns:
            PMI数据列表
        """
        filter_query = {"indicator": f"pmi_{pmi_type}"}
        if start_period:
            filter_query["period"] = {"$gte": start_period}
        if end_period:
            if "period" not in filter_query:
                filter_query["period"] = {}
            filter_query["period"]["$lte"] = end_period

        return await self.find_many(
            filter_query,
            sort=[("period", -1)],
            limit=limit
        )

    async def get_money_supply(
        self,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取货币供应量数据

        Args:
            start_period: 开始周期
            end_period: 结束周期
            limit: 返回数量限制

        Returns:
            货币供应量数据列表
        """
        filter_query = {"indicator": "money_supply"}
        if start_period:
            filter_query["period"] = {"$gte": start_period}
        if end_period:
            if "period" not in filter_query:
                filter_query["period"] = {}
            filter_query["period"]["$lte"] = end_period

        return await self.find_many(
            filter_query,
            sort=[("period", -1)],
            limit=limit
        )

    async def get_gdp(
        self,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取GDP数据

        Args:
            start_period: 开始周期
            end_period: 结束周期
            limit: 返回数量限制

        Returns:
            GDP数据列表
        """
        filter_query = {"indicator": "gdp"}
        if start_period:
            filter_query["period"] = {"$gte": start_period}
        if end_period:
            if "period" not in filter_query:
                filter_query["period"] = {}
            filter_query["period"]["$lte"] = end_period

        return await self.find_many(
            filter_query,
            sort=[("period", -1)],
            limit=limit
        )

    async def get_available_indicators(self) -> List[str]:
        """
        获取所有可用的指标

        Returns:
            指标名称列表
        """
        pipeline = [
            {"$group": {"_id": "$indicator"}},
            {"$sort": {"_id": 1}}
        ]

        results = await self.aggregate(pipeline)
        return [r["_id"] for r in results]

    async def get_indicator_summary(
        self,
        indicator: str
    ) -> Dict[str, Any]:
        """
        获取指标汇总信息

        Args:
            indicator: 指标名称

        Returns:
            指标汇总
        """
        pipeline = [
            {"$match": {"indicator": indicator}},
            {
                "$group": {
                    "_id": "$indicator",
                    "latest_period": {"$first": "$period"},
                    "latest_value": {"$first": "$value"},
                    "count": {"$sum": 1},
                    "min_value": {"$min": "$value"},
                    "max_value": {"$max": "$value"},
                    "avg_value": {"$avg": "$value"}
                }
            }
        ]

        results = await self.aggregate(pipeline)
        return results[0] if results else {}

    async def delete_by_indicator(
        self,
        indicator: str,
        before_period: Optional[str] = None
    ) -> int:
        """
        删除指定指标的数据

        Args:
            indicator: 指标名称
            before_period: 删除此周期之前的数据（可选）

        Returns:
            删除的文档数量
        """
        filter_query = {"indicator": indicator}
        if before_period:
            filter_query["period"] = {"$lt": before_period}

        return await self.delete_many(filter_query)

    async def get_macro_count(
        self,
        indicator: Optional[str] = None
    ) -> int:
        """
        统计宏观经济数据数量

        Args:
            indicator: 指标名称（可选）

        Returns:
            文档数量
        """
        filter_query = {}
        if indicator:
            filter_query["indicator"] = indicator

        return await self.count_documents(filter_query)

    async def get_latest_all(self, indicators: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        获取多个指标的最新数据

        Args:
            indicators: 指标名称列表（可选，不指定则获取所有指标）

        Returns:
            指标最新数据字典，key为indicator名称
        """
        filter_query = {}
        if indicators:
            filter_query["indicator"] = {"$in": indicators}

        pipeline = [
            {"$match": filter_query},
            {"$sort": {"period": -1}},
            {
                "$group": {
                    "_id": "$indicator",
                    "latest": {"$first": "$$ROOT"}
                }
            }
        ]

        results = await self.aggregate(pipeline)
        return {r["_id"]: r["latest"] for r in results}
