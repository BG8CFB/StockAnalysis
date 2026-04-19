"""
系统日志 API

提供日志文件列表、内容读取、导出、统计和删除功能。
"""

import logging
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system/system-logs", tags=["system-logs"])

# 日志目录
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


class LogReadRequest(BaseModel):
    """日志读取请求"""

    filename: str
    lines: Optional[int] = None
    level: Optional[str] = None
    keyword: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class LogExportRequest(BaseModel):
    """日志导出请求"""

    filenames: Optional[List[str]] = None
    level: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    format: Optional[str] = "txt"


def _safe_path(filename: str) -> Path:
    """安全拼接日志文件路径，防止路径遍历"""
    safe_name = Path(filename).name
    return LOGS_DIR / safe_name


def _parse_log_level(line: str) -> str:
    """从日志行提取级别"""
    line_upper = line.upper()
    for level in ("ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL"):
        if level in line_upper:
            return level
    return "UNKNOWN"


def _get_log_type(filename: str) -> str:
    """推断日志类型"""
    name_lower = filename.lower()
    if "error" in name_lower:
        return "error"
    if "access" in name_lower:
        return "access"
    if "slow" in name_lower:
        return "slow_query"
    return "application"


@router.get("/files")
async def list_log_files(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取日志文件列表"""
    if not LOGS_DIR.exists():
        return {"code": 0, "message": "success", "data": []}

    files: List[Dict[str, Any]] = []
    for entry in sorted(LOGS_DIR.iterdir(), key=lambda e: e.stat().st_mtime, reverse=True):
        if entry.is_file() and not entry.name.startswith("."):
            stat = entry.stat()
            files.append(
                {
                    "name": entry.name,
                    "path": str(entry),
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "type": _get_log_type(entry.name),
                }
            )

    return {"code": 0, "message": "success", "data": files}


@router.post("/read")
async def read_log_file(
    request: LogReadRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """读取日志文件内容"""
    file_path = _safe_path(request.filename)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志文件不存在")

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取文件失败: {e}",
        )

    all_lines = content.splitlines()

    # 应用 filters
    filtered: List[str] = all_lines
    if request.level:
        level_upper = request.level.upper()
        filtered = [line for line in filtered if level_upper in line.upper()]
    if request.keyword:
        filtered = [line for line in filtered if request.keyword in line]
    if request.start_time:
        filtered = [line for line in filtered if line >= request.start_time]
    if request.end_time:
        filtered = [line for line in filtered if line <= request.end_time]

    # 限制行数
    if request.lines and request.lines > 0:
        filtered = filtered[-request.lines :]

    # 统计各级别数量
    stats: Dict[str, int] = {}
    for line in filtered:
        level = _parse_log_level(line)
        stats[level] = stats.get(level, 0) + 1

    return {
        "code": 0,
        "message": "success",
        "data": {
            "filename": request.filename,
            "lines": filtered,
            "stats": stats,
        },
    }


@router.post("/export")
async def export_logs(
    request: LogExportRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> StreamingResponse:
    """导出日志文件"""
    if not LOGS_DIR.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志目录不存在")

    filenames = request.filenames or []
    if not filenames:
        # 导出所有日志文件
        filenames = [
            f.name for f in LOGS_DIR.iterdir() if f.is_file() and not f.name.startswith(".")
        ]

    if request.format == "zip":
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in filenames:
                fpath = _safe_path(fname)
                if fpath.exists():
                    zf.write(fpath, fname)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=logs_export.zip"},
        )
    else:
        # 合并为 txt
        all_content: List[str] = []
        for fname in filenames:
            fpath = _safe_path(fname)
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8", errors="replace")
                all_content.append(f"=== {fname} ===\n{content}")

        buf = BytesIO("\n\n".join(all_content).encode("utf-8"))
        return StreamingResponse(
            buf,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=logs_export.txt"},
        )


@router.get("/statistics")
async def get_log_statistics(
    days: int = Query(7, ge=1, le=90),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取日志统计"""
    if not LOGS_DIR.exists():
        return {
            "code": 0,
            "message": "success",
            "data": {
                "total_files": 0,
                "total_size_mb": 0,
                "error_files": 0,
                "recent_errors": [],
                "log_types": {},
            },
        }

    total_size = 0
    error_files = 0
    recent_errors: List[str] = []
    log_types: Dict[str, int] = {}

    for entry in LOGS_DIR.iterdir():
        if entry.is_file() and not entry.name.startswith("."):
            stat = entry.stat()
            total_size += stat.st_size
            log_type = _get_log_type(entry.name)
            log_types[log_type] = log_types.get(log_type, 0) + 1
            if "error" in entry.name.lower():
                error_files += 1
                try:
                    lines = entry.read_text(encoding="utf-8", errors="replace").splitlines()
                    for line in lines[-20:]:
                        if "ERROR" in line.upper():
                            recent_errors.append(line[:200])
                except Exception:
                    pass

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_files": len(log_types),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "error_files": error_files,
            "recent_errors": recent_errors[:50],
            "log_types": log_types,
        },
    }


@router.delete("/files/{filename}")
async def delete_log_file(
    filename: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """删除日志文件"""
    file_path = _safe_path(filename)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志文件不存在")
    if LOGS_DIR not in file_path.parents and file_path.parent != LOGS_DIR:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法路径")

    try:
        file_path.unlink()
        logger.info(f"管理员 {current_admin.username} 删除了日志文件: {filename}")
        return {"code": 0, "message": "success", "data": {}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文件失败: {e}",
        )
