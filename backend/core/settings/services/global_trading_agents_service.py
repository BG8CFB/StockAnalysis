"""
TradingAgents 全局配置服务

提供 TradingAgents 模块的全局/系统级配置管理，由管理员设置后所有用户共享。
"""

import logging
from datetime import datetime
from typing import Any, Dict

from core.db.mongodb import mongodb
from core.settings.models.user import TradingAgentsSettings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "system_settings"
DOCUMENT_ID = "trading_agents"


async def get_global_settings() -> Dict[str, Any]:
    """
    获取 TradingAgents 全局配置

    Returns:
        配置字典，如果不存在则返回默认配置
    """
    collection = mongodb.get_collection(COLLECTION_NAME)
    doc = await collection.find_one({"_id": DOCUMENT_ID})

    if doc:
        doc.pop("_id", None)
        logger.debug("从数据库加载 TradingAgents 全局配置")
        return doc

    # 返回默认配置
    default_settings = TradingAgentsSettings().model_dump()
    logger.debug("数据库中无全局配置，返回默认值")
    return default_settings


async def update_global_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新 TradingAgents 全局配置

    Args:
        settings: 配置字典

    Returns:
        更新后的配置字典
    """
    collection = mongodb.get_collection(COLLECTION_NAME)

    # 添加更新时间
    settings["updated_at"] = datetime.utcnow()

    # 只允许更新 TradingAgentsSettings 中定义的字段
    valid_fields = set(TradingAgentsSettings.model_fields.keys())
    filtered_settings = {k: v for k, v in settings.items() if k in valid_fields}

    await collection.update_one(
        {"_id": DOCUMENT_ID},
        {"$set": filtered_settings},
        upsert=True
    )

    logger.info(f"TradingAgents 全局配置已更新: {list(filtered_settings.keys())}")

    # 返回完整配置
    return await get_global_settings()


async def reset_to_defaults() -> bool:
    """
    恢复默认配置（删除数据库中的配置）

    Returns:
        是否成功删除
    """
    collection = mongodb.get_collection(COLLECTION_NAME)

    result = await collection.delete_one({"_id": DOCUMENT_ID})

    if result.deleted_count > 0:
        logger.info("TradingAgents 全局配置已恢复为默认值")
        return True

    logger.info("TradingAgents 全局配置本就是默认值，无需恢复")
    return True
