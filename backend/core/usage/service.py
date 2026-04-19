"""
用量统计服务

从 analysis_tasks 集合聚合 token 使用数据。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)


def _get_collection():
    """获取分析任务集合"""
    return mongodb.get_collection("analysis_tasks")


async def get_statistics(days: int) -> Dict[str, Any]:
    """获取总体用量统计"""
    collection = _get_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    match_stage = {"$match": {"created_at": {"$gte": cutoff}}}

    by_provider_pipeline = [
        match_stage,
        {"$group": {
            "_id": "$token_usage.provider",
            "requests": {"$sum": 1},
            "tokens": {"$sum": "$token_usage.total_tokens"},
            "cost": {"$sum": "$token_usage.total_cost"},
        }},
    ]

    by_model_pipeline = [
        match_stage,
        {"$group": {
            "_id": "$token_usage.model_name",
            "requests": {"$sum": 1},
            "tokens": {"$sum": "$token_usage.total_tokens"},
            "cost": {"$sum": "$token_usage.total_cost"},
        }},
    ]

    by_date_pipeline = [
        match_stage,
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "requests": {"$sum": 1},
            "tokens": {"$sum": "$token_usage.total_tokens"},
            "cost": {"$sum": "$token_usage.total_cost"},
        }},
        {"$sort": {"_id": 1}},
    ]

    total_pipeline = [
        match_stage,
        {"$group": {
            "_id": None,
            "total_requests": {"$sum": 1},
            "total_input_tokens": {"$sum": "$token_usage.input_tokens"},
            "total_output_tokens": {"$sum": "$token_usage.output_tokens"},
            "total_cost": {"$sum": "$token_usage.total_cost"},
        }},
    ]

    total_result = await collection.aggregate(total_pipeline).to_list(1)
    total_doc = total_result[0] if total_result else {
        "total_requests": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost": 0,
    }

    by_provider: Dict[str, Any] = {}
    async for doc in collection.aggregate(by_provider_pipeline):
        key = doc["_id"] or "unknown"
        by_provider[key] = {"requests": doc["requests"], "tokens": doc["tokens"], "cost": doc["cost"]}

    by_model: Dict[str, Any] = {}
    async for doc in collection.aggregate(by_model_pipeline):
        key = doc["_id"] or "unknown"
        by_model[key] = {"requests": doc["requests"], "tokens": doc["tokens"], "cost": doc["cost"]}

    by_date: Dict[str, Any] = {}
    async for doc in collection.aggregate(by_date_pipeline):
        by_date[doc["_id"]] = {
            "requests": doc["requests"],
            "tokens": doc["tokens"],
            "cost": doc["cost"],
        }

    return {
        "total_requests": total_doc.get("total_requests", 0),
        "total_input_tokens": total_doc.get("total_input_tokens", 0) or 0,
        "total_output_tokens": total_doc.get("total_output_tokens", 0) or 0,
        "total_cost": total_doc.get("total_cost", 0) or 0,
        "cost_by_currency": {"CNY": total_doc.get("total_cost", 0) or 0},
        "by_provider": by_provider,
        "by_model": by_model,
        "by_date": by_date,
    }


async def get_cost_by_provider(days: int) -> Dict[str, Any]:
    """按供应商统计成本"""
    collection = _get_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$token_usage.provider",
            "cost": {"$sum": "$token_usage.total_cost"},
            "count": {"$sum": 1},
        }},
    ]

    result: Dict[str, Any] = {}
    async for doc in collection.aggregate(pipeline):
        key = doc["_id"] or "unknown"
        result[key] = {"cost": doc["cost"] or 0, "count": doc["count"]}
    return result


async def get_cost_by_model(days: int) -> Dict[str, Any]:
    """按模型统计成本"""
    collection = _get_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$token_usage.model_name",
            "cost": {"$sum": "$token_usage.total_cost"},
            "count": {"$sum": 1},
        }},
    ]

    result: Dict[str, Any] = {}
    async for doc in collection.aggregate(pipeline):
        key = doc["_id"] or "unknown"
        result[key] = {"cost": doc["cost"] or 0, "count": doc["count"]}
    return result


async def get_daily_cost(days: int) -> List[Dict[str, Any]]:
    """获取每日成本统计"""
    collection = _get_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "cost": {"$sum": "$token_usage.total_cost"},
            "tokens": {"$sum": "$token_usage.total_tokens"},
        }},
        {"$sort": {"_id": 1}},
    ]

    result = []
    async for doc in collection.aggregate(pipeline):
        result.append({
            "date": doc["_id"],
            "cost": doc["cost"] or 0,
            "tokens": doc["tokens"] or 0,
        })
    return result


async def get_usage_records(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """获取使用记录列表"""
    collection = _get_collection()
    query: Dict[str, Any] = {}

    if provider:
        query["token_usage.provider"] = provider
    if model_name:
        query["token_usage.model_name"] = model_name
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
        records.append({
            "id": str(doc.get("_id", "")),
            "timestamp": doc.get("created_at", datetime.now(timezone.utc)).isoformat()
            if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", "")),
            "provider": token_usage.get("provider", ""),
            "model_name": token_usage.get("model_name", ""),
            "input_tokens": token_usage.get("input_tokens", 0),
            "output_tokens": token_usage.get("output_tokens", 0),
            "cost": token_usage.get("total_cost", 0),
            "currency": "CNY",
            "session_id": str(doc.get("user_id", "")),
            "analysis_type": "trading_agents",
            "stock_code": doc.get("stock_code", ""),
        })

    return {"records": records, "total": total}
