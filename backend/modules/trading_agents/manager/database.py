"""
TradingAgents 数据库集合和索引初始化

定义所有模块特定的数据库集合和索引。
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)


async def init_indexes() -> None:
    """初始化 TradingAgents 模块的数据库索引"""
    db: AsyncIOMotorDatabase = mongodb.database

    # ========================================
    # AI 模型配置集合
    # ========================================
    await db.ai_models.create_index("owner_id", name="idx_owner_id")
    await db.ai_models.create_index("is_system", name="idx_is_system")
    await db.ai_models.create_index("enabled", name="idx_enabled")
    await db.ai_models.create_index("created_at", name="idx_created_at")
    await db.ai_models.create_index(
        [("owner_id", 1), ("enabled", 1)],
        name="idx_owner_enabled"
    )

    # ========================================
    # MCP 服务器配置集合
    # ========================================
    await db.mcp_servers.create_index("owner_id", name="idx_owner_id")
    await db.mcp_servers.create_index("is_system", name="idx_is_system")
    await db.mcp_servers.create_index("enabled", name="idx_enabled")
    await db.mcp_servers.create_index("status", name="idx_status")
    await db.mcp_servers.create_index("created_at", name="idx_created_at")
    await db.mcp_servers.create_index(
        [("owner_id", 1), ("enabled", 1)],
        name="idx_owner_enabled"
    )

    # ========================================
    # 智能体配置集合
    # ========================================
    await db.agent_configs.create_index("user_id", name="idx_user_id", unique=True)
    await db.agent_configs.create_index("created_at", name="idx_created_at")
    await db.agent_configs.create_index("updated_at", name="idx_updated_at")

    # ========================================
    # 分析任务集合
    # ========================================
    await db.analysis_tasks.create_index("user_id", name="idx_user_id")
    await db.analysis_tasks.create_index("status", name="idx_status")
    await db.analysis_tasks.create_index("stock_code", name="idx_stock_code")
    await db.analysis_tasks.create_index("created_at", name="idx_created_at")
    await db.analysis_tasks.create_index("started_at", name="idx_started_at")
    await db.analysis_tasks.create_index("completed_at", name="idx_completed_at")
    await db.analysis_tasks.create_index("expired_at", name="idx_expired_at")
    await db.analysis_tasks.create_index(
        [("user_id", 1), ("status", 1)],
        name="idx_user_status"
    )
    await db.analysis_tasks.create_index(
        [("user_id", 1), ("created_at", -1)],
        name="idx_user_created"
    )
    await db.analysis_tasks.create_index(
        [("status", 1), ("created_at", 1)],
        name="idx_status_created"
    )
    # 批量任务索引
    await db.analysis_tasks.create_index("batch_id", name="idx_batch_id")

    # ========================================
    # 分析报告集合
    # ========================================
    await db.analysis_reports.create_index("task_id", name="idx_task_id")
    await db.analysis_reports.create_index("user_id", name="idx_user_id")
    await db.analysis_reports.create_index("stock_code", name="idx_stock_code")
    await db.analysis_reports.create_index("recommendation", name="idx_recommendation")
    await db.analysis_reports.create_index("created_at", name="idx_created_at")
    await db.analysis_reports.create_index(
        [("user_id", 1), ("created_at", -1)],
        name="idx_user_created"
    )
    await db.analysis_reports.create_index(
        [("user_id", 1), ("stock_code", 1)],
        name="idx_user_stock"
    )
    await db.analysis_reports.create_index(
        [("user_id", 1), ("recommendation", 1)],
        name="idx_user_recommendation"
    )

    # ========================================
    # 归档报告集合
    # ========================================
    await db.archived_reports.create_index("user_id", name="idx_user_id")
    await db.archived_reports.create_index("stock_code", name="idx_stock_code")
    await db.archived_reports.create_index("recommendation", name="idx_recommendation")
    await db.archived_reports.create_index("archived_at", name="idx_archived_at")
    await db.archived_reports.create_index(
        [("user_id", 1), ("archived_at", -1)],
        name="idx_user_archived"
    )

    # ========================================
    # 智能体执行跟踪集合
    # ========================================
    await db.agent_traces.create_index("task_id", name="idx_task_id")
    await db.agent_traces.create_index("agent_slug", name="idx_agent_slug")
    await db.agent_traces.create_index("timestamp", name="idx_timestamp")
    await db.agent_traces.create_index(
        [("task_id", 1), ("timestamp", 1)],
        name="idx_task_timestamp"
    )

    logger.info("TradingAgents indexes initialized successfully")


# =============================================================================
# 集合查询辅助函数
# =============================================================================

async def get_collection_stats() -> dict:
    """
    获取所有 TradingAgents 集合的统计信息

    Returns:
        包含各集合文档数量的字典
    """
    db: AsyncIOMotorDatabase = mongodb.database

    collections = [
        "ai_models",
        "mcp_servers",
        "agent_configs",
        "analysis_tasks",
        "analysis_reports",
        "archived_reports",
        "agent_traces",
    ]

    stats = {}
    for collection_name in collections:
        try:
            count = await db[collection_name].count_documents({})
            stats[collection_name] = count
        except Exception as e:
            logger.warning(f"Failed to get stats for {collection_name}: {e}")
            stats[collection_name] = -1

    return stats


async def drop_collections(collections: Optional[list[str]] = None) -> None:
    """
    删除指定集合（仅用于测试环境）

    Args:
        collections: 要删除的集合列表，None 表示删除所有 TradingAgents 集合
    """
    if collections is None:
        collections = [
            "ai_models",
            "mcp_servers",
            "agent_configs",
            "analysis_tasks",
            "analysis_reports",
            "archived_reports",
            "agent_traces",
        ]

    db: AsyncIOMotorDatabase = mongodb.database

    for collection_name in collections:
        try:
            await db.drop_collection(collection_name)
            logger.info(f"Dropped collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to drop collection {collection_name}: {e}")
