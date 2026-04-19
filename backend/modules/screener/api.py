"""
智能选股模块 API 路由（占位模块）

此模块为占位模块，功能待实现。
返回 HTTP 501 Not Implemented，前端可据此展示"即将上线"提示。

计划功能：
- 基于技术指标的选股策略
- 基本面筛选策略
- 自定义选股条件
- 回测功能
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["智能选股"])


@router.get("/screener/strategies")
async def get_strategies() -> JSONResponse:
    """获取选股策略列表（未实现）"""
    return JSONResponse(
        status_code=501,
        content={
            "success": False,
            "message": "智能选股功能尚未实现",
            "data": {"strategies": []},
        },
    )


@router.post("/screener/run")
async def run_screener() -> JSONResponse:
    """执行选股策略（未实现）"""
    return JSONResponse(
        status_code=501,
        content={
            "success": False,
            "message": "智能选股功能尚未实现",
            "data": {"results": []},
        },
    )
