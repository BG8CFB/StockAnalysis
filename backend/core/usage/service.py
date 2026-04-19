"""
用量统计服务

从 analysis_tasks 集合聚合 token 使用数据。
支持从 analysis_tasks 读取任务级汇总，从 ai_usage_stats 读取详细记录。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)


def _get_tasks_collection() -> Any:
    """获取分析任务集合"""
    return mongodb.get_collection("analysis_tasks")


def _get_usage_collection() -> Any:
    """获取 AI 使用详细记录集合"""
    return mongodb.get_collection("ai_usage_stats")


async def get_statistics(days: int) -> Dict[str, Any]:
    """获取总体用量统计（从 analysis_tasks 聚合任务级汇总）"""
    collection = _get_tasks_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    match_stage = {"$match": {"created_at": {"$gte": cutoff}}}

    # 总计：从 analysis_tasks 的 token_usage 字段聚合
    total_pipeline = [
        match_stage,
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "total_input_tokens": {"$sum": "$token_usage.prompt_tokens"},
                "total_output_tokens": {"$sum": "$token_usage.completion_tokens"},
                "total_tokens": {"$sum": "$token_usage.total_tokens"},
            }
        },
    ]

    total_result = await collection.aggregate(total_pipeline).to_list(1)
    total_doc = (
        total_result[0]
        if total_result
        else {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
        }
    )

    # 按日期聚合
    by_date_pipeline = [
        match_stage,
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "requests": {"$sum": 1},
                "tokens": {"$sum": "$token_usage.total_tokens"},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    by_date: Dict[str, Any] = {}
    async for doc in collection.aggregate(by_date_pipeline):
        by_date[doc["_id"]] = {
            "requests": doc["requests"],
            "tokens": doc["tokens"] or 0,
            "cost": 0,
        }

    # 尝试从 ai_usage_stats 获取更详细的按模型/供应商统计
    usage_collection = _get_usage_collection()
    by_provider: Dict[str, Any] = {}
    by_model: Dict[str, Any] = {}

    try:
        usage_match = {"$match": {"timestamp": {"$gte": cutoff}}}

        by_model_pipeline = [
            usage_match,
            {
                "$group": {
                    "_id": "$model_id",
                    "model_name": {"$first": "$model_name"},
                    "requests": {"$sum": 1},
                    "tokens": {"$sum": "$total_tokens"},
                    "cost": {"$sum": "$cost"},
                }
            },
        ]

        async for doc in usage_collection.aggregate(by_model_pipeline):
            key = doc["_id"] or "unknown"
            by_model[key] = {
                "requests": doc["requests"],
                "tokens": doc["tokens"] or 0,
                "cost": doc["cost"] or 0,
            }

        by_provider_pipeline = [
            usage_match,
            {
                "$group": {
                    "_id": "$model_name",
                    "requests": {"$sum": 1},
                    "tokens": {"$sum": "$total_tokens"},
                    "cost": {"$sum": "$cost"},
                }
            },
        ]

        async for doc in usage_collection.aggregate(by_provider_pipeline):
            key = doc["_id"] or "unknown"
            by_provider[key] = {
                "requests": doc["requests"],
                "tokens": doc["tokens"] or 0,
                "cost": doc["cost"] or 0,
            }
    except Exception as e:
        logger.debug(f"从 ai_usage_stats 聚合详细统计失败: {e}")

    return {
        "total_requests": total_doc.get("total_requests", 0),
        "total_input_tokens": total_doc.get("total_input_tokens", 0) or 0,
        "total_output_tokens": total_doc.get("total_output_tokens", 0) or 0,
        "total_tokens": total_doc.get("total_tokens", 0) or 0,
        "total_cost": 0,
        "cost_by_currency": {"CNY": 0},
        "by_provider": by_provider,
        "by_model": by_model,
        "by_date": by_date,
    }


async def get_cost_by_provider(days: int) -> Dict[str, Any]:
    """按供应商统计成本"""
    collection = _get_usage_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": "$model_name",
                "cost": {"$sum": "$cost"},
                "count": {"$sum": 1},
            }
        },
    ]

    result: Dict[str, Any] = {}
    try:
        async for doc in collection.aggregate(pipeline):
            key = doc["_id"] or "unknown"
            result[key] = {"cost": doc["cost"] or 0, "count": doc["count"]}
    except Exception:
        pass
    return result


async def get_cost_by_model(days: int) -> Dict[str, Any]:
    """按模型统计成本"""
    collection = _get_usage_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": "$model_id",
                "cost": {"$sum": "$cost"},
                "count": {"$sum": 1},
            }
        },
    ]

    result: Dict[str, Any] = {}
    try:
        async for doc in collection.aggregate(pipeline):
            key = doc["_id"] or "unknown"
            result[key] = {"cost": doc["cost"] or 0, "count": doc["count"]}
    except Exception:
        pass
    return result


async def get_daily_cost(days: int) -> List[Dict[str, Any]]:
    """获取每日成本统计"""
    collection = _get_tasks_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "tokens": {"$sum": "$token_usage.total_tokens"},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    result = []
    async for doc in collection.aggregate(pipeline):
        result.append(
            {
                "date": doc["_id"],
                "cost": 0,
                "tokens": doc["tokens"] or 0,
            }
        )
    return result


async def get_usage_records(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """获取使用记录列表（从 analysis_tasks 读取）"""
    collection = _get_tasks_collection()
    query: Dict[str, Any] = {}

    if start_date or end_date:
        date_filter: Dict[str, str] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["created_at"] = date_filter

    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).limit(limit)
    records = []
    async for doc in cursor:
        token_usage = doc.get("token_usage", {})
        records.append(
            {
                "id": str(doc.get("_id", "")),
                "timestamp": (
                    doc.get("created_at", datetime.now(timezone.utc)).isoformat()
                    if isinstance(doc.get("created_at"), datetime)
                    else str(doc.get("created_at", ""))
                ),
                "provider": "",
                "model_name": "",
                "input_tokens": token_usage.get("prompt_tokens", 0),
                "output_tokens": token_usage.get("completion_tokens", 0),
                "cost": 0,
                "currency": "CNY",
                "session_id": str(doc.get("user_id", "")),
                "analysis_type": "trading_agents",
                "stock_code": doc.get("stock_code", ""),
            }
        )

    return {"records": records, "total": total}
