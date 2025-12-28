"""
API Key 加密数据迁移脚本

将数据库中现有的明文 API Key 加密。
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings
from core.security.encryption import encrypt_sensitive_data, is_encrypted

logger = logging.getLogger(__name__)


async def migrate_api_keys_to_encrypted():
    """
    迁移所有 AI 模型和 MCP 服务器的 API Key 到加密存储
    """
    # 连接数据库
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    logger.info("开始 API Key 加密迁移...")

    # ========================================
    # 迁移 AI 模型配置
    # ========================================
    ai_models_collection = db.ai_models
    ai_models_cursor = ai_models_collection.find({})

    ai_models_count = 0
    ai_models_encrypted_count = 0

    async for model in ai_models_cursor:
        ai_models_count += 1
        api_key = model.get("api_key", "")

        if not api_key:
            continue

        # 检查是否已加密
        if is_encrypted(api_key):
            logger.debug(f"AI 模型 {model.get('name')} 的 API Key 已加密，跳过")
            ai_models_encrypted_count += 1
            continue

        # 加密 API Key
        try:
            encrypted_key = encrypt_sensitive_data(api_key)

            # 更新数据库
            await ai_models_collection.update_one(
                {"_id": model["_id"]},
                {"$set": {"api_key": encrypted_key}}
            )

            logger.info(f"✓ AI 模型 {model.get('name')} 的 API Key 已加密")
        except Exception as e:
            logger.error(f"✗ AI 模型 {model.get('name')} 加密失败: {e}")

    logger.info(f"AI 模型迁移完成: 总计 {ai_models_count}，已加密 {ai_models_encrypted_count}")

    # ========================================
    # 迁移 MCP 服务器配置
    # ========================================
    mcp_servers_collection = db.mcp_servers
    mcp_servers_cursor = mcp_servers_collection.find({})

    mcp_servers_count = 0
    mcp_servers_encrypted_count = 0

    async for server in mcp_servers_cursor:
        mcp_servers_count += 1
        auth_token = server.get("auth_token", "")

        if not auth_token:
            continue

        # 检查是否已加密
        if is_encrypted(auth_token):
            logger.debug(f"MCP 服务器 {server.get('name')} 的 auth_token 已加密，跳过")
            mcp_servers_encrypted_count += 1
            continue

        # 加密 auth_token
        try:
            encrypted_token = encrypt_sensitive_data(auth_token)

            # 更新数据库
            await mcp_servers_collection.update_one(
                {"_id": server["_id"]},
                {"$set": {"auth_token": encrypted_token}}
            )

            logger.info(f"✓ MCP 服务器 {server.get('name')} 的 auth_token 已加密")
        except Exception as e:
            logger.error(f"✗ MCP 服务器 {server.get('name')} 加密失败: {e}")

    logger.info(f"MCP 服务器迁移完成: 总计 {mcp_servers_count}，已加密 {mcp_servers_encrypted_count}")

    # 关闭连接
    client.close()

    logger.info("API Key 加密迁移完成！")


if __name__ == "__main__":
    # 直接运行此脚本执行迁移
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(migrate_api_keys_to_encrypted())
