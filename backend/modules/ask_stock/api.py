"""
🔶 AI 问股模块 API 路由

此模块为占位模块，功能待实现。

计划功能：
- 自然语言股票问答
- 智能股票分析
- 历史数据查询
- 技术分析解读
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["AI 问股"])


class AskStockRequest(BaseModel):
    """AI 问股请求"""
    question: str
    symbol: str = None


@router.post("/ask")
async def ask_stock(request: AskStockRequest):
    """
    🔶 AI 股票问答

    TODO: 实现 AI 股票问答功能
    - 使用 LLM 理解用户问题
    - 调用市场数据工具获取相关信息
    - 生成自然语言回答
    - 支持多轮对话上下文
    """
    return {
        "answer": f"🔶 AI analysis for: {request.question}",
        "status": "pending_implementation"
    }


@router.post("/chat")
async def chat_with_stock():
    """
    🔶 股票多轮对话

    TODO: 实现股票多轮对话功能
    - 维护对话历史
    - 支持追问和上下文理解
    - 提供结构化分析结果
    """
    return {
        "message": "🔶 多轮对话功能待实现",
        "status": "pending_implementation"
    }
