"""
报告相关数据模型

包含报告查询、响应等模型。
"""

from datetime import datetime
from typing import Dict, Any, Optional

from pydantic import BaseModel

from .common import RecommendationEnum, RiskLevelEnum, MessageResponse


# =============================================================================
# 报告模型
# =============================================================================

class AnalysisReportResponse(BaseModel):
    """分析报告响应"""
    id: str
    task_id: str
    user_id: str
    stock_code: str
    trade_date: str
    report_type: str
    report_content: str
    recommendation: Optional[RecommendationEnum]
    buy_price: Optional[float]
    sell_price: Optional[float]
    token_usage: Dict[str, int]
    created_at: datetime

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "AnalysisReportResponse":
        """从数据库数据创建响应对象"""
        return cls(
            id=str(data["_id"]),
            task_id=data["task_id"],
            user_id=data["user_id"],
            stock_code=data["stock_code"],
            trade_date=data["trade_date"],
            report_type=data["report_type"],
            report_content=data["report_content"],
            recommendation=RecommendationEnum(data["recommendation"]) if data.get("recommendation") else None,
            buy_price=data.get("buy_price"),
            sell_price=data.get("sell_price"),
            token_usage=data.get("token_usage", {}),
            created_at=data["created_at"],
        )


class ReportSummaryResponse(BaseModel):
    """报告汇总统计响应"""
    total_reports: int
    buy_count: int
    sell_count: int
    hold_count: int
    avg_buy_price: Optional[float] = None
    avg_sell_price: Optional[float] = None
    recommendation_distribution: Dict[str, int] = {}
    total_token_usage: int = 0


__all__ = [
    "AnalysisReportResponse",
    "ReportSummaryResponse",
]
