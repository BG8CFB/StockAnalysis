"""
筛选 API 路由

6 个端点：
- GET  /screening/fields           获取筛选字段配置
- GET  /screening/fields/{field_name}  获取指定字段详情
- POST /screening/run              传统筛选
- POST /screening/enhanced         增强筛选
- POST /screening/validate         验证筛选条件
- GET  /screening/industries       获取行业列表
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth.dependencies import get_current_active_user
from core.auth.models import UserModel
from core.screening.service import ScreeningService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screening", tags=["screening"])

_service = ScreeningService()


@router.get("/fields")
async def get_screening_fields(
    user: UserModel = Depends(get_current_active_user),
):
    """获取所有可用的筛选字段配置"""
    config = await _service.get_fields_config()
    return {"success": True, "data": config}


@router.get("/fields/{field_name}")
async def get_screening_field_info(
    field_name: str,
    user: UserModel = Depends(get_current_active_user),
):
    """获取指定字段的详细信息"""
    detail = await _service.get_field_detail(field_name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"字段不存在: {field_name}")
    return {"success": True, "data": detail}


@router.post("/run")
async def run_screening(
    body: dict[str, Any],
    user: UserModel = Depends(get_current_active_user),
):
    """
    运行传统筛选

    body 结构:
    {
        "market": "A_STOCK",
        "conditions": {
            "logic": "AND",
            "children": [
                {"field": "pe_ttm", "op": "between", "value": [5, 30]},
                {"field": "roe", "op": "gt", "value": 10}
            ]
        },
        "order_by": [{"field": "roe", "direction": "desc"}],
        "limit": 50,
        "offset": 0
    }
    """
    conditions_raw = body.get("conditions", {})
    logic = conditions_raw.get("logic", "AND") if isinstance(conditions_raw, dict) else "AND"
    children = conditions_raw.get("children", []) if isinstance(conditions_raw, dict) else []

    result = await _service.run_screening(
        conditions=children,
        logic=logic,
        market=body.get("market"),
        order_by=body.get("order_by"),
        limit=body.get("limit", 50),
        offset=body.get("offset", 0),
    )
    return {"success": True, "data": result}


@router.post("/enhanced")
async def run_enhanced_screening(
    body: dict[str, Any],
    user: UserModel = Depends(get_current_active_user),
):
    """
    运行增强筛选（多条件）

    body 结构:
    {
        "conditions": [
            {"field": "pe_ttm", "operator": "between", "value": [5, 30]},
            {"field": "roe", "operator": "gt", "value": 10}
        ],
        "market": "A_STOCK",
        "order_by": [{"field": "roe", "direction": "desc"}],
        "limit": 50,
        "offset": 0
    }
    """
    conditions = body.get("conditions", [])
    if not conditions:
        raise HTTPException(status_code=400, detail="至少需要一个筛选条件")

    result = await _service.run_enhanced_screening(
        conditions=conditions,
        market=body.get("market"),
        order_by=body.get("order_by"),
        limit=body.get("limit", 50),
        offset=body.get("offset", 0),
    )
    return {"success": True, "data": result}


@router.post("/validate")
async def validate_screening_conditions(
    body: list[dict[str, Any]],
    user: UserModel = Depends(get_current_active_user),
):
    """验证筛选条件是否合法"""
    result = await _service.validate_conditions(body)
    return {"success": True, "data": result}


@router.get("/industries")
async def get_industries(
    user: UserModel = Depends(get_current_active_user),
):
    """获取行业列表（含股票数量统计）"""
    result = await _service.get_industries()
    return {"success": True, "data": result}
