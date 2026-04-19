"""
报告归档服务

定期将超过 30 天的报告归档，仅保留核心字段。
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.db.mongodb import mongodb
from modules.trading_agents.schemas import TaskStatusEnum

logger = logging.getLogger(__name__)


# 归档天数阈值
ARCHIVE_DAYS = 30


class ReportArchivalService:
    """
    报告归档服务

    定期将旧报告归档，释放主集合存储空间。
    """

    def __init__(
        self,
        check_interval_hours: int = 24,  # 默认每天执行一次
        archive_days: int = ARCHIVE_DAYS,
    ):
        """
        初始化归档服务

        Args:
            check_interval_hours: 执行间隔（小时）
            archive_days: 归档天数阈值
        """
        self.check_interval_hours = check_interval_hours
        self.archive_days = archive_days
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动归档服务"""
        if self._running:
            logger.warning("报告归档服务已在运行中")
            return

        self._running = True
        self._task = asyncio.create_task(self._archival_loop())
        logger.info(
            f"报告归档服务已启动: "
            f"执行间隔={self.check_interval_hours}小时, "
            f"归档阈值={self.archive_days}天"
        )

    async def stop(self) -> None:
        """停止归档服务"""
        if not self._running:
            return

        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("报告归档服务已停止")

    async def _archival_loop(self) -> None:
        """归档循环"""
        while self._running:
            try:
                archived_count = await self._archive_old_reports()
                if archived_count > 0:
                    logger.info(f"归档报告数量: {archived_count}")
            except Exception as e:
                logger.error(f"报告归档失败: {e}", exc_info=True)

            # 等待下一次执行
            await asyncio.sleep(self.check_interval_hours * 3600)

    async def _archive_old_reports(self) -> int:
        """
        归档旧报告

        Returns:
            归档的报告数量
        """
        tasks_col = mongodb.get_collection("analysis_tasks")
        archived_col = mongodb.get_collection("archived_reports")
        traces_col = mongodb.get_collection("agent_traces")

        # 计算归档阈值
        archive_threshold = datetime.now(timezone.utc) - timedelta(days=self.archive_days)

        # 查找已完成的旧任务
        query = {
            "status": {
                "$in": [
                    TaskStatusEnum.COMPLETED.value,
                    TaskStatusEnum.FAILED.value,
                    TaskStatusEnum.EXPIRED.value,
                    TaskStatusEnum.CANCELLED.value,
                ]
            },
            "created_at": {"$lt": archive_threshold},
        }

        old_tasks = await tasks_col.find(query).to_list(None)

        if not old_tasks:
            return 0

        logger.info(f"发现 {len(old_tasks)} 个可归档的任务")

        archived_count = 0

        for task_doc in old_tasks:
            task_id = str(task_doc["_id"])
            user_id = task_doc["user_id"]
            stock_code = task_doc.get("stock_code", "未知")

            try:
                # 创建归档文档（仅保留核心字段）
                archived_doc = {
                    "task_id": task_id,
                    "user_id": user_id,
                    "stock_code": stock_code,
                    "trade_date": task_doc.get("trade_date"),
                    "analysis_time": task_doc.get("created_at"),
                    "final_report": await self._extract_final_report(task_doc),
                    "recommendation": task_doc.get("final_recommendation"),
                    "buy_price": task_doc.get("buy_price"),
                    "sell_price": task_doc.get("sell_price"),
                    "risk_level": task_doc.get("risk_level"),
                    "token_usage": task_doc.get("token_usage", {}),
                    "status": task_doc["status"],
                    "archived_at": datetime.now(timezone.utc),
                }

                # 插入归档集合
                await archived_col.insert_one(archived_doc)

                # 删除 agent_traces 中的相关记录
                await traces_col.delete_many({"task_id": task_id})

                # 更新原任务记录，移除中间数据
                await tasks_col.update_one(
                    {"_id": task_doc["_id"]},
                    {
                        "$set": {
                            "reports": {},
                            "trade_plan": None,
                            "risk_assessment": None,
                            "analyst_reports": {},
                            "archived_at": datetime.now(timezone.utc),
                        }
                    },
                )

                archived_count += 1

                logger.debug(
                    f"报告已归档: task_id={task_id}, " f"user_id={user_id}, stock={stock_code}"
                )

            except Exception as e:
                logger.error(f"归档报告失败: task_id={task_id}, error={e}", exc_info=True)

        return archived_count

    async def _extract_final_report(self, task_doc: Dict[str, Any]) -> Optional[str]:
        """
        提取最终报告

        Args:
            task_doc: 任务文档

        Returns:
            最终报告内容或 None
        """
        # 如果任务有最终报告，优先使用
        if task_doc.get("final_report"):
            return str(task_doc["final_report"])

        # 否则，尝试从分析师报告中生成简单摘要
        reports = task_doc.get("reports", {})
        if not reports:
            return None

        summary_parts = []
        for agent_slug, report_content in reports.items():
            if report_content:
                summary_parts.append(f"## {agent_slug}\n{report_content}\n")

        return "\n".join(summary_parts) if summary_parts else None

    async def get_archived_reports(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """
        获取用户的归档报告

        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            归档报告列表
        """
        archived_col = mongodb.get_collection("archived_reports")

        cursor = (
            archived_col.find({"user_id": user_id})
            .sort("archived_at", -1)
            .skip(offset)
            .limit(limit)
        )

        reports = []
        async for report_doc in cursor:
            reports.append(
                {
                    "task_id": report_doc["task_id"],
                    "stock_code": report_doc["stock_code"],
                    "trade_date": report_doc["trade_date"],
                    "analysis_time": report_doc["analysis_time"],
                    "recommendation": report_doc.get("recommendation"),
                    "buy_price": report_doc.get("buy_price"),
                    "sell_price": report_doc.get("sell_price"),
                    "risk_level": report_doc.get("risk_level"),
                    "token_usage": report_doc.get("token_usage", {}),
                    "status": report_doc["status"],
                    "archived_at": report_doc["archived_at"],
                }
            )

        return reports

    async def restore_report(
        self,
        task_id: str,
        user_id: str,
    ) -> bool:
        """
        恢复归档报告

        Args:
            task_id: 任务 ID
            user_id: 用户 ID

        Returns:
            是否恢复成功
        """
        archived_col = mongodb.get_collection("archived_reports")
        tasks_col = mongodb.get_collection("analysis_tasks")

        # 查找归档报告
        archived_doc = await archived_col.find_one({"task_id": task_id, "user_id": user_id})

        if not archived_doc:
            logger.warning(f"归档报告不存在: task_id={task_id}")
            return False

        try:
            from bson import ObjectId

            # 恢复任务记录
            await tasks_col.update_one(
                {"_id": ObjectId(task_id)},
                {
                    "$set": {
                        "final_report": archived_doc.get("final_report"),
                        "archived_at": None,
                    }
                },
            )

            # 删除归档记录
            await archived_col.delete_one({"_id": archived_doc["_id"]})

            logger.info(f"归档报告已恢复: task_id={task_id}")

            return True

        except Exception as e:
            logger.error(f"恢复归档报告失败: task_id={task_id}, error={e}", exc_info=True)
            return False


# =============================================================================
# 全局归档服务实例
# =============================================================================

_archival_service: Optional[ReportArchivalService] = None


def get_archival_service() -> ReportArchivalService:
    """获取全局归档服务实例"""
    global _archival_service
    if _archival_service is None:
        _archival_service = ReportArchivalService()
    return _archival_service


async def start_archival_service() -> None:
    """启动全局归档服务"""
    service = get_archival_service()
    await service.start()


async def stop_archival_service() -> None:
    """停止全局归档服务"""
    global _archival_service
    if _archival_service is not None:
        await _archival_service.stop()
