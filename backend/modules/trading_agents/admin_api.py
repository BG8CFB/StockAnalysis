"""
TradingAgents 管理员 API

提供管理员专用的系统管理接口。
"""
import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from bson import ObjectId

from core.auth.dependencies import get_current_user
from core.user.models import UserModel
from core.auth.rbac import Role, Permission, require_role, require_permission
from core.ai.model import get_model_service
from modules.trading_agents.manager.task_manager import get_task_manager
from modules.trading_agents.manager.batch_manager import get_batch_manager
from modules.trading_agents.manager.alerts import get_alert_manager, AlertEventType, AlertSeverity

logger = logging.getLogger(__name__)


# =============================================================================
# AI 模型管理
# =============================================================================

router = APIRouter(prefix="/admin/trading-agents", tags=["TradingAgents-Admin"])


# =============================================================================
# 依赖项
# =============================================================================

async def get_admin_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """验证管理员权限"""
    if current_user.role not in [Role.ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# =============================================================================
# AI 模型管理
# =============================================================================

@router.get("/models")
async def list_all_models(
    admin_user: UserModel = Depends(get_admin_user),
    include_disabled: bool = Query(False, description="是否包含已禁用的模型"),
):
    """
    获取所有 AI 模型配置（管理员）

    包括系统级模型和用户自定义模型。
    """
    model_service = get_model_service()
    result = await model_service.list_models(
        user_id=admin_user.id,
        is_admin=True,
        include_system=True
    )

    # 统计信息
    all_models = result.get("system", []) + result.get("user", [])
    if not include_disabled:
        all_models = [m for m in all_models if m.enabled]

    return {
        "total": len(all_models),
        "system": result["system"],
        "user": result["user"],
    }


@router.post("/models")
async def create_system_model(
    name: str = Query(..., description="模型名称"),
    provider: str = Query(..., description="提供商类型"),
    api_base_url: str = Query(..., description="API 地址"),
    api_key: str = Query(..., description="API 密钥"),
    model_id: str = Query(..., description="模型 ID"),
    max_concurrency: int = Query(5, description="最大并发数"),
    timeout_seconds: int = Query(60, description="超时时间（秒）"),
    temperature: float = Query(0.5, description="默认温度"),
    admin_user: UserModel = Depends(get_admin_user),
):
    """
    创建系统级 AI 模型配置（管理员）

    创建对所有用户可用的系统级模型。
    """
    from core.ai.model.schemas import AIModelConfigCreate, ModelProviderEnum

    model_service = get_model_service()

    # 尝试解析提供商类型
    try:
        provider_enum = ModelProviderEnum(provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的提供商类型: {provider}"
        )

    request = AIModelConfigCreate(
        name=name,
        provider=provider_enum,
        api_base_url=api_base_url,
        api_key=api_key,
        model_id=model_id,
        max_concurrency=max_concurrency,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        enabled=True,
        is_system=True,
    )

    model = await model_service.create_model(user_id=str(admin_user.id), request=request)

    logger.info(f"管理员创建系统模型: name={name}, admin={admin_user.username}")

    return model


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    admin_user: UserModel = Depends(get_admin_user),
):
    """删除 AI 模型配置（管理员）"""
    model_service = get_model_service()
    success = await model_service.delete_model(
        model_id=model_id,
        user_id=str(admin_user.id),
        is_admin=True
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在或无权删除"
        )

    logger.info(f"管理员删除模型: model_id={model_id}, admin={admin_user.username}")

    return {"success": True, "message": "模型已删除"}


# =============================================================================
# MCP 服务器管理端点已迁移到 core/mcp/api/routes.py
# =============================================================================

# =============================================================================
# 任务管理
# =============================================================================

