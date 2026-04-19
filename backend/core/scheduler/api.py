"""
定时任务调度器管理 API

提供 APScheduler 任务的管理、监控和手动操作接口。
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def _get_scheduler() -> Any:
    """获取 APScheduler 实例（延迟导入，避免循环依赖）"""
    from core.admin.tasks import get_scheduler

    sched = get_scheduler()
    if sched is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="调度器未启动（APScheduler 未安装或处于调试模式）",
        )
    return sched


def _get_data_scheduler() -> Any:
    """获取数据调度器实例"""
    from core.market_data.services.data_scheduler import get_data_scheduler

    return get_data_scheduler()


def _serialize_job(job: Any) -> Dict[str, Any]:
    """序列化 APScheduler Job 对象"""
    trigger_type = "cron"
    cron_expr = None
    if hasattr(job.trigger, "fields"):
        cron_expr = str(job.trigger)

    return {
        "id": job.id,
        "name": job.name,
        "display_name": job.name,
        "description": "",
        "enabled": job.next_run_time is not None,
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "trigger": {
            "type": trigger_type,
            "cron_expression": cron_expr,
        },
    }


# 存储执行记录的内存列表（简化实现，避免额外依赖）
_execution_records: List[Dict[str, Any]] = []
_execution_counter = 0


def _add_execution_record(
    job_id: str,
    exec_status: str,
    is_manual: bool = False,
    result: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """添加执行记录"""
    global _execution_counter
    _execution_counter += 1
    now = datetime.now(timezone.utc)
    record: Dict[str, Any] = {
        "id": f"exec_{_execution_counter}",
        "job_id": job_id,
        "status": exec_status,
        "started_at": now.isoformat(),
        "finished_at": now.isoformat() if exec_status != "running" else None,
        "duration_ms": 0,
        "is_manual": is_manual,
        "result": result,
        "error": error,
    }
    _execution_records.append(record)
    # 只保留最近 500 条
    if len(_execution_records) > 500:
        _execution_records[:] = _execution_records[-500:]
    return record


@router.get("/jobs")
async def list_scheduler_jobs(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取所有定时任务"""
    sched = _get_scheduler()
    jobs = [_serialize_job(j) for j in sched.get_jobs()]
    return {"code": 0, "message": "success", "data": jobs}


@router.get("/jobs/{job_id}")
async def get_job_detail(
    job_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取任务详情"""
    sched = _get_scheduler()
    job = sched.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return {"code": 0, "message": "success", "data": _serialize_job(job)}


@router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """暂停任务"""
    sched = _get_scheduler()
    job = sched.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    sched.pause_job(job_id)
    return {"code": 0, "message": "success", "data": {}}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """恢复任务"""
    sched = _get_scheduler()
    job = sched.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    sched.resume_job(job_id)
    return {"code": 0, "message": "success", "data": {}}


@router.post("/jobs/{job_id}/trigger")
async def trigger_job(
    job_id: str,
    force: bool = Query(False),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """手动触发任务"""
    sched = _get_scheduler()
    job = sched.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    try:
        sched.modify_job(job_id, next_run_time=datetime.now(timezone.utc))
        _add_execution_record(job_id, "success", is_manual=True, result="手动触发成功")
    except Exception as e:
        _add_execution_record(job_id, "failed", is_manual=True, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发任务失败: {e}",
        )
    return {"code": 0, "message": "success", "data": {}}


@router.get("/jobs/{job_id}/history")
async def get_job_history(
    job_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取任务执行历史"""
    records = [r for r in _execution_records if r["job_id"] == job_id]
    total = len(records)
    items = records[offset : offset + limit]
    return {
        "code": 0,
        "message": "success",
        "data": {
            "history": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/history")
async def get_all_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    job_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取所有执行历史"""
    records = _execution_records
    if job_id:
        records = [r for r in records if r["job_id"] == job_id]
    if status_filter:
        records = [r for r in records if r["status"] == status_filter]
    total = len(records)
    items = records[offset : offset + limit]
    return {
        "code": 0,
        "message": "success",
        "data": {
            "history": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/stats")
async def get_scheduler_stats(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取调度器统计"""
    sched = _get_scheduler()
    jobs = sched.get_jobs()
    active = sum(1 for j in jobs if j.next_run_time is not None)
    paused = len(jobs) - active
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_execs = [r for r in _execution_records if r["started_at"].startswith(today)]
    success_count = sum(1 for r in today_execs if r["status"] == "success")
    success_rate = (success_count / len(today_execs) * 100) if today_execs else 100.0
    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_jobs": len(jobs),
            "active_jobs": active,
            "paused_jobs": paused,
            "today_executions": len(today_execs),
            "success_rate": round(success_rate, 2),
        },
    }


@router.get("/health")
async def scheduler_health_check(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """调度器健康检查"""
    try:
        sched = _get_scheduler()
        running = sched.running
        jobs = sched.get_jobs()
        return {
            "code": 0,
            "message": "success",
            "data": {
                "status": "running" if running else "stopped",
                "running": running,
                "jobs_count": len(jobs),
            },
        }
    except HTTPException:
        return {
            "code": 0,
            "message": "success",
            "data": {
                "status": "unavailable",
                "running": False,
                "jobs_count": 0,
            },
        }


@router.get("/executions")
async def get_job_executions(
    job_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    is_manual: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取任务执行记录"""
    records = _execution_records
    if job_id:
        records = [r for r in records if r["job_id"] == job_id]
    if status_filter:
        records = [r for r in records if r["status"] == status_filter]
    if is_manual is not None:
        records = [r for r in records if r["is_manual"] == is_manual]
    total = len(records)
    items = records[offset : offset + limit]
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """取消执行"""
    for record in _execution_records:
        if record["id"] == execution_id:
            if record["status"] == "running":
                record["status"] = "failed"
                record["error"] = "用户取消"
                record["finished_at"] = datetime.now(timezone.utc).isoformat()
            return {"code": 0, "message": "success", "data": {}}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="执行记录不存在")


@router.post("/executions/{execution_id}/mark-failed")
async def mark_execution_failed(
    execution_id: str,
    reason: str = Query("用户手动标记"),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """标记执行为失败"""
    for record in _execution_records:
        if record["id"] == execution_id:
            record["status"] = "failed"
            record["error"] = reason
            record["finished_at"] = datetime.now(timezone.utc).isoformat()
            return {"code": 0, "message": "success", "data": {}}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="执行记录不存在")


@router.delete("/executions/{execution_id}")
async def delete_execution(
    execution_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """删除执行记录"""
    for i, record in enumerate(_execution_records):
        if record["id"] == execution_id:
            _execution_records.pop(i)
            return {"code": 0, "message": "success", "data": {}}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="执行记录不存在")
