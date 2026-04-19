"""
分析报告管理服务

提供报告的创建、查询、统计和归档功能。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.schemas import (
    RecommendationEnum,
    RiskLevelEnum,
)

logger = logging.getLogger(__name__)


class ReportService:
    """
    分析报告管理服务

    提供报告的 CRUD 操作、统计查询和导出功能。
    """

    # 集合名称
    TASKS_COLLECTION = "analysis_tasks"
    REPORTS_COLLECTION = "analysis_reports"
    ARCHIVED_COLLECTION = "archived_reports"

    def __init__(self) -> None:
        """初始化服务"""
        self._db = None

    async def _get_tasks_collection(self) -> Any:
        """获取任务集合"""
        return mongodb.get_collection(self.TASKS_COLLECTION)

    async def _get_reports_collection(self) -> Any:
        """获取报告集合"""
        return mongodb.get_collection(self.REPORTS_COLLECTION)

    async def _get_archived_collection(self) -> Any:
        """获取归档报告集合"""
        return mongodb.get_collection(self.ARCHIVED_COLLECTION)

    # ========================================================================
    # 报告创建与更新
    # ========================================================================

    async def create_report(
        self,
        user_id: str,
        task_id: str,
        final_report: str,
        recommendation: RecommendationEnum,
        buy_price: Optional[float] = None,
        sell_price: Optional[float] = None,
        risk_level: Optional[RiskLevelEnum] = None,
        token_usage: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        创建分析报告

        Args:
            user_id: 用户 ID
            task_id: 关联任务 ID
            final_report: 最终报告内容
            recommendation: 推荐结果
            buy_price: 买入价格
            sell_price: 卖出价格
            risk_level: 风险等级
            token_usage: Token 使用量

        Returns:
            报告 ID
        """
        # 从任务中获取股票信息
        tasks_col = await self._get_tasks_collection()
        task_doc = await tasks_col.find_one({"_id": ObjectId(task_id)})

        if not task_doc:
            logger.error(f"任务不存在，无法创建报告: task_id={task_id}")
            raise ValueError(f"Task {task_id} not found")

        # 创建报告文档
        report_doc = {
            "user_id": user_id,
            "task_id": task_id,
            "stock_code": task_doc.get("stock_code"),
            "trade_date": task_doc.get("trade_date"),
            "final_report": final_report,
            "recommendation": recommendation.value,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "risk_level": risk_level.value if risk_level else None,
            "token_usage": token_usage or {},
            "analyst_reports": task_doc.get("reports", {}),
            "trade_plan": task_doc.get("trade_plan"),
            "risk_assessment": task_doc.get("risk_assessment"),
            "created_at": datetime.now(timezone.utc),
            "archived_at": None,
        }

        # 插入数据库
        reports_col = await self._get_reports_collection()
        result = await reports_col.insert_one(report_doc)

        logger.info(
            f"创建分析报告: report_id={result.inserted_id}, "
            f"user_id={user_id}, stock={task_doc.get('stock_code')}, "
            f"recommendation={recommendation.value}"
        )

        return str(result.inserted_id)

    async def get_report(
        self,
        report_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个报告

        Args:
            report_id: 报告 ID
            user_id: 用户 ID

        Returns:
            报告内容或 None
        """
        reports_col = await self._get_reports_collection()

        try:
            object_id = ObjectId(report_id)
        except Exception:
            return None

        report_doc = await reports_col.find_one({"_id": object_id, "user_id": user_id})

        if not report_doc:
            return None

        return self._format_report(report_doc)

    async def list_reports(
        self,
        user_id: str,
        stock_code: Optional[str] = None,
        recommendation: Optional[RecommendationEnum] = None,
        risk_level: Optional[RiskLevelEnum] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> List[Dict[str, Any]]:
        """
        列出用户的报告

        Args:
            user_id: 用户 ID
            stock_code: 股票代码过滤
            recommendation: 推荐结果过滤
            risk_level: 风险等级过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制
            offset: 偏移量
            sort_by: 排序字段
            sort_order: 排序方向 (1=升序, -1=降序)

        Returns:
            报告列表
        """
        reports_col = await self._get_reports_collection()

        # 构建查询条件
        query: Dict[str, Any] = {"user_id": user_id}

        if stock_code:
            query["stock_code"] = stock_code

        if recommendation:
            query["recommendation"] = recommendation.value

        if risk_level:
            query["risk_level"] = risk_level.value

        if start_date or end_date:
            date_query: Dict[str, datetime] = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["created_at"] = date_query

        # 查询数据库
        cursor = reports_col.find(query).sort(sort_by, sort_order).skip(offset).limit(limit)

        reports = []
        async for report_doc in cursor:
            reports.append(self._format_report_summary(report_doc))

        return reports

    async def get_reports_summary(
        self,
        user_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        获取报告统计摘要

        Args:
            user_id: 用户 ID
            days: 统计天数

        Returns:
            统计摘要
        """
        reports_col = await self._get_reports_collection()

        # 计算时间范围
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # 聚合查询
        # 注意：数据库中 recommendation 字段存储的是枚举的中文值（"买入", "卖出", "持有"）
        # 对应 RecommendationEnum.BUY.value = "买入",
        #     RecommendationEnum.SELL.value = "卖出",
        #     RecommendationEnum.HOLD.value = "持有"
        pipeline = [
            {"$match": {"user_id": user_id, "created_at": {"$gte": start_date}}},
            {
                "$group": {
                    "_id": None,
                    "total_reports": {"$sum": 1},
                    "buy_recommendations": {
                        "$sum": {"$cond": [{"$eq": ["$recommendation", "买入"]}, 1, 0]}
                    },
                    "sell_recommendations": {
                        "$sum": {"$cond": [{"$eq": ["$recommendation", "卖出"]}, 1, 0]}
                    },
                    "hold_recommendations": {
                        "$sum": {"$cond": [{"$eq": ["$recommendation", "持有"]}, 1, 0]}
                    },
                    "total_tokens": {"$sum": "$token_usage.total_tokens"},
                    "total_buy_price": {"$sum": "$buy_price"},
                    "total_sell_price": {"$sum": "$sell_price"},
                    "buy_price_count": {"$sum": {"$cond": [{"$ne": ["$buy_price", None]}, 1, 0]}},
                    "sell_price_count": {"$sum": {"$cond": [{"$ne": ["$sell_price", None]}, 1, 0]}},
                }
            },
        ]

        result = await reports_col.aggregate(pipeline).to_list(length=1)

        if result:
            summary = result[0]

            # 计算平均价格
            avg_buy_price = None
            buy_price_count = summary.get("buy_price_count", 0)
            if buy_price_count > 0:
                avg_buy_price = summary.get("total_buy_price", 0) / buy_price_count

            avg_sell_price = None
            sell_price_count = summary.get("sell_price_count", 0)
            if sell_price_count > 0:
                avg_sell_price = summary.get("total_sell_price", 0) / sell_price_count

            return {
                "total_reports": summary.get("total_reports", 0),
                "buy_count": summary.get("buy_recommendations", 0),
                "sell_count": summary.get("sell_recommendations", 0),
                "hold_count": summary.get("hold_recommendations", 0),
                "recommendation_distribution": {
                    "buy": summary.get("buy_recommendations", 0),
                    "sell": summary.get("sell_recommendations", 0),
                    "hold": summary.get("hold_recommendations", 0),
                },
                "total_token_usage": summary.get("total_tokens", 0),
                "avg_buy_price": avg_buy_price,
                "avg_sell_price": avg_sell_price,
            }
        else:
            return {
                "total_reports": 0,
                "buy_count": 0,
                "sell_count": 0,
                "hold_count": 0,
                "recommendation_distribution": {
                    "buy": 0,
                    "sell": 0,
                    "hold": 0,
                },
                "total_token_usage": 0,
                "avg_buy_price": None,
                "avg_sell_price": None,
            }

    async def delete_report(
        self,
        report_id: str,
        user_id: str,
    ) -> bool:
        """
        删除报告

        Args:
            report_id: 报告 ID
            user_id: 用户 ID

        Returns:
            是否删除成功
        """
        reports_col = await self._get_reports_collection()

        try:
            object_id = ObjectId(report_id)
        except Exception:
            return False

        result = await reports_col.delete_one({"_id": object_id, "user_id": user_id})

        if result.deleted_count > 0:
            logger.info(f"删除报告: report_id={report_id}, user_id={user_id}")
            return True

        return False

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _format_report(self, report_doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化完整报告"""
        return {
            "id": str(report_doc["_id"]),
            "user_id": report_doc["user_id"],
            "task_id": report_doc["task_id"],
            "stock_code": report_doc["stock_code"],
            "trade_date": report_doc["trade_date"],
            "final_report": report_doc["final_report"],
            "recommendation": report_doc["recommendation"],
            "buy_price": report_doc.get("buy_price"),
            "sell_price": report_doc.get("sell_price"),
            "risk_level": report_doc.get("risk_level"),
            "token_usage": report_doc.get("token_usage", {}),
            "analyst_reports": report_doc.get("analyst_reports", {}),
            "trade_plan": report_doc.get("trade_plan"),
            "risk_assessment": report_doc.get("risk_assessment"),
            "created_at": report_doc["created_at"],
        }

    def _format_report_summary(self, report_doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化报告摘要"""
        return {
            "id": str(report_doc["_id"]),
            "task_id": report_doc["task_id"],
            "stock_code": report_doc["stock_code"],
            "trade_date": report_doc["trade_date"],
            "recommendation": report_doc["recommendation"],
            "buy_price": report_doc.get("buy_price"),
            "sell_price": report_doc.get("sell_price"),
            "risk_level": report_doc.get("risk_level"),
            "created_at": report_doc["created_at"],
        }


# =============================================================================
# 全局服务实例
# =============================================================================

_report_service: Optional[ReportService] = None


def get_report_service() -> ReportService:
    """获取全局报告服务实例"""
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
