"""
筛选服务层

处理筛选逻辑：构建 MongoDB 聚合管道、执行查询。
"""

import logging
import time
from typing import Any

from core.screening.fields import FIELD_CATEGORIES, FIELDS_MAP, SCREENING_FIELDS

logger = logging.getLogger(__name__)


def _build_comparison(db_field: str, op: str, value: Any) -> dict[str, Any] | None:
    """将前端运算符映射为 MongoDB 查询条件"""
    if op == "gt":
        return {db_field: {"$gt": value}}
    if op == "gte":
        return {db_field: {"$gte": value}}
    if op == "lt":
        return {db_field: {"$lt": value}}
    if op == "lte":
        return {db_field: {"$lte": value}}
    if op == "eq":
        return {db_field: value}
    if op == "ne":
        return {db_field: {"$ne": value}}
    if op == "in":
        if not isinstance(value, list):
            value = [value]
        return {db_field: {"$in": value}}
    if op == "contains":
        return {db_field: {"$regex": str(value), "$options": "i"}}
    if op == "between":
        if isinstance(value, list) and len(value) == 2:
            return {db_field: {"$gte": value[0], "$lte": value[1]}}
        return None
    return None


class ScreeningService:
    """筛选服务"""

    async def get_fields_config(self) -> dict[str, Any]:
        """获取所有筛选字段配置"""
        fields = {f.name: f.to_dict() for f in SCREENING_FIELDS}
        return {
            "fields": fields,
            "categories": FIELD_CATEGORIES,
        }

    async def get_field_detail(self, field_name: str) -> dict[str, Any] | None:
        """获取指定字段详情"""
        f = FIELDS_MAP.get(field_name)
        if f is None:
            return None
        return f.to_dict()

    def _build_match_stage(
        self,
        conditions: list[dict[str, Any]] | None,
        logic: str = "AND",
        market: str | None = None,
    ) -> dict[str, Any]:
        """构建 $match 阶段"""
        match_parts: list[dict[str, Any]] = []

        # 市场过滤
        if market:
            match_parts.append({"market": market})

        # 只查上市状态
        match_parts.append({"status": "L"})

        # 条件过滤
        if conditions:
            cond_queries: list[dict[str, Any]] = []
            for cond in conditions:
                field_name = cond.get("field", "")
                op = cond.get("op") or cond.get("operator", "")
                value = cond.get("value")

                field_def = FIELDS_MAP.get(field_name)
                if not field_def or not op or value is None:
                    continue

                q = _build_comparison(field_def.db_field, op, value)
                if q:
                    cond_queries.append(q)

            if cond_queries:
                if logic.upper() == "OR":
                    match_parts.append({"$or": cond_queries})
                else:
                    # AND: 所有条件平铺到同一个 dict
                    and_query: dict[str, Any] = {}
                    for q in cond_queries:
                        and_query.update(q)
                    match_parts.append(and_query)

        # 合并为单个 $match
        merged: dict[str, Any] = {}
        for part in match_parts:
            merged.update(part)
        return merged

    async def run_screening(
        self,
        conditions: list[dict[str, Any]] | None = None,
        logic: str = "AND",
        market: str | None = None,
        order_by: list[dict[str, Any]] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """运行传统筛选"""
        from core.market_data.repositories.stock_financial import (
            StockFinancialIndicatorRepository,
        )
        from core.market_data.repositories.stock_info import StockInfoRepository

        match_stage = self._build_match_stage(conditions, logic, market)

        # 排序
        sort_stage = self._build_sort_stage(order_by)

        repo = StockFinancialIndicatorRepository()

        pipeline: list[dict[str, Any]] = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        if sort_stage:
            pipeline.append(sort_stage)

        # 先获取总数
        count_pipeline = pipeline + [{"$count": "total"}]
        count_result = await repo.aggregate(count_pipeline)
        total = count_result[0]["total"] if count_result else 0

        # 分页
        if offset > 0:
            pipeline.append({"$skip": offset})
        if limit > 0:
            pipeline.append({"$limit": limit})

        results = await repo.aggregate(pipeline)

        # 补充股票名称
        info_repo = StockInfoRepository()
        items = []
        for doc in results:
            doc.pop("_id", None)
            symbol = doc.get("symbol", "")
            info = await info_repo.get_by_symbol(symbol)
            if info:
                doc["name"] = info.get("name", "")
                doc.setdefault("market", info.get("market", ""))
                doc.setdefault("industry", info.get("industry", ""))
            items.append(doc)

        return {"total": total, "items": items}

    async def run_enhanced_screening(
        self,
        conditions: list[dict[str, Any]],
        market: str | None = None,
        order_by: list[dict[str, Any]] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """运行增强筛选（支持跨集合关联）"""
        start = time.time()

        from core.market_data.repositories.stock_financial import (
            StockFinancialIndicatorRepository,
        )
        from core.market_data.repositories.stock_info import StockInfoRepository

        # 构建查询条件
        match_stage = self._build_match_stage(conditions, logic="AND", market=market)

        # 排序
        sort_stage = self._build_sort_stage(order_by)

        repo = StockFinancialIndicatorRepository()

        pipeline: list[dict[str, Any]] = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        if sort_stage:
            pipeline.append(sort_stage)

        # 总数
        count_pipeline = pipeline + [{"$count": "total"}]
        count_result = await repo.aggregate(count_pipeline)
        total = count_result[0]["total"] if count_result else 0

        # 分页
        if offset > 0:
            pipeline.append({"$skip": offset})
        if limit > 0:
            pipeline.append({"$limit": limit})

        results = await repo.aggregate(pipeline)

        # 补充信息
        info_repo = StockInfoRepository()
        items = []
        for doc in results:
            doc.pop("_id", None)
            symbol = doc.get("symbol", "")
            info = await info_repo.get_by_symbol(symbol)
            if info:
                doc["name"] = info.get("name", "")
                doc.setdefault("market", info.get("market", ""))
                doc.setdefault("industry", info.get("industry", ""))
            items.append(doc)

        took_ms = int((time.time() - start) * 1000)

        return {
            "total": total,
            "items": items,
            "took_ms": took_ms,
            "optimization_used": False,
            "source": "database",
        }

    async def validate_conditions(self, conditions: list[dict[str, Any]]) -> dict[str, Any]:
        """验证筛选条件"""
        errors: list[dict[str, str]] = []
        valid_count = 0

        for i, cond in enumerate(conditions):
            field_name = cond.get("field", "")
            op = cond.get("operator", "")
            value = cond.get("value")

            # 检查字段是否存在
            if not field_name:
                errors.append({"index": str(i), "message": "缺少 field 字段"})
                continue

            field_def = FIELDS_MAP.get(field_name)
            if not field_def:
                errors.append({"index": str(i), "message": f"未知字段: {field_name}"})
                continue

            # 检查运算符
            valid_ops = {"gt", "gte", "lt", "lte", "eq", "ne", "in", "contains", "between"}
            if op not in valid_ops:
                errors.append({"index": str(i), "message": f"不支持的操作符: {op}"})
                continue

            # 检查值
            if value is None:
                errors.append({"index": str(i), "message": "缺少 value"})
                continue

            # 数字类型检查范围
            if field_def.type == "number" and isinstance(value, (int, float)):
                if field_def.min is not None and value < field_def.min:
                    errors.append(
                        {
                            "index": str(i),
                            "message": f"值 {value} 低于最小值 {field_def.min}",
                        }
                    )
                if field_def.max is not None and value > field_def.max:
                    errors.append(
                        {
                            "index": str(i),
                            "message": f"值 {value} 超过最大值 {field_def.max}",
                        }
                    )

            valid_count += 1

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "total_conditions": len(conditions),
            "valid_conditions": valid_count,
        }

    async def get_industries(self) -> dict[str, Any]:
        """获取行业列表（含股票数量统计）"""
        from core.market_data.repositories.stock_info import StockInfoRepository

        repo = StockInfoRepository()
        pipeline = [
            {"$match": {"status": "L", "industry": {"$ne": None, "$nin": ["", None]}}},
            {"$group": {"_id": "$industry", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        results = await repo.aggregate(pipeline)  # type: ignore[arg-type]

        industries = [
            {"value": r["_id"], "label": r["_id"], "count": r["count"]} for r in results if r["_id"]
        ]
        return {
            "industries": industries,
            "total": len(industries),
            "source": "database",
        }

    def _build_sort_stage(self, order_by: list[dict[str, Any]] | None) -> dict[str, Any] | None:
        """构建排序阶段"""
        if not order_by:
            return None

        sort_doc: dict[str, int] = {}
        for item in order_by:
            field_name = item.get("field", "")
            direction = item.get("direction", "desc")
            field_def = FIELDS_MAP.get(field_name)
            if field_def:
                sort_doc[field_def.db_field] = 1 if direction == "asc" else -1

        if not sort_doc:
            return None
        return {"$sort": sort_doc}
