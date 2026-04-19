"""
报告适配路由

将前端 /api/reports/* 请求适配到 trading_agents 模块的数据。
报告本质是已完成的 analysis_tasks，本路由提供列表、详情、
模块内容、删除、下载等端点。
"""

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from core.auth.dependencies import get_current_active_user
from core.db.mongodb import mongodb
from core.user.models import UserModel
from modules.trading_agents.schemas import (
    TaskStatusEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["报告管理"])

# 报告阶段模块名 → MongoDB reports 字段的映射
MODULE_KEY_MAP = {
    "data-collection": "phase1_data",
    "debate": "phase2_debate",
    "risk-assessment": "phase3_risk",
    "summary": "final_report",
}


def _format_report_item(task: Dict[str, Any]) -> Dict[str, Any]:
    """将 analysis_tasks 文档格式化为前端 ReportItem 结构"""
    reports = task.get("reports") or {}
    final_report = reports.get("final_report") or ""
    task.get("token_usage") or {}

    created_at = task.get("created_at")
    completed_at = task.get("completed_at")
    created_at_str = _to_iso(created_at) if created_at else ""
    _completed_at_str = _to_iso(completed_at) if completed_at else ""

    # 从阶段配置中提取分析师列表
    stages = task.get("stages") or {}
    stage1 = stages.get("stage1") or {}
    analysts = stage1.get("selected_agents") or []

    return {
        "id": str(task["_id"]),
        "analysis_id": str(task["_id"]),
        "title": f"{task.get('stock_code', '')} 分析报告",
        "stock_code": task.get("stock_code", ""),
        "stock_name": task.get("stock_code", ""),
        "market_type": task.get("market", "A_STOCK"),
        "model_info": task.get("debate_model") or task.get("data_collection_model") or "",
        "type": "full_analysis",
        "format": "markdown",
        "status": task.get("status", "completed"),
        "created_at": created_at_str,
        "analysis_date": task.get("trade_date", ""),
        "analysts": analysts,
        "research_depth": 4,
        "summary": final_report[:200] if final_report else "",
        "file_size": len(final_report) if final_report else 0,
        "source": "trading_agents",
        "task_id": str(task["_id"]),
    }


def _format_report_detail(task: Dict[str, Any]) -> Dict[str, Any]:
    """将 analysis_tasks 文档格式化为前端 ReportDetail 结构"""
    reports = task.get("reports") or {}
    final_report = reports.get("final_report") or ""
    token_usage = task.get("token_usage") or {}
    total_tokens = token_usage.get("total_tokens", 0)

    created_at = task.get("created_at")
    completed_at = task.get("completed_at")
    started_at = task.get("started_at")
    created_at_str = _to_iso(created_at) if created_at else ""
    completed_at_str = _to_iso(completed_at) if completed_at else ""

    # 计算执行时间（秒）
    execution_time = 0
    if started_at and completed_at:
        try:
            execution_time = int((completed_at - started_at).total_seconds())
        except (TypeError, AttributeError):
            pass

    # 从阶段配置中提取分析师列表
    stages = task.get("stages") or {}
    stage1 = stages.get("stage1") or {}
    analysts = stage1.get("selected_agents") or []

    # 从最终报告中提取置信度、风险等级、关键要点
    confidence_score = _extract_confidence_score(final_report, task)
    risk_level = task.get("risk_level") or _extract_risk_level(final_report)
    key_points = _extract_key_points(final_report)

    # 从报告中提取投资决策信息
    decision = _extract_decision(reports, task)

    return {
        "id": str(task["_id"]),
        "analysis_id": str(task["_id"]),
        "stock_symbol": task.get("stock_code", ""),
        "stock_name": task.get("stock_code", ""),
        "model_info": task.get("debate_model") or task.get("data_collection_model") or "",
        "analysis_date": task.get("trade_date", ""),
        "status": task.get("status", "completed"),
        "created_at": created_at_str,
        "updated_at": completed_at_str,
        "analysts": analysts,
        "research_depth": 4,
        "summary": final_report[:200] if final_report else "",
        "reports": reports,
        "source": "trading_agents",
        "task_id": str(task["_id"]),
        "recommendation": task.get("final_recommendation") or "",
        "confidence_score": confidence_score,
        "risk_level": risk_level,
        "key_points": key_points,
        "execution_time": execution_time,
        "tokens_used": total_tokens,
        "decision": decision,
    }


