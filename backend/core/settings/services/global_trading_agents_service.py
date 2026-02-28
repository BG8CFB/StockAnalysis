"""
TradingAgents 全局配置服务 (改进版)

提供 TradingAgents 模块的全局/系统级配置管理，由管理员设置后所有用户共享。

改进点:
1. 系统启动时自动初始化默认配置
2. 支持配置合并策略
3. 提供完整的 CRUD 操作
4. 自动处理空值，回退到合理默认值
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId

from core.db.mongodb import mongodb
from core.settings.models.user import TradingAgentsSettings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "system_settings"
DOCUMENT_ID = "trading_agents"

# =============================================================================
# 硬编码的默认配置 (代码层面的兜底值)
# =============================================================================

DEFAULT_CONFIG = {
    # AI 模型配置 - 使用特殊标记表示"使用第一个可用模型"
    "data_collection_model_id": "",  # 空字符串 = 使用第一个可用模型
    "debate_model_id": "",  # 空字符串 = 使用第一个可用模型

    # 辩论配置
    "default_debate_rounds": 3,
    "max_debate_rounds": 5,

    # 超时配置
    "phase_timeout_minutes": 30,
    "agent_timeout_minutes": 10,
    "tool_timeout_seconds": 30,

    # 流程默认配置
    "default_phase1_agents": [],  # 空数组 = 用户自行选择
    "default_phase2_enabled": True,
    "default_phase3_enabled": False,

    # 其他配置
    "task_expiry_hours": 24,
    "archive_days": 30,
    "enable_loop_detection": True,
    "enable_progress_events": True,
}


async def ensure_default_config() -> bool:
    """
    确保全局配置存在，不存在则创建默认配置

    此方法应在系统启动时调用，确保配置始终可用。

    Returns:
        是否创建了新配置 (False = 已存在，True = 新创建)
    """
    collection = mongodb.get_collection(COLLECTION_NAME)

    # 检查配置是否存在
    existing = await collection.find_one({"_id": DOCUMENT_ID})

    if existing:
        logger.info("TradingAgents 全局配置已存在，跳过初始化")
        return False

    # 创建默认配置
    default_config = DEFAULT_CONFIG.copy()
    default_config["_id"] = DOCUMENT_ID
    default_config["created_at"] = datetime.now(timezone.utc)
    default_config["updated_at"] = datetime.now(timezone.utc)
    default_config["version"] = "1.0"

    await collection.insert_one(default_config)
    logger.info("✅ TradingAgents 全局配置已初始化为默认值")

    return True


async def get_global_settings() -> Dict[str, Any]:
    """
    获取 TradingAgents 全局配置

    配置优先级:
    1. MongoDB 中的管理员配置 (最高优先级)
    2. 硬编码的默认配置 (兜底)

    Returns:
        配置字典
    """
    collection = mongodb.get_collection(COLLECTION_NAME)
    doc = await collection.find_one({"_id": DOCUMENT_ID})

    if doc:
        # 移除 MongoDB 特有字段
        doc.pop("_id", None)
        doc.pop("created_at", None)
        doc.pop("updated_at", None)
        doc.pop("version", None)
        logger.debug("✅ 从 MongoDB 加载 TradingAgents 全局配置")
        return doc

    # 返回硬编码默认配置
    logger.warning("⚠️ MongoDB 中无全局配置，使用硬编码默认值")
    return DEFAULT_CONFIG.copy()


async def update_global_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新 TradingAgents 全局配置

    Args:
        settings: 配置字典 (只更新提供的字段)

    Returns:
        更新后的完整配置字典
    """
    collection = mongodb.get_collection(COLLECTION_NAME)

    # 构建更新字段
    update_fields = {"updated_at": datetime.now(timezone.utc)}

    # 只更新 TradingAgentsSettings 中定义的有效字段
    valid_fields = set(TradingAgentsSettings.model_fields.keys())

    for key, value in settings.items():
        if key in valid_fields:
            update_fields[key] = value
        else:
            logger.warning(f"⚠️ 忽略无效字段: {key}")

    # 使用 upsert: 如果不存在则创建
    await collection.update_one(
        {"_id": DOCUMENT_ID},
        {"$set": update_fields},
        upsert=True
    )

    logger.info(f"✅ TradingAgents 全局配置已更新: {list(update_fields.keys())}")

    # 返回完整配置
    return await get_global_settings()


async def reset_to_defaults() -> bool:
    """
    恢复默认配置（删除数据库中的配置，系统将回退到硬编码默认值）

    Returns:
        是否成功删除
    """
    collection = mongodb.get_collection(COLLECTION_NAME)

    result = await collection.delete_one({"_id": DOCUMENT_ID})

    if result.deleted_count > 0:
        logger.info("✅ TradingAgents 全局配置已删除，系统将使用硬编码默认值")
        return True

    logger.info("ℹ️ TradingAgents 全局配置本来就不存在")
    return True


async def get_global_settings_with_fallback() -> Dict[str, Any]:
    """
    获取全局配置，确保所有字段都有值（即使是空值）

    对于 MongoDB 中缺失的字段，使用硬编码默认值填充。

    Returns:
        完整的配置字典，所有字段都存在
    """
    # 获取 MongoDB 配置
    mongo_config = await get_global_settings()

    # 合并硬编码默认值（MongoDB 配置优先）
    full_config = DEFAULT_CONFIG.copy()
    full_config.update(mongo_config)

    return full_config


async def get_merged_config(user_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    获取合并后的配置 (全局配置 + 用户配置)

    合并策略:
    - 用户配置中非空字段覆盖全局配置
    - 用户配置中空字段使用全局配置
    - 全局配置中空字段使用硬编码默认值

    Args:
        user_config: 用户自定义配置 (可选)

    Returns:
        合并后的完整配置
    """
    # 获取完整全局配置 (已包含硬编码默认值)
    global_config = await get_global_settings_with_fallback()

    if not user_config:
        return global_config

    # 合并用户配置
    merged_config = global_config.copy()

    for key, value in user_config.items():
        # 只覆盖非空值
        if value is not None and value != "" and value != []:
            merged_config[key] = value

    return merged_config
