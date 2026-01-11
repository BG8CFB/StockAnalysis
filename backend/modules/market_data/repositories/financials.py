"""
财务数据 Repository
"""

from typing import List, Optional
from datetime import datetime

from modules.market_data.repositories.base import BaseRepository
from modules.market_data.models import StockFinancial, StockFinancialIndicator


class StockFinancialRepository(BaseRepository):
    """财务报表Repository"""

    def __init__(self):
        super().__init__("stock_financials")

    async def init_indexes(self) -> None:
        """初始化索引"""
        await self.create_index([
            ("symbol", 1),
            ("report_date", 1),
            ("report_type", 1)
        ], unique=True)
        await self.create_index([("symbol", 1), ("report_date", -1)])
        await self.create_index([("fetched_at", 1)])

    async def upsert_financial(self, financial: StockFinancial) -> int:
        """
        更新或插入财务数据

        Args:
            financial: 财务数据对象

        Returns:
            修改的文档数量（0=新增, 1=更新）
        """
        filter_query = {
            "symbol": financial.symbol,
            "report_date": financial.report_date,
            "report_type": financial.report_type
        }
        data = financial.model_dump()
        return await self.upsert_one(filter_query, data)

    async def get_financials(
        self,
        symbol: str,
        report_type: Optional[str] = None,
        limit: int = 0
    ) -> List[dict]:
        """
        查询财务数据

        Args:
            symbol: 股票代码
            report_type: 报告类型
            limit: 返回数量限制

        Returns:
            财务数据列表
        """
        filter_query = {"symbol": symbol}

        if report_type:
            filter_query["report_type"] = report_type

        sort = [("report_date", -1)]

        return await self.find_many(filter_query, sort=sort, limit=limit)


class StockFinancialIndicatorRepository(BaseRepository):
    """财务指标Repository"""

    def __init__(self):
        super().__init__("stock_financial_indicators")

    async def init_indexes(self) -> None:
        """初始化索引"""
        await self.create_index([
            ("symbol", 1),
            ("report_date", 1)
        ], unique=True)
        await self.create_index([("symbol", 1), ("report_date", -1)])

    async def upsert_indicator(self, indicator: StockFinancialIndicator) -> int:
        """
        更新或插入财务指标

        Args:
            indicator: 财务指标对象

        Returns:
            修改的文档数量（0=新增, 1=更新）
        """
        filter_query = {
            "symbol": indicator.symbol,
            "report_date": indicator.report_date
        }
        data = indicator.model_dump()
        return await self.upsert_one(filter_query, data)

    async def get_indicators(
        self,
        symbol: str,
        limit: int = 0
    ) -> List[dict]:
        """
        查询财务指标

        Args:
            symbol: 股票代码
            limit: 返回数量限制

        Returns:
            财务指标列表
        """
        filter_query = {"symbol": symbol}
        sort = [("report_date", -1)]

        return await self.find_many(filter_query, sort=sort, limit=limit)

    async def get_latest_indicator(self, symbol: str) -> Optional[dict]:
        """
        获取最新财务指标

        Args:
            symbol: 股票代码

        Returns:
            最新财务指标，未找到返回None
        """
        sort = [("report_date", -1)]
        results = await self.find_many(
            {"symbol": symbol},
            sort=sort,
            limit=1
        )
        return results[0] if results else None
