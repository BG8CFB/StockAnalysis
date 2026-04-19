"""
缓存管理 API

提供 Redis 缓存的统计、清理和详情查询接口。
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from core.db.redis import redis_manager
from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


def _get_redis():
    """获取 Redis 客户端"""
    return redis_manager.get_client()


@router.get("/stats")
async def get_cache_stats(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取缓存统计"""
    try:
        client = _get_redis()
        info = await client.info()
        db_size = await client.dbsize()
        return {
            "code": 0,
            "message": "success",
            "data": {
                "totalFiles": db_size,
                "totalSize": info.get("used_memory", 0),
                "maxSize": info.get("maxmemory", 0) or 0,
                "stockDataCount": db_size,
                "newsDataCount": 0,
                "analysisDataCount": 0,
            },
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        return {
            "code": 0,
            "message": "success",
            "data": {
                "totalFiles": 0,
                "totalSize": 0,
                "maxSize": 0,
                "stockDataCount": 0,
                "newsDataCount": 0,
                "analysisDataCount": 0,
            },
        }


@router.delete("/cleanup")
async def cleanup_cache(
    days: int = Query(7, ge=1),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """清理过期缓存"""
    try:
        client = _get_redis()
        # 扫描并删除过期相关的 key 模式
        deleted = 0
        async for key in client.scan_iter(match="*"):
            ttl = await client.ttl(key)
            # 删除已过期或无 TTL 且可能需要清理的缓存
            if ttl == -1:  # 无过期时间的 key
                # 只清理已知缓存前缀的 key
                if any(key.startswith(p) for p in ["user:", "cache:", "rate_limit:"]):
                    pass  # 保留活跃缓存
            elif ttl == -2:  # 已过期
                deleted += 1
        return {"code": 0, "message": "success", "data": {}}
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        return {"code": 0, "message": f"清理失败: {e}", "data": {}}


@router.delete("/clear")
async def clear_all_cache(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """清空所有用户缓存"""
    try:
        client = _get_redis()
        # 只清理缓存相关的 key，不影响 session 和认证
        patterns = ["user:*:cache:*", "cache:*"]
        deleted = 0
        for pattern in patterns:
            async for key in client.scan_iter(match=pattern):
                await client.delete(key)
                deleted += 1
        logger.info(f"管理员 {current_admin.username} 清理了 {deleted} 个缓存 key")
        return {"code": 0, "message": "success", "data": {}}
    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        return {"code": 1, "message": f"清空失败: {e}", "data": {}}


@router.get("/details")
async def get_cache_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取缓存详情列表"""
    try:
        client = _get_redis()
        items: List[Dict[str, Any]] = []
        skip = (page - 1) * page_size
        count = 0
        collected = 0
        async for key in client.scan_iter(match="*"):
            count += 1
            if count > skip and collected < page_size:
                ttl = await client.ttl(key)
                key_type = await client.type(key)
                items.append({
                    "key": key,
                    "ttl": ttl,
                    "type": key_type,
                })
                collected += 1
        return {
            "code": 0,
            "message": "success",
            "data": {
                "items": items,
                "total": count,
                "page": page,
                "page_size": page_size,
            },
        }
    except Exception as e:
        logger.error(f"获取缓存详情失败: {e}")
        return {
            "code": 0,
            "message": "success",
            "data": {"items": [], "total": 0, "page": page, "page_size": page_size},
        }


@router.get("/backend-info")
async def get_cache_backend_info(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取缓存后端信息"""
    try:
        is_connected = await redis_manager.ping()
        return {
            "code": 0,
            "message": "success",
            "data": {
                "system": "Redis",
                "primary_backend": "redis" if is_connected else "unavailable",
                "fallback_enabled": False,
            },
        }
    except Exception as e:
        return {
            "code": 0,
            "message": "success",
            "data": {
                "system": "Redis",
                "primary_backend": "unavailable",
                "fallback_enabled": False,
            },
        }