@router.get("/tasks")
async def list_all_tasks(
    admin_user: UserModel = Depends(get_admin_user),
    status_filter: Optional[str] = Query(None, description="状态过滤"),
    user_filter: Optional[str] = Query(None, description="用户 ID 过滤"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    获取所有任务（管理员）
    """
    from core.db.mongodb import mongodb

    task_manager = get_task_manager()
    batch_manager = get_batch_manager()

    # 构建查询条件
    query = {}
    if status_filter:
        query["status"] = status_filter
    if user_filter:
        query["user_id"] = user_filter

    collection = mongodb.database.analysis_tasks

    # 获取总数
    total = await collection.count_documents(query)

    # 获取任务列表
    cursor = collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
    tasks = []
    async for doc in cursor:
        tasks.append({
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "stock_code": doc.get("stock_code"),
            "trade_date": doc.get("trade_date"),
            "status": doc["status"],
            "created_at": doc["created_at"],
            "started_at": doc.get("started_at"),
            "completed_at": doc.get("completed_at"),
            "final_recommendation": doc.get("final_recommendation"),
            "token_usage": doc.get("token_usage"),
        })

    # 获取运行中的公共模型任务数
    public_running = await batch_manager.get_public_model_running_count()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "public_model_running": public_running,
        "tasks": tasks,
    }


@router.get("/tasks/stats")
async def get_task_statistics(
    admin_user: UserModel = Depends(get_admin_user),
):
    """
    获取任务统计信息（管理员）
    """
    from core.db.mongodb import mongodb
    from datetime import datetime, timedelta, timezone

    task_manager = get_task_manager()

    collection = mongodb.database.analysis_tasks

    # 按状态统计
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_stats = {}
    async for doc in collection.aggregate(pipeline):
        status_stats[doc["_id"]] = doc["count"]

    # 总任务数
    total_tasks = await collection.count_documents({})

    # 今日任务数
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_tasks = await collection.count_documents({
        "created_at": {"$gte": today_start}
    })

    # 运行中任务数
    running_tasks = await task_manager.get_running_tasks_count()

    return {
        "total": total_tasks,
        "today": today_tasks,
        "running": running_tasks,
        "by_status": status_stats,
    }


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    admin_user: UserModel = Depends(get_admin_user),
):
    """删除任务（管理员）"""
    from core.db.mongodb import mongodb
    from bson import ObjectId

    # 检查任务是否存在
    task_doc = await mongodb.database.analysis_tasks.find_one({"_id": ObjectId(task_id)})
    if not task_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 删除任务
    await mongodb.database.analysis_tasks.delete_one({"_id": ObjectId(task_id)})

    logger.info(f"管理员删除任务: task_id={task_id}, admin={admin_user.username}")

    return {"success": True, "message": "任务已删除"}


# =============================================================================
# 报告管理
# =============================================================================

@router.get("/reports")
async def list_all_reports(
    admin_user: UserModel = Depends(get_admin_user),
    user_filter: Optional[str] = Query(None),
    stock_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    获取所有分析报告（管理员）
    """
    from core.db.mongodb import mongodb

    # 构建查询条件
    query = {}
    if user_filter:
        query["user_id"] = user_filter
    if stock_filter:
        query["stock_code"] = stock_filter

    collection = mongodb.database.analysis_reports

    # 获取总数
    total = await collection.count_documents(query)

    # 获取报告列表
    cursor = collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
    reports = []
    async for doc in cursor:
        reports.append({
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "task_id": doc.get("task_id"),
            "stock_code": doc["stock_code"],
            "trade_date": doc.get("trade_date"),
            "recommendation": doc.get("recommendation"),
            "risk_level": doc.get("risk_level"),
            "created_at": doc["created_at"],
            "token_usage": doc.get("token_usage"),
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "reports": reports,
    }


@router.get("/reports/stats")
async def get_report_statistics(
    admin_user: UserModel = Depends(get_admin_user),
):
    """
    获取报告统计信息（管理员）
    """
    from core.db.mongodb import mongodb

    collection = mongodb.database.analysis_reports

    # 按推荐类型统计
    pipeline = [
        {"$group": {"_id": "$recommendation", "count": {"$sum": 1}}}
    ]
    recommendation_stats = {}
    async for doc in collection.aggregate(pipeline):
        recommendation_stats[doc["_id"]] = doc["count"]

    # 按风险等级统计
    pipeline = [
        {"$group": {"_id": "$risk_level", "count": {"$sum": 1}}}
    ]
    risk_stats = {}
    async for doc in collection.aggregate(pipeline):
        risk_stats[doc["_id"]] = doc["count"]

    # 总报告数
    total_reports = await collection.count_documents({})

    # Token 总消耗
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$token_usage.total_tokens"}}}
    ]
    total_tokens = 0
    async for doc in collection.aggregate(pipeline):
        total_tokens = doc.get("total", 0)

    return {
        "total": total_reports,
        "total_tokens": total_tokens,
        "by_recommendation": recommendation_stats,
        "by_risk": risk_stats,
    }


# =============================================================================
# 告警管理
# =============================================================================

@router.get("/alerts")
async def list_all_alerts(
    admin_user: UserModel = Depends(get_admin_user),
    severity_filter: Optional[str] = Query(None),
    type_filter: Optional[str] = Query(None),
    unresolved_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    获取所有告警（管理员）
    """
    alert_manager = get_alert_manager()

    # 构建查询条件
    query = {}
    if severity_filter:
        query["severity"] = severity_filter
    if type_filter:
        query["event_type"] = type_filter
    if unresolved_only:
        query["resolved"] = False

    # 直接查询 MongoDB
    from core.db.mongodb import mongodb
    alerts_collection = mongodb.database.alerts

    # 获取总数
    total = await alerts_collection.count_documents(query)

    # 获取告警列表
    cursor = alerts_collection.find(query).sort("timestamp", -1).skip(offset).limit(limit)
    alerts = []
    async for doc in cursor:
        alerts.append({
            "id": str(doc["_id"]),
            "event_type": doc["event_type"],
            "severity": doc["severity"],
            "title": doc["title"],
            "description": doc["description"],
            "user_id": doc.get("user_id"),
            "task_id": doc.get("task_id"),
            "timestamp": doc["timestamp"],
            "resolved": doc["resolved"],
            "resolved_at": doc.get("resolved_at"),
            "metadata": doc.get("metadata", {}),
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "alerts": alerts,
    }


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    admin_user: UserModel = Depends(get_admin_user),
):
    """
    解决告警（管理员）
    """
    alert_manager = get_alert_manager()
    success = await alert_manager.resolve_alert(alert_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警不存在"
        )

    logger.info(f"管理员解决告警: alert_id={alert_id}, admin={admin_user.username}")

    return {"success": True, "message": "告警已解决"}


@router.get("/alerts/stats")
async def get_alerts_stats(
    admin_user: UserModel = Depends(get_admin_user),
):
    """
    获取告警统计信息（管理员）
    """
    from core.db.mongodb import mongodb
    from datetime import datetime, timedelta, timezone

    alerts_collection = mongodb.database.alerts

    # 总告警数
    total = await alerts_collection.count_documents({})

    # 未解决告警数
    unresolved = await alerts_collection.count_documents({"resolved": False})

    # 严重告警数
    critical = await alerts_collection.count_documents({"severity": "critical", "resolved": False})

    # 今日新增告警数
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today = await alerts_collection.count_documents({"timestamp": {"$gte": today_start}})

    # 按严重程度统计
    severity_stats = {}
    pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    async for doc in alerts_collection.aggregate(pipeline):
        severity_stats[doc["_id"]] = doc["count"]

    # 按事件类型统计
    type_stats = {}
    pipeline = [
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    async for doc in alerts_collection.aggregate(pipeline):
        type_stats[doc["_id"]] = doc["count"]

    return {
        "total": total,
        "unresolved": unresolved,
        "critical": critical,
        "today": today,
        "by_severity": severity_stats,
        "by_type": type_stats,
    }


# =============================================================================
# 智能体配置管理
# =============================================================================

@router.post("/agent-config/public/restore")
async def restore_public_config(
    current_admin: UserModel = Depends(get_admin_user),
):
    """
    恢复公共智能体配置为默认值

    从YAML文件重新导入，用于配置被改乱后的恢复。
    YAML文件作为系统出厂设置备份，只在系统启动时和恢复时使用。

    Returns:
        恢复后的公共配置
    """
    from modules.trading_agents.manager.agent_config_service import get_agent_config_service

    service = get_agent_config_service()
    config = await service.restore_public_config()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="恢复默认配置失败"
        )

    logger.info(f"管理员恢复公共配置为默认值: admin={current_admin.username}")

    return {
        "success": True,
        "message": "公共配置已恢复为默认值",
        "config": config
    }
