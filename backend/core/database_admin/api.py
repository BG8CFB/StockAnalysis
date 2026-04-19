"""
数据库管理 API

提供 MongoDB + Redis 的状态查询、备份、清理等管理接口。
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.db.mongodb import mongodb
from core.db.redis import redis_manager
from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system/database", tags=["database-admin"])


class BackupRequest(BaseModel):
    """备份请求"""

    name: str
    collections: List[str] = []


class CleanupRequest(BaseModel):
    """清理请求"""

    days: int = 30


# 内存存储备份元数据（简化实现）
_backups: Dict[str, Dict[str, Any]] = {}


@router.get("/status")
async def get_database_status(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取数据库连接状态"""
    # MongoDB 状态
    mongo_status: Dict[str, Any] = {"status": "disconnected"}
    try:
        client = mongodb.client
        if client:
            server_info = await client.server_info()
            db = mongodb.database
            collections = await db.list_collection_names()
            mongo_status = {
                "status": "connected",
                "version": server_info.get("version", "unknown"),
                "collections_count": len(collections),
            }
    except Exception as e:
        mongo_status = {"status": "error", "error": str(e)}

    # Redis 状态
    redis_status: Dict[str, Any] = {"status": "disconnected"}
    try:
        is_connected = await redis_manager.ping()
        if is_connected:
            redis_client = redis_manager.get_client()
            info = await redis_client.info("server")
            redis_status = {
                "status": "connected",
                "version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
    except Exception as e:
        redis_status = {"status": "error", "error": str(e)}

    return {
        "code": 0,
        "message": "success",
        "data": {"mongodb": mongo_status, "redis": redis_status},
    }


@router.get("/stats")
async def get_database_stats(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取数据库统计信息"""
    try:
        db = mongodb.database
        collections = await db.list_collection_names()
        collection_stats: List[Dict[str, Any]] = []
        total_docs = 0
        total_size = 0

        for coll_name in collections:
            try:
                count = await db[coll_name].estimated_document_count()
                stats = await db.command("collStats", coll_name)
                size = stats.get("size", 0)
                total_docs += count
                total_size += size
                collection_stats.append(
                    {
                        "name": coll_name,
                        "documents": count,
                        "size": size,
                    }
                )
            except Exception:
                collection_stats.append(
                    {
                        "name": coll_name,
                        "documents": 0,
                        "size": 0,
                    }
                )

        return {
            "code": 0,
            "message": "success",
            "data": {
                "total_collections": len(collections),
                "total_documents": total_docs,
                "total_size": total_size,
                "collections": collection_stats,
            },
        }
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {e}",
        )


@router.post("/test")
async def test_database_connections(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """测试数据库连接"""
    results: Dict[str, Any] = {}

    # 测试 MongoDB
    try:
        client = mongodb.client
        await client.admin.command("ping")
        results["mongodb"] = {"connected": True, "message": "连接正常"}
    except Exception as e:
        results["mongodb"] = {"connected": False, "message": str(e)}

    # 测试 Redis
    try:
        is_connected = await redis_manager.ping()
        results["redis"] = {
            "connected": is_connected,
            "message": "连接正常" if is_connected else "连接失败",
        }
    except Exception as e:
        results["redis"] = {"connected": False, "message": str(e)}

    return {"code": 0, "message": "success", "data": results}


@router.post("/backup")
async def create_backup(
    request: BackupRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """创建数据库备份（记录元数据）"""
    backup_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    try:
        db = mongodb.database
        collections = request.collections or await db.list_collection_names()

        # 记录备份元数据
        backup_info = {
            "id": backup_id,
            "name": request.name,
            "size": 0,
            "created_at": now.isoformat(),
            "collections": collections,
            "created_by": str(current_admin.id),
        }
        _backups[backup_id] = backup_info

        # 保存到数据库
        await db.database_backups.insert_one(
            {
                **backup_info,
                "_id": backup_id,
            }
        )

        logger.info(f"管理员 {current_admin.username} 创建了数据库备份: {request.name}")
        return {"code": 0, "message": "success", "data": backup_info}
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建备份失败: {e}",
        )


@router.get("/backups")
async def list_backups(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取备份列表"""
    try:
        db = mongodb.database
        backups = []
        async for doc in db.database_backups.find().sort("created_at", -1):
            doc["id"] = str(doc.pop("_id", doc.get("id", "")))
            backups.append(doc)
        return {"code": 0, "message": "success", "data": backups}
    except Exception:
        # 如果集合不存在，返回空列表
        return {"code": 0, "message": "success", "data": []}


@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """删除备份"""
    try:
        db = mongodb.database
        result = await db.database_backups.delete_one({"_id": backup_id})
        if result.deleted_count == 0:
            _backups.pop(backup_id, None)
        return {"code": 0, "message": "success", "data": {}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除备份失败: {e}",
        )


@router.post("/cleanup")
async def cleanup_old_data(
    request: CleanupRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """清理旧数据"""
    try:
        db = mongodb.database
        cutoff = datetime.now(timezone.utc)
        from datetime import timedelta

        cutoff_date = cutoff - timedelta(days=request.days)
        deleted_count = 0

        # 清理过期的临时数据
        for coll_name in ["temp_data", "expired_tasks"]:
            try:
                result = await db[coll_name].delete_many({"created_at": {"$lt": cutoff_date}})
                deleted_count += result.deleted_count
            except Exception:
                pass

        logger.info(f"管理员 {current_admin.username} 清理了 {deleted_count} 条旧数据")
        return {
            "code": 0,
            "message": "success",
            "data": {"deleted_count": deleted_count},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理数据失败: {e}",
        )


@router.post("/cleanup/analysis")
async def cleanup_analysis_results(
    request: CleanupRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """清理过期分析结果"""
    try:
        db = mongodb.database
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=request.days)
        deleted_count = 0

        # 清理已过期且超过保留期的分析任务
        result = await db.analysis_tasks.delete_many(
            {
                "status": {"$in": ["completed", "failed", "cancelled", "expired"]},
                "completed_at": {"$lt": cutoff_date},
            }
        )
        deleted_count += result.deleted_count

        logger.info(f"管理员 {current_admin.username} 清理了 {deleted_count} 条过期分析结果")
        return {
            "code": 0,
            "message": "success",
            "data": {"deleted_count": deleted_count},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理分析结果失败: {e}",
        )


@router.post("/cleanup/logs")
async def cleanup_operation_logs(
    request: CleanupRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """清理操作日志"""
    try:
        db = mongodb.database
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=request.days)
        deleted_count = 0

        # 清理审计日志
        result = await db.audit_logs.delete_many({"timestamp": {"$lt": cutoff_date}})
        deleted_count += result.deleted_count

        logger.info(f"管理员 {current_admin.username} 清理了 {deleted_count} 条操作日志")
        return {
            "code": 0,
            "message": "success",
            "data": {"deleted_count": deleted_count},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理操作日志失败: {e}",
        )
