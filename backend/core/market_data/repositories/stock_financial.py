"""
财务数据 Repository
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .base import BaseRepository
from core.market_data.models import (
    StockFinancial,
    StockFinancialIndicator,
    MarketType,
)

logger = logging.getLogger(__name__)


class StockFinancialRepository(BaseRepository):
    """财务报表数据 Repository"""

    def __init__(self):
        super().__init__("stock_financials")

    async def create_indexes(self):
        """创建索引"""
        await self.create_index(
            [("symbol", 1), ("report_date", 1), ("report_type", 1)],
            unique=True
        )
        await self.create_index([("symbol", 1), ("report_date", -1)])
        await self.create_index([("report_date", -1)])
        await self.create_index([("market", 1)])

    async def upsert_financial(self, financial: StockFinancial) -> str:
        """
        新增或更新财务数据

        Args:
            financial: 财务数据对象

        Returns:
            文档ID
        """
        filter_query = {
            "symbol": financial.symbol,
            "report_date": financial.report_date,
            "report_type": financial.report_type
        }
        data = financial.model_dump()

        return await self.upsert_one(filter_query, data)

    async def upsert_many(self, financials: List[StockFinancial]) -> List[str]:
        """
        批量新增或更新财务数据

        Args:
            financials: 财务数据列表

        Returns:
            文档ID列表
        """
        ids = []
        for financial in financials:
            doc_id = await self.upsert_financial(financial)
            ids.append(doc_id)
        return ids

    async def get_financial(
        self,
        symbol: str,
        report_date: str,
        report_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定股票、报告期和报告类型的财务数据

        Args:
            symbol: 股票代码
            report_date: 报告期
            report_type: 报告类型

        Returns:
            财务数据，未找到返回None
        """
        filter_query = {
            "symbol": symbol,
            "report_date": report_date,
            "report_type": report_type
        }
        return await self.find_one(filter_query)

    async def get_latest_financial(
        self,
        symbol: str,
        report_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新的财务数据

        Args:
            symbol: 股票代码
            report_type: 报告类型（可选）

        Returns:
            最新财务数据，未找到返回None
        """
        filter_query = {"symbol": symbol}
        if report_type:
            filter_query["report_type"] = report_type

        results = await self.find_many(
            filter_query,
            sort=[("report_date", -1)],
            limit=1
        )
        return results[0] if results else None

    async def get_financial_history(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        report_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取财务数据历史记录

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            report_type: 报告类型（可选）
            limit: 返回数量限制

        Returns:
            财务数据列表
        """
        filter_query = {"symbol": symbol}
        if report_type:
            filter_query["report_type"] = report_type
        if start_date:
            filter_query["report_date"] = {"$gte": start_date}
        if end_date:
            if "report_date" not in filter_query:
                filter_query["report_date"] = {}
            filter_query["report_date"]["$lte"] = end_date

        return await self.find_many(
            filter_query,
            sort=[("report_date", -1)],
            limit=limit
        )

    async def get_financials_by_symbols(
        self,
        symbols: List[str],
        report_date: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取多只股票的财务数据

        Args:
            symbols: 股票代码列表
            report_date: 报告期（可选）
            report_type: 报告类型（可选）

        Returns:
            财务数据列表
        """
        filter_query = {"symbol": {"$in": symbols}}
        if report_date:
            filter_query["report_date"] = report_date
        if report_type:
            filter_query["report_type"] = report_type

        return await self.find_many(filter_query, sort=[("symbol", 1), ("report_date", -1)])

    async def get_income_statement(
        self,
        symbol: str,
        report_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取利润表数据

        Args:
            symbol: 股票代码
            report_date: 报告期

        Returns:
            利润表数据
        """
        filter_query = {
            "symbol": symbol,
            "report_date": report_date
        }
        projection = {"income_statement": 1, "publish_date": 1}
        result = await self.find_one(filter_query, projection)
        return result.get("income_statement") if result else None

    async def get_balance_sheet(
        self,
        symbol: str,
        report_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取资产负债表数据

        Args:
            symbol: 股票代码
            report_date: 报告期

        Returns:
            资产负债表数据
        """
        filter_query = {
            "symbol": symbol,
            "report_date": report_date
        }
        projection = {"balance_sheet": 1, "publish_date": 1}
        result = await self.find_one(filter_query, projection)
        return result.get("balance_sheet") if result else None

    async def get_cash_flow(
        self,
        symbol: str,
        report_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取现金流量表数据

        Args:
            symbol: 股票代码
            report_date: 报告期

        Returns:
            现金流量表数据
        """
        filter_query = {
            "symbol": symbol,
            "report_date": report_date
        }
        projection = {"cash_flow": 1, "publish_date": 1}
        result = await self.find_one(filter_query, projection)
        return result.get("cash_flow") if result else None

    async def delete_by_symbol(
        self,
        symbol: str,
        before_date: Optional[str] = None
    ) -> int:
        """
        删除指定股票的财务数据

        Args:
            symbol: 股票代码
            before_date: 删除此日期之前的数据（可选）

        Returns:
            删除的文档数量
        """
        filter_query = {"symbol": symbol}
        if before_date:
            filter_query["report_date"] = {"$lt": before_date}

        return await self.delete_many(filter_query)

    async def get_financial_count(
        self,
        symbol: Optional[str] = None,
        market: Optional[MarketType] = None
    ) -> int:
        """
        统计财务数据数量

        Args:
            symbol: 股票代码（可选）
            market: 市场类型（可选）

        Returns:
            文档数量
        """
        filter_query = {}
        if symbol:
            filter_query["symbol"] = symbol
        if market:
            filter_query["market"] = market.value

        return await self.count_documents(filter_query)


class StockFinancialIndicatorRepository(BaseRepository):
    """财务指标数据 Repository"""

    def __init__(self):
        super().__init__("stock_financial_indicators")

    async def create_indexes(self):
        """创建索引"""
        await self.create_index(
            [("symbol", 1), ("report_date", 1)],
            unique=True
        )
        await self.create_index([("symbol", 1), ("report_date", -1)])
        await self.create_index([("report_date", -1)])
        await self.create_index([("market", 1)])
        await self.create_index([("roe", -1)])
        await self.create_index([("net_profit_margin", -1)])

    async def upsert_indicator(
        self,
        indicator: StockFinancialIndicator
    ) -> str:
        """
        新增或更新财务指标数据

        Args:
            indicator: 财务指标对象

        Returns:
            文档ID
        """
        filter_query = {
            "symbol": indicator.symbol,
            "report_date": indicator.report_date
        }
        data = indicator.model_dump()

        return await self.upsert_one(filter_query, data)

    async def upsert_many(
        self,
        indicators: List[StockFinancialIndicator]
    ) -> List[str]:
        """
        批量新增或更新财务指标数据

        Args:
            indicators: 财务指标列表

        Returns:
            文档ID列表
        """
        ids = []
        for indicator in indicators:
            doc_id = await self.upsert_indicator(indicator)
            ids.append(doc_id)
        return ids

    async def get_indicator(
        self,
        symbol: str,
        report_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定股票和报告期的财务指标

        Args:
            symbol: 股票代码
            report_date: 报告期

        Returns:
            财务指标数据，未找到返回None
        """
        filter_query = {
            "symbol": symbol,
            "report_date": report_date
        }
        return await self.find_one(filter_query)

    async def get_latest_indicator(
        self,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新的财务指标

        Args:
            symbol: 股票代码

        Returns:
            最新财务指标，未找到返回None
        """
        filter_query = {"symbol": symbol}
        results = await self.find_many(
            filter_query,
            sort=[("report_date", -1)],
            limit=1
        )
        return results[0] if results else None

    async def get_indicator_history(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取财务指标历史记录

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制

        Returns:
            财务指标列表
        """
        filter_query = {"symbol": symbol}
        if start_date:
            filter_query["report_date"] = {"$gte": start_date}
        if end_date:
            if "report_date" not in filter_query:
                filter_query["report_date"] = {}
            filter_query["report_date"]["$lte"] = end_date

        return await self.find_many(
            filter_query,
            sort=[("report_date", -1)],
            limit=limit
        )

    async def get_indicators_by_symbols(
        self,
        symbols: List[str],
        report_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取多只股票的财务指标

        Args:
            symbols: 股票代码列表
            report_date: 报告期（可选）

        Returns:
            财务指标列表
        """
        filter_query = {"symbol": {"$in": symbols}}
        if report_date:
            filter_query["report_date"] = report_date

        return await self.find_many(filter_query, sort=[("symbol", 1)])

    async def search_by_roe(
        self,
        min_roe: float,
        max_roe: Optional[float] = None,
        report_date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        按ROE筛选股票

        Args:
            min_roe: 最小ROE值
            max_roe: 最大ROE值（可选）
            report_date: 报告期（可选）
            limit: 返回数量限制

        Returns:
            符合条件的股票指标列表
        """
        filter_query = {
            "roe": {"$gte": min_roe}
        }
        if max_roe is not None:
            filter_query["roe"]["$lte"] = max_roe
        if report_date:
            filter_query["report_date"] = report_date

        return await self.find_many(
            filter_query,
            sort=[("roe", -1)],
            limit=limit
        )

    async def search_by_net_profit_margin(
        self,
        min_margin: float,
        max_margin: Optional[float] = None,
        report_date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        按净利率筛选股票

        Args:
            min_margin: 最小净利率
            max_margin: 最大净利率（可选）
            report_date: 报告期（可选）
            limit: 返回数量限制

        Returns:
            符合条件的股票指标列表
        """
        filter_query = {
            "net_profit_margin": {"$gte": min_margin}
        }
        if max_margin is not None:
            filter_query["net_profit_margin"]["$lte"] = max_margin
        if report_date:
            filter_query["report_date"] = report_date

        return await self.find_many(
            filter_query,
            sort=[("net_profit_margin", -1)],
            limit=limit
        )

    async def get_financial_summary(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        获取财务指标汇总信息

        Args:
            symbol: 股票代码

        Returns:
            财务指标汇总
        """
        pipeline = [
            {"$match": {"symbol": symbol}},
            {
                "$group": {
                    "_id": "$symbol",
                    "latest_report": {"$first": "$report_date"},
                    "latest_roe": {"$first": "$roe"},
                    "latest_roa": {"$first": "$roa"},
                    "latest_net_profit_margin": {"$first": "$net_profit_margin"},
                    "latest_gross_profit_margin": {"$first": "$gross_profit_margin"},
                    "latest_debt_to_assets": {"$first": "$debt_to_assets"},
                    "count": {"$sum": 1}
                }
            }
        ]

        results = await self.aggregate(pipeline)
        return results[0] if results else {}

    async def delete_by_symbol(
        self,
        symbol: str,
        before_date: Optional[str] = None
    ) -> int:
        """
        删除指定股票的财务指标数据

        Args:
            symbol: 股票代码
            before_date: 删除此日期之前的数据（可选）

        Returns:
            删除的文档数量
        """
        filter_query = {"symbol": symbol}
        if before_date:
            filter_query["report_date"] = {"$lt": before_date}

        return await self.delete_many(filter_query)

    async def get_indicator_count(
        self,
        symbol: Optional[str] = None,
        market: Optional[MarketType] = None
    ) -> int:
        """
        统计财务指标数量

        Args:
            symbol: 股票代码（可选）
            market: 市场类型（可选）

        Returns:
            文档数量
        """
        filter_query = {}
        if symbol:
            filter_query["symbol"] = symbol
        if market:
            filter_query["market"] = market.value

        return await self.count_documents(filter_query)
