"""
数据同步 API

包装现有 DataSyncService，提供 9 个 REST 端点供前端调用。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from core.auth.dependencies import get_current_active_user
from core.auth.models import UserModel
from core.market_data.models.datasource import DataSourceStatus, DataSourceType
from core.market_data.repositories.datasource import (
    DataSourceStatusHistoryRepository,
    DataSourceStatusRepository,
    SystemDataSourceRepository,
)
from core.market_data.services.data_sync_service import DataSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


def _get_sync_service() -> DataSyncService:
    """获取 DataSyncService 单例（延迟创建）"""
    return DataSyncService()


# ==================== 基础同步 ====================


@router.post("/stock_basics/run")
async def run_stock_basics_sync(
    force: bool = Query(default=False),
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """触发股票基础数据全量同步"""
    sync_service = _get_sync_service()
    result = await sync_service.sync_stock_list_with_fallback()
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/stock_basics/status")
async def get_stock_basics_status(
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取股票基础数据同步状态"""
    status_repo = DataSourceStatusRepository()
    statuses = await status_repo.find_many(
        {"data_type": "stock_list"},
        sort=[("last_check_at", -1)],
    )
    return {"code": 0, "data": statuses, "message": "ok"}


# ==================== 多数据源同步 ====================


@router.get("/multi-source/sources/status")
async def get_data_sources_status(
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取所有数据源状态"""
    system_repo = SystemDataSourceRepository()
    status_repo = DataSourceStatusRepository()

    configs = await system_repo.find_many({}, sort=[("priority", 1)])
    result: List[Dict[str, Any]] = []

    for cfg in configs:
        source_statuses = await status_repo.find_many(
            {"source_id": cfg["source_id"], "source_type": DataSourceType.SYSTEM.value},
            sort=[("last_check_at", -1)],
            limit=1,
        )
        latest = source_statuses[0] if source_statuses else {}
        result.append(
            {
                "name": cfg["source_id"],
                "priority": cfg.get("priority", 999),
                "available": latest.get("status") == DataSourceStatus.HEALTHY.value,
                "description": cfg.get("supported_data_types", []),
                "token_source": cfg.get("config", {}).get("api_token") and "configured" or None,
            }
        )

    return {"code": 0, "data": result, "message": "ok"}


@router.get("/multi-source/sources/current")
async def get_current_data_source(
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取当前使用的数据源"""
    system_repo = SystemDataSourceRepository()
    status_repo = DataSourceStatusRepository()

    configs = await system_repo.find_many(
        {"enabled": True, "market": "A_STOCK"},
        sort=[("priority", 1)],
    )
    for cfg in configs:
        src_id = cfg["source_id"]
        statuses = await status_repo.find_many(
            {
                "source_id": src_id,
                "source_type": DataSourceType.SYSTEM.value,
                "status": DataSourceStatus.HEALTHY.value,
            },
            limit=1,
        )
        if statuses:
            return {
                "code": 0,
                "data": {
                    "name": src_id,
                    "priority": cfg.get("priority", 999),
                    "description": cfg.get("supported_data_types", []),
                },
                "message": "ok",
            }

    return {"code": 0, "data": None, "message": "no healthy source"}


@router.get("/multi-source/status")
async def get_multi_source_sync_status(
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取多数据源同步状态"""
    status_repo = DataSourceStatusRepository()
    summary = await status_repo.get_status_summary()
    all_statuses = await status_repo.find_many({}, sort=[("last_check_at", -1)])
    return {
        "code": 0,
        "data": {"summary": summary, "sources": all_statuses},
        "message": "ok",
    }


@router.post("/multi-source/stock_basics/run")
async def run_multi_source_sync(
    force: bool = Query(default=False),
    preferred_sources: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """触发多数据源股票基础信息同步"""
    sync_service = _get_sync_service()
    result = await sync_service.sync_stock_list_with_fallback()
    return {"code": 0, "data": result, "message": "ok"}


@router.post("/multi-source/test-sources")
async def test_data_sources(
    body: Optional[Dict[str, Any]] = None,
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """测试数据源连通性"""
    from core.market_data.services.source_monitor_service import SourceMonitorService

    body = body or {}
    source_name = body.get("source_name")

    monitor = SourceMonitorService()
    system_repo = SystemDataSourceRepository()

    configs = await system_repo.find_many({"enabled": True}, sort=[("priority", 1)])
    if source_name:
        configs = [c for c in configs if c["source_id"] == source_name]

    test_results: List[Dict[str, Any]] = []
    for cfg in configs:
        src_id = cfg["source_id"]
        market = cfg.get("market", "A_STOCK")
        try:
            check = await monitor.check_single_source(
                source_id=src_id,
                market=market,
                data_type="stock_list",
                check_type="manual_test",
            )
            test_results.append(
                {
                    "name": src_id,
                    "priority": cfg.get("priority", 999),
                    "available": check.get("status") == "healthy",
                    "message": (
                        "ok"
                        if check.get("status") == "healthy"
                        else check.get("error", "unavailable")
                    ),
                }
            )
        except Exception as e:
            test_results.append(
                {
                    "name": src_id,
                    "priority": cfg.get("priority", 999),
                    "available": False,
                    "message": str(e),
                }
            )

    return {"code": 0, "data": {"test_results": test_results}, "message": "ok"}


@router.get("/multi-source/recommendations")
async def get_sync_recommendations(
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取数据源使用建议"""
    status_repo = DataSourceStatusRepository()
    system_repo = SystemDataSourceRepository()

    configs = await system_repo.find_many(
        {"enabled": True, "market": "A_STOCK"},
        sort=[("priority", 1)],
    )

    primary_source = None
    fallback_sources: List[Dict[str, Any]] = []
    suggestions: List[str] = []
    warnings: List[str] = []

    for cfg in configs:
        src_id = cfg["source_id"]
        healthy_statuses = await status_repo.find_many(
            {"source_id": src_id, "status": DataSourceStatus.HEALTHY.value},
            limit=1,
        )
        is_healthy = len(healthy_statuses) > 0

        entry = {"name": src_id, "priority": cfg.get("priority", 999)}
        if is_healthy and primary_source is None:
            primary_source = entry
        else:
            fallback_sources.append(entry)

        if not is_healthy:
            warnings.append(f"数据源 {src_id} 当前不可用")

    if primary_source is None:
        suggestions.append("未找到可用的主数据源，请检查数据源配置")
        if not configs:
            suggestions.append("尚未配置任何数据源")

    return {
        "code": 0,
        "data": {
            "primary_source": primary_source,
            "fallback_sources": fallback_sources,
            "suggestions": suggestions,
            "warnings": warnings,
        },
        "message": "ok",
    }


@router.get("/multi-source/history")
async def get_sync_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取同步历史记录"""
    history_repo = DataSourceStatusHistoryRepository()

    filter_query: Dict[str, Any] = {}
    if status:
        filter_query["event_type"] = status

    total = await history_repo.count_documents(filter_query)
    records = await history_repo.find_many(
        filter_query,
        sort=[("timestamp", -1)],
        limit=page_size,
        skip=(page - 1) * page_size,
    )

    return {
        "code": 0,
        "data": {
            "records": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
        },
        "message": "ok",
    }
