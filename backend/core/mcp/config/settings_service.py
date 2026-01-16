"""
MCP 系统配置数据库服务

提供 MCP 系统配置的数据库 CRUD 操作。
"""

import logging
from datetime import datetime
from typing import Any, Dict

from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)

COLLECTION_NAME = "mcp_settings"
DOCUMENT_ID = "system"


async def get_system_settings() -> Dict[str, Any]:
    """
    获取系统配置（从数据库）

    Returns:
        配置字典，如果不存在则返回空字典
    """
    collection = mongodb.get_collection(COLLECTION_NAME)
    doc = await collection.find_one({"_id": DOCUMENT_ID})

    if doc:
        doc.pop("_id", None)
        logger.debug("从数据库加载 MCP 系统配置")
        return doc

    logger.debug("数据库中无 MCP 系统配置，将使用默认值")
    return {}


async def update_system_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新系统配置

    Args:
        settings: 配置字典

    Returns:
        更新后的配置字典
    """
    collection = mongodb.get_collection(COLLECTION_NAME)

    settings["updated_at"] = datetime.utcnow()

    await collection.update_one(
        {"_id": DOCUMENT_ID},
        {"$set": settings},
        upsert=True
    )

    logger.info(f"MCP 系统配置已更新: {list(settings.keys())}")
    return settings


async def reset_to_defaults() -> bool:
    """
    恢复默认配置（删除数据库中的配置）

    Returns:
        是否成功删除
    """
    collection = mongodb.get_collection(COLLECTION_NAME)

    result = await collection.delete_one({"_id": DOCUMENT_ID})

    if result.deleted_count > 0:
        logger.info("MCP 系统配置已恢复为默认值")
        return True

    logger.info("MCP 系统配置本就是默认值，无需恢复")
    return True
