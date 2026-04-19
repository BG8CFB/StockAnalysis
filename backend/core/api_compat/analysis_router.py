"""
Analysis API 适配器路由

将前端 /api/analysis/* 请求适配到现有 trading_agents 服务。
前端使用 { success, data, message } 响应格式。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.auth.dependencies import (
    get_current_active_user,
    get_current_user_from_query,
)
from core.background_tasks import create_analysis_task_background
from core.db.mongodb import mongodb
from core.settings.services.user_service import get_user_settings_service
from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel
from modules.trading_agents.manager.batch_manager import get_batch_manager
from modules.trading_agents.manager.task_manager import get_task_manager
from modules.trading_agents.schemas import (
    AnalysisStagesConfig,
    AnalysisTaskCreate,
    BatchTaskCreate,
    TaskStatusEnum,
)

logger = logging.getLogger(__name__)

# =============================================================================
# 响应辅助
# =============================================================================


def ok(data: Any, message: str = "success") -> Dict[str, Any]:
    """标准成功响应"""
    return {"success": True, "data": data, "message": message}


def fail(message: str, code: int = -1) -> Dict[str, Any]:
    """标准失败响应"""
    return {"success": False, "data": None, "message": message, "code": code}


# =============================================================================
# 请求模型
# =============================================================================


class SingleAnalysisRequest(BaseModel):
    """前端单股分析请求"""

    symbol: Optional[str] = None
    stock_code: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class BatchAnalysisRequest(BaseModel):
    """前端批量分析请求"""

    title: str
    description: Optional[str] = None
    symbols: Optional[List[str]] = None
    stock_codes: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None


# =============================================================================
# 辅助：从前端请求参数解析 stages / models
# =============================================================================


def _parse_stages_from_params(params: Optional[Dict[str, Any]]) -> AnalysisStagesConfig:
    """从前端 parameters 字段解析阶段配置"""
    if not params:
        return AnalysisStagesConfig()

    from modules.trading_agents.schemas import (
        DebateConfig,
        Stage1Config,
        Stage2Config,
        Stage3Config,
        Stage4Config,
    )

    stage1 = Stage1Config(
        enabled=True,
        selected_agents=params.get("selected_analysts", []),
    )
    stage2 = Stage2Config(
        enabled=params.get("phase2_enabled", True),
        debate=DebateConfig(rounds=params.get("phase2_debate_rounds", 3)),
    )
    stage3 = Stage3Config(
        enabled=params.get("phase3_enabled", True),
        debate=DebateConfig(rounds=params.get("phase3_debate_rounds", 3)),
    )
    stage4 = Stage4Config(
        enabled=params.get("phase4_enabled", True),
    )
    return AnalysisStagesConfig(
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        stage4=stage4,
    )


def _resolve_stock_code(req: SingleAnalysisRequest) -> str:
    """从请求中提取股票代码"""
    code = req.stock_code or req.symbol or ""
    if not code:
        raise HTTPException(status_code=400, detail="必须提供 symbol 或 stock_code")
    return code


def _resolve_market(params: Optional[Dict[str, Any]]) -> str:
    """从前端参数解析市场类型"""
    if not params:
        return "A_STOCK"
    market_map = {"美股": "US_STOCK", "A股": "A_STOCK", "港股": "HK_STOCK"}
    mt = params.get("market_type", "A股")
    return market_map.get(mt, "A_STOCK")


# =============================================================================
# 路由
# =============================================================================

router = APIRouter(prefix="/analysis", tags=["Analysis API 兼容层"])
stream_router = APIRouter(tags=["Analysis Stream 兼容层"])

# SSE ticket 有效期
_STREAM_TICKET_TTL = 90


# ----- 单股分析 -----
@router.post("/single")
async def create_single_analysis(
    request: SingleAnalysisRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """提交单股分析"""
    stock_code = _resolve_stock_code(request)
    params = request.parameters or {}
    market = _resolve_market(params)
    stages = _parse_stages_from_params(params)
    trade_date = params.get(
        "analysis_date",
        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )

    settings_service = get_user_settings_service()
    user_id = str(current_user.id)

    allowed, error_msg = await settings_service.check_task_quota_batch(user_id, 1)
    if not allowed:
        return fail(f"配额不足: {error_msg}", 429)

    try:
        task_create_task = asyncio.create_task(
            create_analysis_task_background(
                user_id=user_id,
                request=AnalysisTaskCreate(
                    stock_code=stock_code,
                    market=market,
                    trade_date=trade_date,
                    stages=stages,
                    data_collection_model=params.get("quick_analysis_model"),
                    debate_model=params.get("deep_analysis_model"),
                ),
                config={},
            )
        )
        task_id = await asyncio.wait_for(task_create_task, timeout=10.0)
        await settings_service.increment_task_usage(user_id)
        return ok(
            {
                "task_id": task_id,
                "analysis_id": task_id,
                "status": "pending",
                "message": "分析任务已创建",
            }
        )
    except asyncio.TimeoutError:
        return fail("任务创建超时")
    except Exception as e:
        logger.error(f"单股分析创建失败: {e}", exc_info=True)
        return fail(f"任务创建失败: {e}")


# ----- 批量分析 -----
@router.post("/batch")
async def create_batch_analysis(
    request: BatchAnalysisRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """提交批量分析"""
    raw_codes = request.stock_codes or request.symbols or []
    if not raw_codes:
        return fail("必须提供 stock_codes 或 symbols")

    params = request.parameters or {}
    market = _resolve_market(params)
    stages = _parse_stages_from_params(params)
    trade_date = params.get(
        "analysis_date",
        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )

    settings_service = get_user_settings_service()
    user_id = str(current_user.id)

    allowed, error_msg = await settings_service.check_task_quota_batch(user_id, len(raw_codes))
    if not allowed:
        return fail(f"配额不足: {error_msg}", 429)

    task_manager = get_task_manager()
    try:
        batch_id = await task_manager.create_batch_task(
            user_id=user_id,
            request=BatchTaskCreate(
                stock_codes=raw_codes,
                market=market,
                trade_date=trade_date,
                stages=stages,
                data_collection_model=params.get("quick_analysis_model"),
                debate_model=params.get("deep_analysis_model"),
                batch_name=request.title,
            ),
            config={},
        )
        for _ in range(len(raw_codes)):
            await settings_service.increment_task_usage(user_id)

        return ok(
            {
                "batch_id": batch_id,
                "total_tasks": len(raw_codes),
                "task_ids": [],
                "mapping": [{"symbol": c, "stock_code": c, "task_id": ""} for c in raw_codes],
                "status": "pending",
            }
        )
    except Exception as e:
        logger.error(f"批量分析创建失败: {e}", exc_info=True)
        return fail(f"批量任务创建失败: {e}")


# ----- 任务列表 -----
@router.get("/tasks")
async def list_user_tasks(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取当前用户的任务列表"""
    task_manager = get_task_manager()
    user_id = str(current_user.id)

    status_enum = None
    if status:
        try:
            status_enum = TaskStatusEnum(status)
        except ValueError:
            pass

    tasks = await task_manager.list_tasks(
        user_id=user_id,
        status=status_enum,
        limit=limit,
        offset=offset,
    )
    total = await task_manager.count_tasks(user_id=user_id, status=status_enum)

    # 转换为前端 AnalysisTask 格式
    mapped = []
    for t in tasks:
        mapped.append(
            {
                "task_id": t["id"],
                "symbol": t.get("stock_code", ""),
                "stock_code": t.get("stock_code", ""),
                "status": _map_status(t["status"]),
                "progress": t.get("progress", 0.0),
                "created_at": _fmt_dt(t.get("created_at")),
                "started_at": _fmt_dt(t.get("started_at")),
                "completed_at": _fmt_dt(t.get("completed_at")),
            }
        )

    return ok(
        {
            "tasks": mapped,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


# ----- 所有任务（管理员） -----
@router.get("/tasks/all")
async def list_all_tasks(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_user: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取所有任务列表（管理员）"""
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status

    collection = mongodb.database.analysis_tasks
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip(offset).limit(limit)

    tasks = []
    async for doc in cursor:
        tasks.append(
            {
                "task_id": str(doc["_id"]),
                "symbol": doc.get("stock_code", ""),
                "stock_code": doc.get("stock_code", ""),
                "status": _map_status(doc["status"]),
                "progress": doc.get("progress", 0.0),
                "created_at": _fmt_dt(doc.get("created_at")),
                "started_at": _fmt_dt(doc.get("started_at")),
                "completed_at": _fmt_dt(doc.get("completed_at")),
                "user_id": doc.get("user_id"),
            }
        )

    return ok({"tasks": tasks, "total": total, "limit": limit, "offset": offset})


# ----- 任务状态 -----
@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取任务状态"""
    task_manager = get_task_manager()
    try:
        info = await task_manager.get_task_status(task_id)
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise

    if info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此任务")

    return ok(
        {
            "task_id": info["id"],
            "status": _map_status(info["status"]),
            "progress": info.get("progress", 0.0),
            "message": _phase_label(info.get("current_phase", 0)),
            "current_step": _phase_label(info.get("current_phase", 0)),
            "stock_code": info.get("stock_code", ""),
            "stock_symbol": info.get("stock_code", ""),
            "error_message": info.get("error_message"),
        }
    )


# ----- 任务结果 -----
@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取任务结果"""
    task_manager = get_task_manager()
    try:
        info = await task_manager.get_task_status(task_id)
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise

    if info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此任务")

    reports = info.get("reports", {}) or {}
    final_report = reports.get("final_report") or reports.get("summarizer", "")
    token_usage = info.get("token_usage", {}) or {}

    # 从最终报告和任务数据中提取实际值
    confidence_score = _extract_confidence_score(final_report, info)
    risk_level = info.get("risk_level") or _extract_risk_level(final_report)
    key_points = _extract_key_points(final_report)
    execution_time = _calc_execution_time(info.get("started_at"), info.get("completed_at"))
    total_tokens = token_usage.get("total_tokens", 0)

    return ok(
        {
            "analysis_id": info["id"],
            "stock_symbol": info.get("stock_code", ""),
            "stock_code": info.get("stock_code", ""),
            "analysis_date": info.get("trade_date", ""),
            "summary": final_report,
            "recommendation": info.get("final_recommendation", ""),
            "confidence_score": confidence_score,
            "risk_level": risk_level,
            "key_points": key_points,
            "charts": [],
            "tokens_used": total_tokens,
            "execution_time": execution_time,
            "error_message": info.get("error_message"),
            "reports": reports,
            "status": _map_status(info["status"]),
            "created_at": _fmt_dt(info.get("created_at")),
            "updated_at": _fmt_dt(info.get("completed_at")),
        }
    )


# ----- 任务详情 -----
@router.get("/tasks/{task_id}/details")
async def get_task_details(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取任务完整详情"""
    task_manager = get_task_manager()
    try:
        info = await task_manager.get_task_status(task_id)
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise

    if info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此任务")

    return ok(info)


# ----- 取消任务 -----
@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """取消任务"""
    task_manager = get_task_manager()
    try:
        info = await task_manager.get_task_status(task_id)
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise

    if info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权操作此任务")

    status_val = info.get("status")
    if status_val == TaskStatusEnum.RUNNING.value:
        await task_manager.stop_task(task_id)
    else:
        await task_manager.cancel_task(task_id)

    return ok({"success": True, "message": "任务已取消"})


# ----- 标记失败 -----
@router.post("/tasks/{task_id}/mark-failed")
async def mark_task_failed(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """将任务标记为失败"""
    task_manager = get_task_manager()
    try:
        info = await task_manager.get_task_status(task_id)
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise

    if info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权操作此任务")

    await task_manager.fail_task(task_id, "用户手动标记为失败")
    return ok({"success": True, "message": "任务已标记为失败"})


# ----- 删除任务 -----
@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除任务"""
    task_manager = get_task_manager()
    try:
        info = await task_manager.get_task_status(task_id)
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise

    if info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权操作此任务")

    if info["status"] == TaskStatusEnum.RUNNING.value:
        raise HTTPException(status_code=400, detail="运行中的任务不能删除，请先取消")

    await mongodb.database.analysis_tasks.delete_one({"_id": ObjectId(task_id)})
    return ok({"success": True, "message": "任务已删除"})


# ----- 用户历史 -----
@router.get("/user/history")
async def get_user_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stock_code: Optional[str] = None,
    market_type: Optional[str] = None,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取用户分析历史"""
    user_id = str(current_user.id)
    query: Dict[str, Any] = {"user_id": user_id}

    if status:
        query["status"] = status
    if stock_code:
        query["stock_code"] = stock_code
    if start_date or end_date:
        date_filter: Dict[str, Any] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["trade_date"] = date_filter

    collection = mongodb.database.analysis_tasks
    total = await collection.count_documents(query)
    skip = (page - 1) * page_size
    cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(page_size)

    items = []
    async for doc in cursor:
        items.append(
            {
                "task_id": str(doc["_id"]),
                "symbol": doc.get("stock_code", ""),
                "stock_code": doc.get("stock_code", ""),
                "status": _map_status(doc["status"]),
                "progress": doc.get("progress", 0.0),
                "created_at": _fmt_dt(doc.get("created_at")),
                "started_at": _fmt_dt(doc.get("started_at")),
                "completed_at": _fmt_dt(doc.get("completed_at")),
                "batch_id": doc.get("batch_id"),
            }
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return ok(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    )


# ----- 用户队列状态 -----
@router.get("/user/queue-status")
async def get_user_queue_status(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取用户队列状态"""
    task_manager = get_task_manager()
    user_id = str(current_user.id)

    pending = await task_manager.count_tasks(user_id, TaskStatusEnum.PENDING)
    running = await task_manager.count_tasks(user_id, TaskStatusEnum.RUNNING)
    completed = await task_manager.count_tasks(user_id, TaskStatusEnum.COMPLETED)
    failed = await task_manager.count_tasks(user_id, TaskStatusEnum.FAILED)

    return ok(
        {
            "pending": pending,
            "processing": running,
            "completed": completed,
            "failed": failed,
            "total": pending + running + completed + failed,
            "max_concurrent": 2,
            "current_processing": running,
        }
    )


# ----- 分析统计 -----
@router.get("/stats")
async def get_analysis_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    market_type: Optional[str] = None,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取分析统计"""
    user_id = str(current_user.id)
    query: Dict[str, Any] = {"user_id": user_id}

    if start_date or end_date:
        date_filter: Dict[str, Any] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["trade_date"] = date_filter

    collection = mongodb.database.analysis_tasks
    total = await collection.count_documents(query)
    successful = await collection.count_documents(
        {**query, "status": TaskStatusEnum.COMPLETED.value}
    )
    failed = await collection.count_documents({**query, "status": TaskStatusEnum.FAILED.value})

    # 按日期聚合
    pipeline_date: list[dict[str, Any]] = [
        {"$match": query},
        {"$group": {"_id": "$trade_date", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    analysis_by_date = []
    async for doc in collection.aggregate(pipeline_date):
        analysis_by_date.append({"date": doc["_id"] or "", "count": doc["count"]})

    # 热门股票
    pipeline_stock: list[dict[str, Any]] = [
        {"$match": query},
        {"$group": {"_id": "$stock_code", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    popular_stocks = []
    async for doc in collection.aggregate(pipeline_stock):
        popular_stocks.append(
            {
                "symbol": doc["_id"] or "",
                "name": doc["_id"] or "",
                "count": doc["count"],
            }
        )

    # 平均执行时长（从已完成任务中计算）
    pipeline_duration = [
        {
            "$match": {
                **query,
                "status": TaskStatusEnum.COMPLETED.value,
                "started_at": {"$ne": None},
                "completed_at": {"$ne": None},
            }
        },
        {
            "$project": {
                "duration": {"$divide": [{"$subtract": ["$completed_at", "$started_at"]}, 1000]}
            }
        },
        {"$group": {"_id": None, "avg_duration": {"$avg": "$duration"}}},
    ]
    avg_duration = 0
    async for doc in collection.aggregate(pipeline_duration):
        avg_duration = round(doc.get("avg_duration", 0) or 0, 1)

    # 总 Token 用量
    pipeline_tokens = [
        {"$match": query},
        {"$group": {"_id": None, "total_tokens": {"$sum": "$token_usage.total_tokens"}}},
    ]
    total_tokens = 0
    async for doc in collection.aggregate(pipeline_tokens):
        total_tokens = doc.get("total_tokens", 0) or 0

    # 按市场聚合
    pipeline_market = [
        {"$match": query},
        {"$group": {"_id": "$market", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    analysis_by_market = []
    async for doc in collection.aggregate(pipeline_market):
        analysis_by_market.append(
            {
                "market": doc["_id"] or "unknown",
                "count": doc["count"],
            }
        )

    return ok(
        {
            "total_analyses": total,
            "successful_analyses": successful,
            "failed_analyses": failed,
            "avg_duration": avg_duration,
            "total_tokens": total_tokens,
            "total_cost": 0,
            "popular_stocks": popular_stocks,
            "analysis_by_date": analysis_by_date,
            "analysis_by_market": analysis_by_market,
        }
    )


# ----- 股票信息 -----
@router.get("/stock-info")
async def get_stock_info(
    symbol: str = Query(...),
    market: str = Query("A_STOCK"),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取股票基础信息"""
    stock = await mongodb.database.stock_info.find_one({"code": symbol, "market": market})
    if not stock:
        stock = await mongodb.database.stock_info.find_one({"code": symbol})

    if not stock:
        return ok(
            {
                "symbol": symbol,
                "name": symbol,
                "market": market,
            }
        )

    return ok(
        {
            "symbol": symbol,
            "code": stock.get("code", symbol),
            "name": stock.get("name", symbol),
            "market": stock.get("market", market),
            "industry": stock.get("industry"),
            "sector": stock.get("sector"),
        }
    )


# ----- 搜索股票 -----
@router.get("/search")
async def search_stocks(
    query: str = Query(..., min_length=1),
    market: Optional[str] = None,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """搜索股票"""
    search_filter: Dict[str, Any] = {
        "$or": [
            {"code": {"$regex": query, "$options": "i"}},
            {"name": {"$regex": query, "$options": "i"}},
        ]
    }
    if market:
        market_map = {"美股": "US_STOCK", "A股": "A_STOCK", "港股": "HK_STOCK"}
        db_market = market_map.get(market, market)
        search_filter["market"] = db_market

    cursor = mongodb.database.stock_info.find(search_filter).limit(20)
    results = []
    async for doc in cursor:
        results.append(
            {
                "symbol": doc.get("code", ""),
                "name": doc.get("name", ""),
                "market": doc.get("market", ""),
                "type": "stock",
            }
        )

    return ok(results)


# ----- 热门股票 -----
@router.get("/popular")
async def get_popular_stocks(
    market: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取热门股票"""
    pipeline: list[dict[str, Any]] = [
        {"$group": {"_id": "$stock_code", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    if market:
        market_map = {"美股": "US_STOCK", "A股": "A_STOCK", "港股": "HK_STOCK"}
        db_market = market_map.get(market, market)
        pipeline.insert(0, {"$match": {"market": db_market}})

    results = []
    async for doc in mongodb.database.analysis_tasks.aggregate(pipeline):
        code = doc["_id"] or ""
        # 尝试从 stock_info 获取名称
        info = await mongodb.database.stock_info.find_one({"code": code})
        name = info.get("name", code) if info else code
        results.append(
            {
                "symbol": code,
                "name": name,
                "market": market or "",
                "current_price": 0,
                "change_percent": 0,
                "volume": 0,
                "analysis_count": doc["count"],
            }
        )

    return ok(results)


# ----- 批次详情 -----
@router.get("/batches/{batch_id}")
async def get_batch(
    batch_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取批次详情"""
    batch_manager = get_batch_manager()
    batch_status = await batch_manager.get_batch_status(batch_id)

    if not batch_status:
        # 尝试从任务中获取
        tasks_cursor = mongodb.database.analysis_tasks.find(
            {"batch_id": batch_id, "user_id": str(current_user.id)}
        )
        tasks = await tasks_cursor.to_list(length=None)
        if not tasks:
            raise HTTPException(status_code=404, detail="批次不存在")

        completed = sum(1 for t in tasks if t["status"] == "completed")
        failed = sum(1 for t in tasks if t["status"] == "failed")
        cancelled = sum(1 for t in tasks if t["status"] in ("cancelled", "stopped"))
        processing = sum(1 for t in tasks if t["status"] in ("pending", "running"))

        progress = (completed / len(tasks) * 100) if tasks else 0
        overall_status = "completed"
        if processing > 0:
            overall_status = "processing"
        elif failed > 0 and completed > 0:
            overall_status = "partial_success"
        elif failed == len(tasks):
            overall_status = "failed"

        return ok(
            {
                "batch_id": batch_id,
                "title": tasks[0].get("batch_name", ""),
                "status": overall_status,
                "total_tasks": len(tasks),
                "completed_tasks": completed,
                "failed_tasks": failed,
                "cancelled_tasks": cancelled,
                "progress": progress,
                "created_at": _fmt_dt(tasks[0].get("created_at")),
                "completed_at": _fmt_dt(
                    max(
                        (t.get("completed_at") for t in tasks if t.get("completed_at")),
                        default=None,
                    )
                ),
            }
        )

    # 使用 batch_manager 数据
    total = batch_status["total_count"]
    running = batch_status["running_count"]
    created = batch_status["created_count"]
    completed_approx = created - running

    return ok(
        {
            "batch_id": batch_id,
            "title": "",
            "status": "processing" if running > 0 else "completed",
            "total_tasks": total,
            "completed_tasks": max(0, completed_approx),
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "progress": (completed_approx / total * 100) if total else 100,
            "created_at": None,
            "completed_at": None,
        }
    )


# ----- 僵尸任务 -----
@router.get("/admin/zombie-tasks")
async def get_zombie_tasks(
    max_running_hours: float = Query(2, ge=0.5),
    admin_user: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取僵尸任务列表"""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_running_hours)
    query = {
        "status": {"$in": ["running", "pending"]},
        "created_at": {"$lt": cutoff},
    }
    cursor = mongodb.database.analysis_tasks.find(query).sort("created_at", 1)
    tasks = []
    async for doc in cursor:
        started = doc.get("started_at") or doc.get("created_at")
        elapsed = (
            (datetime.now(timezone.utc) - started).total_seconds() / 3600
            if started
            else max_running_hours
        )
        tasks.append(
            {
                "task_id": str(doc["_id"]),
                "symbol": doc.get("stock_code", ""),
                "status": doc["status"],
                "progress": doc.get("progress", 0.0),
                "created_at": _fmt_dt(doc.get("created_at")),
                "started_at": _fmt_dt(doc.get("started_at")),
                "elapsed_hours": round(elapsed, 2),
            }
        )

    return ok(
        {
            "tasks": tasks,
            "total": len(tasks),
            "max_running_hours": max_running_hours,
        }
    )


# ----- 清理僵尸任务 -----
@router.post("/admin/cleanup-zombie-tasks")
async def cleanup_zombie_tasks(
    max_running_hours: float = Query(2, ge=0.5),
    admin_user: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """清理僵尸任务"""
    from datetime import timedelta

    task_manager = get_task_manager()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_running_hours)
    query = {
        "status": {"$in": ["running", "pending"]},
        "created_at": {"$lt": cutoff},
    }

    cursor = mongodb.database.analysis_tasks.find(query)
    count = 0
    async for doc in cursor:
        task_id = str(doc["_id"])
        await task_manager.fail_task(
            task_id,
            f"僵尸任务清理（运行超过 {max_running_hours} 小时）",
        )
        count += 1

    return ok({"total_cleaned": count, "message": f"已清理 {count} 个僵尸任务"})


# =============================================================================
# SSE 流端点
# =============================================================================


@stream_router.get("/stream/tasks/{task_id}")
async def stream_task_progress(
    task_id: str,
    token: Optional[str] = Query(None),
    ticket: Optional[str] = Query(None),
    current_user: UserModel = Depends(get_current_user_from_query),
) -> StreamingResponse:
    """SSE 流：单任务进度"""
    task_manager = get_task_manager()

    try:
        info = await task_manager.get_task_status(task_id)
        if info["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权访问此任务")
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise

    async def event_stream() -> Any:  # type: ignore[misc]
        while True:
            try:
                state = await task_manager.get_task_status(task_id)
                status_val = state.get("status", "")

                if status_val in (
                    "completed",
                    "failed",
                    "cancelled",
                    "stopped",
                    "expired",
                ):
                    yield _sse(
                        "finished",
                        {
                            "task_id": task_id,
                            "status": _map_status(status_val),
                            "progress": state.get("progress", 0.0),
                            "final_status": _map_status(status_val),
                        },
                    )
                    break

                yield _sse(
                    "progress",
                    {
                        "task_id": task_id,
                        "status": _map_status(status_val),
                        "progress": state.get("progress", 0.0),
                        "current_step": _phase_label(state.get("current_phase", 0)),
                    },
                )
                await asyncio.sleep(1.0 if status_val == "running" else 3.0)

            except Exception as e:
                logger.error(f"SSE 流错误: task_id={task_id}, error={e}")
                yield _sse("error", {"error": str(e)})
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@stream_router.get("/stream/batches/{batch_id}")
async def stream_batch_progress(
    batch_id: str,
    token: Optional[str] = Query(None),
    ticket: Optional[str] = Query(None),
    current_user: UserModel = Depends(get_current_user_from_query),
) -> StreamingResponse:
    """SSE 流：批次进度"""
    user_id = str(current_user.id)

    async def event_stream() -> Any:  # type: ignore[misc]
        while True:
            try:
                # 查询该批次的任务状态
                tasks_cursor = mongodb.database.analysis_tasks.find(
                    {"batch_id": batch_id, "user_id": user_id}
                )
                tasks = await tasks_cursor.to_list(length=None)
                if not tasks:
                    yield _sse("error", {"error": "批次不存在"})
                    break

                total = len(tasks)
                completed = sum(1 for t in tasks if t["status"] == "completed")
                failed = sum(1 for t in tasks if t["status"] == "failed")
                processing = sum(1 for t in tasks if t["status"] in ("pending", "running"))
                progress = (completed / total * 100) if total else 100

                yield _sse(
                    "progress",
                    {
                        "batch_id": batch_id,
                        "progress": progress,
                        "total_tasks": total,
                        "completed": completed,
                        "failed": failed,
                        "processing": processing,
                    },
                )

                if processing == 0:
                    yield _sse(
                        "finished",
                        {
                            "batch_id": batch_id,
                            "progress": 100,
                            "total_tasks": total,
                            "completed": completed,
                            "failed": failed,
                            "processing": 0,
                            "final_status": ("completed" if failed == 0 else "partial_success"),
                        },
                    )
                    break

                await asyncio.sleep(2.0)

            except Exception as e:
                logger.error(f"SSE 批次流错误: batch_id={batch_id}, error={e}")
                yield _sse("error", {"error": str(e)})
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# 工具函数
# =============================================================================


def _sse(event: str, data: Any) -> str:
    """生成 SSE 事件字符串"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _map_status(status: str) -> str:
    """后端状态映射为前端状态"""
    mapping = {
        "pending": "pending",
        "running": "processing",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
        "stopped": "cancelled",
        "expired": "failed",
    }
    return mapping.get(status, status)


def _phase_label(phase: int) -> str:
    """阶段数字转文字"""
    labels = {
        0: "准备中",
        1: "信息收集与基础分析",
        2: "多空博弈与投资决策",
        3: "策略风格与风险评估",
        4: "总结报告生成",
    }
    return labels.get(phase, f"阶段 {phase}")


def _fmt_dt(dt: Any) -> Optional[str]:
    """格式化 datetime"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(dt)


def _extract_confidence_score(final_report: str, info: Dict[str, Any]) -> int:
    """从最终报告或任务数据中提取置信度分数（0-100）"""
    explicit = info.get("confidence_score")
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass

    if not final_report:
        return 0

    import re

    patterns = [
        r"置信度[：:]\s*(\d+)",
        r"confidence[：:]\s*(\d+)",
        r"信心指数[：:]\s*(\d+)",
        r"(\d+)%\s*(?:置信|信心|把握)",
    ]
    for pattern in patterns:
        match = re.search(pattern, final_report, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            return min(score, 100) if score <= 100 else score // 10
    return 0


def _extract_risk_level(final_report: str) -> str:
    """从最终报告中提取风险等级"""
    import re

    if not final_report:
        return ""
    risk_patterns = [
        (r"风险等级[：:]\s*(高|中|低)", 1),
        (r"risk\s*level[：:]\s*(high|medium|low)", 1),
    ]
    for pattern, group in risk_patterns:
        match = re.search(pattern, final_report, re.IGNORECASE)
        if match:
            return match.group(group)
    if re.search(r"高风险", final_report):
        return "高"
    if re.search(r"低风险", final_report):
        return "低"
    if re.search(r"中风险|中等风险", final_report):
        return "中"
    return ""


def _extract_key_points(final_report: str) -> List[str]:
    """从最终报告中提取关键要点"""
    if not final_report:
        return []
    import re

    points: List[str] = []
    in_section = False
    for line in final_report.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^#+\s*(?:关键|要点|核心|总结|key\s*points)", stripped, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("#"):
                break
            if re.match(r"^[-*•]\s+", stripped):
                points.append(re.sub(r"^[-*•]\s+", "", stripped))
            elif re.match(r"^\d+[.、)\s]+", stripped):
                points.append(re.sub(r"^\d+[.、)\s]+", "", stripped))
            if len(points) >= 5:
                break
    return points


def _calc_execution_time(started_at: Any, completed_at: Any) -> int:
    """计算任务执行时间（秒）"""
    if not started_at or not completed_at:
        return 0
    try:
        if isinstance(started_at, datetime) and isinstance(completed_at, datetime):
            return int((completed_at - started_at).total_seconds())
    except (TypeError, AttributeError):
        pass
    return 0