def _to_iso(dt: Any) -> str:
    """将 datetime 序列化为 ISO 格式字符串"""
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(dt)


# =============================================================================
# 端点实现
# =============================================================================


@router.get("/list")
async def list_reports(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(
        None, alias="keyword", description="搜索关键词（股票代码/名称）"
    ),
    search_keyword: Optional[str] = Query(
        None, alias="search_keyword", description="搜索关键词（兼容前端旧参数名）"
    ),
    market: Optional[str] = Query(
        None, alias="market", description="市场过滤: A_STOCK/US_STOCK/HK_STOCK"
    ),
    market_filter: Optional[str] = Query(
        None, alias="market_filter", description="市场过滤（兼容前端旧参数名）"
    ),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    获取报告列表（已完成的任务）

    前端使用分页接口，返回 ReportListResponse 结构。
    支持 keyword/search_keyword 和 market/market_filter 两组参数名。
    """
    # 兼容旧参数名：优先使用新参数，旧参数作为回退
    effective_keyword = keyword or search_keyword
    effective_market = market or market_filter
    user_id = str(current_user.id)

    # 构建查询条件：只查已完成的任务
    query: Dict[str, Any] = {
        "user_id": user_id,
        "status": TaskStatusEnum.COMPLETED.value,
    }

    # 市场过滤
    if effective_market:
        query["market"] = effective_market

    # 关键词搜索（模糊匹配股票代码）
    if effective_keyword:
        query["stock_code"] = {"$regex": effective_keyword, "$options": "i"}

    # 日期范围过滤
    if start_date or end_date:
        date_filter: Dict[str, str] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["trade_date"] = date_filter

    # 计算偏移量
    skip = (page - 1) * page_size

    # 并行执行查询和计数
    collection = mongodb.database.analysis_tasks
    cursor = collection.find(query).sort("completed_at", -1).skip(skip).limit(page_size)
    total = await collection.count_documents(query)

    tasks: List[Dict[str, Any]] = []
    async for doc in cursor:
        tasks.append(doc)

    reports = [_format_report_item(t) for t in tasks]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return {
        "success": True,
        "data": {
            "reports": reports,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        "message": "获取报告列表成功",
    }


@router.get("/{report_id}/detail")
async def get_report_detail(
    report_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取报告详情"""
    user_id = str(current_user.id)

    try:
        task = await mongodb.database.analysis_tasks.find_one(
            {"_id": ObjectId(report_id), "user_id": user_id}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    if not task:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 允许查看任何状态的任务详情（不限于 completed）
    detail = _format_report_detail(task)

    return {
        "success": True,
        "data": detail,
        "message": "获取报告详情成功",
    }


@router.get("/{report_id}/content/{module}")
async def get_report_module_content(
    report_id: str,
    module: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取报告特定模块/阶段的内容"""
    user_id = str(current_user.id)

    # 验证模块名
    content_key = MODULE_KEY_MAP.get(module)
    if not content_key:
        valid_modules = list(MODULE_KEY_MAP.keys())
        raise HTTPException(
            status_code=400,
            detail=f"无效的模块名: {module}，可选: {', '.join(valid_modules)}",
        )

    try:
        task = await mongodb.database.analysis_tasks.find_one(
            {"_id": ObjectId(report_id), "user_id": user_id}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    if not task:
        raise HTTPException(status_code=404, detail="报告不存在")

    reports = task.get("reports") or {}
    content = reports.get(content_key, "")

    return {
        "success": True,
        "data": {
            "module": module,
            "content": content or "",
            "report_id": report_id,
        },
        "message": "获取模块内容成功",
    }


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除报告（已完成的任务）"""
    user_id = str(current_user.id)

    try:
        task = await mongodb.database.analysis_tasks.find_one(
            {"_id": ObjectId(report_id), "user_id": user_id}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    if not task:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 不允许删除运行中的任务
    if task.get("status") == TaskStatusEnum.RUNNING.value:
        raise HTTPException(status_code=400, detail="运行中的任务不能删除，请先取消任务")

    # 删除任务记录
    await mongodb.database.analysis_tasks.delete_one({"_id": ObjectId(report_id)})

    # 删除关联的分析报告
    await mongodb.database.analysis_reports.delete_many({"task_id": report_id})

    return {
        "success": True,
        "message": "报告已删除",
    }


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = Query("json", description="导出格式: json/markdown"),
    current_user: UserModel = Depends(get_current_active_user),
) -> JSONResponse:
    """下载报告（JSON 格式导出）"""
    user_id = str(current_user.id)

    try:
        task = await mongodb.database.analysis_tasks.find_one(
            {"_id": ObjectId(report_id), "user_id": user_id}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="无效的报告 ID")

    if not task:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 准备导出数据
    export_data = _format_report_detail(task)
    export_data["export_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if format == "markdown":
        # Markdown 格式：组合各阶段报告
        reports = task.get("reports") or {}
        parts = [
            f"# {export_data['stock_symbol']} 分析报告",
            f"\n**分析日期**: {export_data['analysis_date']}",
            f"**推荐**: {export_data['recommendation']}",
            f"**风险等级**: {export_data['risk_level']}",
        ]

        final = reports.get("final_report", "")
        if final:
            parts.append(f"\n---\n\n## 最终报告\n\n{final}")

        for key, label in [
            ("phase1_data", "数据收集"),
            ("phase2_debate", "多空辩论"),
            ("phase3_risk", "风险评估"),
        ]:
            content = reports.get(key, "")
            if content:
                parts.append(f"\n---\n\n## {label}\n\n{content}")

        md_content = "\n".join(parts)
        stock_code = export_data.get("stock_symbol", "report")
        filename = f"{stock_code}_{export_data['analysis_date']}_report.md"

        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "content": md_content,
                    "filename": filename,
                    "format": "markdown",
                },
                "message": "下载成功",
            }
        )

    # 默认 JSON 格式
    stock_code = export_data.get("stock_symbol", "report")
    filename = f"{stock_code}_{export_data['analysis_date']}_report.json"
    export_data["filename"] = filename

    return JSONResponse(
        content={
            "success": True,
            "data": export_data,
            "message": "下载成功",
        }
    )


# =============================================================================
# 数据提取辅助函数
# =============================================================================


def _extract_confidence_score(final_report: str, task: Dict[str, Any]) -> int:
    """从最终报告或任务数据中提取置信度分数（0-100）"""
    explicit = task.get("confidence_score")
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    if not final_report:
        return 0
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
    if not final_report:
        return ""
    if re.search(r"高风险", final_report):
        return "高"
    if re.search(r"低风险", final_report):
        return "低"
    if re.search(r"中风险|中等风险", final_report):
        return "中"
    match = re.search(r"风险等级[：:]\s*(高|中|低)", final_report)
    if match:
        return match.group(1)
    return ""


def _extract_key_points(final_report: str) -> List[str]:
    """从最终报告中提取关键要点"""
    if not final_report:
        return []
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


def _extract_decision(reports: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """从报告数据中提取投资决策信息"""
    decision: Dict[str, Any] = {}

    recommendation = task.get("final_recommendation")
    if recommendation:
        decision["recommendation"] = recommendation

    # 从 Phase 2 报告中提取交易计划
    phase2 = reports.get("phase2_debate") or ""
    if phase2:
        # 尝试提取目标价格
        price_match = re.search(r"目标价[格]?[：:]\s*([\d.]+)", phase2)
        if price_match:
            decision["target_price"] = float(price_match.group(1))
        # 尝试提取止损价
        stop_match = re.search(r"止损[价]?[：:]\s*([\d.]+)", phase2)
        if stop_match:
            decision["stop_loss"] = float(stop_match.group(1))

    # 从 Phase 3 报告中提取风险建议
    phase3 = reports.get("phase3_risk") or ""
    if phase3:
        risk_match = re.search(r"(?:风险等级|综合风险)[：:]\s*(高|中|低)", phase3)
        if risk_match:
            decision["risk_assessment"] = risk_match.group(1)

    return decision
