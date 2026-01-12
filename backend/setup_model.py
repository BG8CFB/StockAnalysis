# -*- coding: utf-8 -*-
"""配置 AI 模型"""
import asyncio
import sys
sys.path.insert(0, '.')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from bson import ObjectId

async def setup_model():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.stock_analysis

    # 创建智谱 GLM-4.7 模型
    model_id = str(ObjectId())
    model_doc = {
        "_id": ObjectId(model_id),
        "id": model_id,
        "name": "智谱 GLM-4.7",
        "provider": "zhipu",
        "model_name": "glm-4.7",
        "api_base": "https://open.bigmodel.cn/api/paas/v4/",
        "api_key": "c47d36e6e5e64d278e0e23be4e1e5e98.VtqxJ2zF6lWQp5Q4",
        "enabled": True,
        "is_default": True,
        "max_concurrency": 10,
        "task_concurrency": 3,
        "batch_concurrency": 2,
        "thinking_enabled": False,
        "thinking_mode": "auto",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # 删除旧模型（如果存在）
    await db.ai_models.delete_many({"provider": "zhipu"})

    # 插入新模型
    result = await db.ai_models.insert_one(model_doc)
    print(f"模型创建成功: {result.inserted_id}")

    # 更新用户默认模型设置
    await db.users.update_one(
        {"account": "test_ta_user"},
        {"$set": {
            "settings.trading_agents_settings.data_collection_model_id": model_id,
            "settings.trading_agents_settings.debate_model_id": model_id,
            "updated_at": datetime.utcnow()
        }}
    )
    print("用户默认模型已更新")

    client.close()

if __name__ == "__main__":
    asyncio.run(setup_model())
