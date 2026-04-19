"""
AI 问股模块 API 路由（占位模块）

此模块为占位模块，功能待实现。
返回 HTTP 501 Not Implemented，前端可据此展示"即将上线"提示。

计划功能：
- 自然语言股票问答
- 智能股票分析
- 历史数据查询
- 技术分析解读
"""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(tags=["AI 问股"])


class AskStockRequest(BaseModel):
    """AI 问股请求"""

    question: str
    symbol: Optional[str] = None


@router.post("/ask")
async def ask_stock(request: AskStockRequest) -> JSONResponse:
    """AI 股票问答（未实现）"""
    return JSONResponse(
        status_code=501,
        content={
            "success": False,
            "message": "AI 问股功能尚未实现",
            "data": None,
        },
    )


@router.post("/chat")
async def chat_with_stock() -> JSONResponse:
    """股票多轮对话（未实现）"""
    return JSONResponse(
        status_code=501,
        content={
            "success": False,
            "message": "AI 多轮对话功能尚未实现",
            "data": None,
        },
    )
