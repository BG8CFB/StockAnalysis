"""
操作日志 API

提供审计/操作日志的查询、统计和清理接口。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from core.db.mongodb import mongodb
from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system/logs", tags=["operation-logs"])


def _get_collection() -> Any:
    """获取审计日志集合"""
    return mongodb.get_collection("audit_logs")


def _convert_objectids(obj: Any) -> Any:
    """递归将 ObjectId 转为字符串，避免序列化失败"""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _convert_objectids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_objectids(v) for v in obj]
    return obj


@router.get("/list")
async def get_operation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    keyword: Optional[str] = Query(None),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取操作日志列表"""
    collection = _get_collection()
    query: Dict[str, Any] = {}

    if start_date or end_date:
        date_filter: Dict[str, str] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["timestamp"] = date_filter

    if action_type:
        query["action_type"] = action_type
    if success is not None:
        query["success"] = success
    if keyword:
        query["$or"] = [
            {"action": {"$regex": keyword, "$options": "i"}},
            {"username": {"$regex": keyword, "$options": "i"}},
            {"error_message": {"$regex": keyword, "$options": "i"}},
        ]

    total = await collection.count_documents(query)
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    cursor = collection.find(query).sort("timestamp", -1).skip(skip).limit(page_size)
    logs = []
    async for doc in cursor:
        doc = _convert_objectids(doc)
        doc["id"] = str(doc.pop("_id"))
        # 确保前端需要的字段都有默认值
        doc.setdefault("user_id", "")
        doc.setdefault("username", "")
        doc.setdefault("action_type", "")
        doc.setdefault("action", "")
        doc.setdefault("success", True)
        doc.setdefault("duration_ms", None)
        doc.setdefault("ip_address", None)
        doc.setdefault("error_message", None)
        doc.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        doc.setdefault("details", None)
        if isinstance(doc.get("timestamp"), datetime):
            doc["timestamp"] = doc["timestamp"].isoformat()
        logs.append(doc)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "logs": logs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    }


@router.get("/stats")
async def get_operation_log_stats(
    days: int = Query(30, ge=1, le=365),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取操作日志统计"""
    collection = _get_collection()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 基础统计
    total_count = await collection.count_documents({"timestamp": {"$gte": cutoff.isoformat()}})
    success_count = await collection.count_documents(
        {
            "timestamp": {"$gte": cutoff.isoformat()},
            "success": True,
        }
    )
    failed_count = await collection.count_documents(
        {
            "timestamp": {"$gte": cutoff.isoformat()},
            "success": False,
        }
    )

    # 按操作类型统计
    by_action_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff.isoformat()}}},
        {"$group": {"_id": "$action_type", "count": {"$sum": 1}}},
    ]
    by_action: Dict[str, int] = {}
    async for doc in collection.aggregate(by_action_pipeline):
        if doc["_id"]:
            by_action[doc["_id"]] = doc["count"]

    # 按用户统计
    by_user_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff.isoformat()}}},
        {"$group": {"_id": "$username", "count": {"$sum": 1}}},
    ]
    by_user: Dict[str, int] = {}
    async for doc in collection.aggregate(by_user_pipeline):
        if doc["_id"]:
            by_user[doc["_id"]] = doc["count"]

    # 每日趋势
    daily_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff.isoformat()}}},
        {
            "$group": {
                "_id": {"$substr": ["$timestamp", 0, 10]},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    daily_trend: list = []
    async for doc in collection.aggregate(daily_pipeline):
        daily_trend.append({"date": doc["_id"], "count": doc["count"]})

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "by_action_type": by_action,
            "by_user": by_user,
            "daily_trend": daily_trend,
        },
    }


@router.get("/{log_id}")
async def get_operation_log_detail(
    log_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取操作日志详情"""
    from bson import ObjectId

    collection = _get_collection()
    try:
        doc = await collection.find_one({"_id": ObjectId(log_id)})
    except Exception:
        doc = await collection.find_one({"_id": log_id})

    if doc is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志不存在")

    doc = _convert_objectids(doc)
    doc["id"] = str(doc.pop("_id"))
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].isoformat()
    doc.setdefault("user_id", "")
    doc.setdefault("username", "")
    doc.setdefault("action_type", "")
    doc.setdefault("action", "")
    doc.setdefault("success", True)
    doc.setdefault("duration_ms", None)
    doc.setdefault("ip_address", None)
    doc.setdefault("error_message", None)
    doc.setdefault("details", None)

    return {"code": 0, "message": "success", "data": doc}


@router.post("/clear")
async def clear_operation_logs(
    request: dict,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """清空操作日志"""
    collection = _get_collection()
    query: Dict[str, Any] = {}
    days = request.get("days")
    action_type = request.get("action_type")

    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query["timestamp"] = {"$lt": cutoff}
    if action_type:
        query["action_type"] = action_type

    if not query:
        # 安全限制：不允许无条件清空
        return {
            "code": 1,
            "message": "必须指定清理条件（days 或 action_type）",
            "data": {"deleted_count": 0},
        }

    result = await collection.delete_many(query)
    logger.info(f"管理员 {current_admin.username} 清理了 {result.deleted_count} 条操作日志")
    return {
        "code": 0,
        "message": "success",
        "data": {"deleted_count": result.deleted_count},
    }
