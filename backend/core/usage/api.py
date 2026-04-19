"""
用量统计 API

提供 LLM Token 使用量统计、成本分析等接口。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from core.usage.service import (
    get_cost_by_model,
    get_cost_by_provider,
    get_daily_cost,
    get_statistics,
    get_usage_records,
)
from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/statistics")
async def usage_statistics(
    days: int = Query(7, ge=1, le=365),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取使用统计"""
    data = await get_statistics(days)
    return {"code": 0, "message": "success", "data": data}


@router.get("/cost/by-provider")
async def cost_by_provider(
    days: int = Query(7, ge=1, le=365),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取按供应商统计的成本"""
    data = await get_cost_by_provider(days)
    return {"code": 0, "message": "success", "data": data}


@router.get("/cost/by-model")
async def cost_by_model(
    days: int = Query(7, ge=1, le=365),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取按模型统计的成本"""
    data = await get_cost_by_model(days)
    return {"code": 0, "message": "success", "data": data}


@router.get("/cost/daily")
async def daily_cost(
    days: int = Query(30, ge=1, le=365),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取每日成本统计"""
    data = await get_daily_cost(days)
    return {"code": 0, "message": "success", "data": data}


@router.get("/records")
async def usage_records(
    provider: Optional[str] = Query(None),
    model_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取使用记录列表"""
    data = await get_usage_records(
        provider=provider,
        model_name=model_name,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"code": 0, "message": "success", "data": data}
