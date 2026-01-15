"""
AI 使用统计和成本追踪

记录每次 AI 调用的 Token 使用、成本和工具调用信息。
提供按任务、模型、用户的统计功能。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class ToolCallRecord:
    """工具调用记录"""
    tool_name: str
    call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class AIUsageRecord:
    """AI 使用记录"""

    # 基本信息
    user_id: str
    task_id: Optional[str]  # 关联任务 ID（如果有）
    model_id: str
    model_name: str  # 模型显示名称
    phase: Optional[str]  # 阶段（如 phase1, phase2）
    agent_slug: Optional[str]  # 智能体标识

    # Token 统计
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    thinking_tokens: int = 0

    # 成本统计（单位：分）
    cost: Optional[Decimal] = None

    # 工具调用统计
    tool_calls: Dict[str, ToolCallRecord] = field(default_factory=dict)

    # 时间戳
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # 额外信息
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于存储）"""
        return {
            "user_id": self.user_id,
            "task_id": self.task_id,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "phase": self.phase,
            "agent_slug": self.agent_slug,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "thinking_tokens": self.thinking_tokens,
            "cost": float(self.cost) if self.cost is not None else None,
            "tool_calls": {
                name: {
                    "tool_name": record.tool_name,
                    "call_count": record.call_count,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "total_tokens": record.total_tokens,
                }
                for name, record in self.tool_calls.items()
            },
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# =============================================================================
# 统计服务
# =============================================================================

class AIUsageService:
    """AI 使用统计服务"""

    COLLECTION_NAME = "ai_usage_stats"

    def __init__(self):
        self._db = None

    async def _get_collection(self):
        """获取数据库集合"""
        return mongodb.get_collection(self.COLLECTION_NAME)

    async def record_usage(
        self,
        record: AIUsageRecord
    ) -> bool:
        """
        记录 AI 使用情况

        Args:
            record: 使用记录

        Returns:
            是否记录成功
        """
        try:
            collection = await self._get_collection()
            await collection.insert_one(record.to_dict())
            logger.debug(
                f"记录 AI 使用: user={record.user_id}, "
                f"model={record.model_id}, "
                f"tokens={record.total_tokens}, "
                f"cost={record.cost}"
            )
            return True
        except Exception as e:
            logger.error(f"记录 AI 使用失败: {e}")
            return False

    async def record_from_response(
        self,
        user_id: str,
        model_id: str,
        model_name: str,
        response: Any,
        task_id: Optional[str] = None,
        phase: Optional[str] = None,
        agent_slug: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None,
    ) -> bool:
        """
        从 AI 响应记录使用情况

        Args:
            user_id: 用户 ID
            model_id: 模型 ID
            model_name: 模型显示名称
            response: AI 响应对象
            task_id: 任务 ID（可选）
            phase: 阶段（可选）
            agent_slug: 智能体标识（可选）
            tool_calls: 工具调用列表（可选）

        Returns:
            是否记录成功
        """
        # 解析 Token 使用
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        thinking_tokens = 0

        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            if usage:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        # 解析思考 Token
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if metadata:
                thinking_tokens = metadata.get("reasoning_tokens", 0)

        # 计算成本
        from .pricing import get_pricing_service
        cost = get_pricing_service().calculate_cost(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
        )

        # 解析工具调用
        tool_call_records: Dict[str, ToolCallRecord] = {}
        if tool_calls:
            for tc in tool_calls:
                tool_name = tc.get("name", "unknown")
                if tool_name not in tool_call_records:
                    tool_call_records[tool_name] = ToolCallRecord(tool_name=tool_name)
                tool_call_records[tool_name].call_count += 1

        # 创建记录
        record = AIUsageRecord(
            user_id=user_id,
            task_id=task_id,
            model_id=model_id,
            model_name=model_name,
            phase=phase,
            agent_slug=agent_slug,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            thinking_tokens=thinking_tokens,
            cost=cost,
            tool_calls=tool_call_records,
        )

        return await self.record_usage(record)

    async def get_user_stats(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取用户统计信息

        Args:
            user_id: 用户 ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            统计信息
        """
        collection = await self._get_collection()

        # 构建查询条件
        query = {"user_id": user_id}
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date

        # 聚合统计
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": "$model_id",
                    "model_name": {"$first": "$model_name"},
                    "total_calls": {"$sum": 1},
                    "total_input_tokens": {"$sum": "$input_tokens"},
                    "total_output_tokens": {"$sum": "$output_tokens"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_thinking_tokens": {"$sum": "$thinking_tokens"},
                    "total_cost": {"$sum": "$cost"},
                }
            },
            {
                "$project": {
                    "model_id": "$_id",
                    "model_name": 1,
                    "total_calls": 1,
                    "total_input_tokens": 1,
                    "total_output_tokens": 1,
                    "total_tokens": 1,
                    "total_thinking_tokens": 1,
                    "total_cost": 1,
                }
            },
        ]

        results = []
        async for doc in collection.aggregate(pipeline):
            results.append(doc)

        # 计算总计
        summary = {
            "total_calls": sum(r["total_calls"] for r in results),
            "total_tokens": sum(r["total_tokens"] for r in results),
            "total_cost": sum(r["total_cost"] or 0 for r in results),
            "by_model": results,
        }

        return summary

    async def get_task_stats(
        self,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        获取任务统计信息

        Args:
            task_id: 任务 ID

        Returns:
            统计信息
        """
        collection = await self._get_collection()

        # 聚合统计
        pipeline = [
            {"$match": {"task_id": task_id}},
            {
                "$group": {
                    "_id": "$phase",
                    "total_calls": {"$sum": 1},
                    "total_input_tokens": {"$sum": "$input_tokens"},
                    "total_output_tokens": {"$sum": "$output_tokens"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_thinking_tokens": {"$sum": "$thinking_tokens"},
                    "total_cost": {"$sum": "$cost"},
                }
            },
            {
                "$project": {
                    "phase": "$_id",
                    "total_calls": 1,
                    "total_input_tokens": 1,
                    "total_output_tokens": 1,
                    "total_tokens": 1,
                    "total_thinking_tokens": 1,
                    "total_cost": 1,
                }
            },
        ]

        results = []
        async for doc in collection.aggregate(pipeline):
            results.append(doc)

        # 计算总计
        summary = {
            "total_calls": sum(r["total_calls"] for r in results),
            "total_tokens": sum(r["total_tokens"] for r in results),
            "total_cost": sum(r["total_cost"] or 0 for r in results),
            "by_phase": {r["phase"]: r for r in results},
        }

        return summary


# =============================================================================
# 全局单例
# =============================================================================

_usage_service: Optional[AIUsageService] = None


def get_usage_service() -> AIUsageService:
    """获取统计服务单例"""
    global _usage_service
    if _usage_service is None:
        _usage_service = AIUsageService()
    return _usage_service
