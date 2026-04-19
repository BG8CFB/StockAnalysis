"""
模型目录管理服务

MongoDB 集合 model_catalog 的 CRUD 操作。
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.ai.model_catalog_models import (
    AvailableModelItem,
    AvailableModelsByProvider,
    ModelCatalogCreateRequest,
    ModelCatalogItem,
    ModelCatalogResponse,
)
from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)

COLLECTION_NAME = "model_catalog"


class ModelCatalogService:
    """模型目录管理服务"""

    async def _get_collection(self) -> Any:
        return mongodb.get_collection(COLLECTION_NAME)

    async def list_catalogs(self) -> List[ModelCatalogResponse]:
        """获取所有目录"""
        collection = await self._get_collection()
        cursor = collection.find({})
        docs = await cursor.to_list(length=None)
        results = []
        for doc in docs:
            models = [ModelCatalogItem(**m) for m in doc.get("models", [])]
            results.append(
                ModelCatalogResponse(
                    provider=doc["provider"],
                    provider_name=doc.get("provider_name", doc["provider"]),
                    models=models,
                )
            )
        return results

    async def get_catalog(self, provider: str) -> Optional[ModelCatalogResponse]:
        """获取指定厂家的目录"""
        collection = await self._get_collection()
        doc = await collection.find_one({"provider": provider})
        if not doc:
            return None
        models = [ModelCatalogItem(**m) for m in doc.get("models", [])]
        return ModelCatalogResponse(
            provider=doc["provider"],
            provider_name=doc.get("provider_name", doc["provider"]),
            models=models,
        )

    async def save_catalog(self, data: ModelCatalogCreateRequest) -> bool:
        """保存或更新目录"""
        collection = await self._get_collection()
        models_data = [m.model_dump() for m in data.models]

        now = datetime.now(timezone.utc)
        await collection.update_one(
            {"provider": data.provider},
            {
                "$set": {
                    "provider_name": data.provider_name,
                    "models": models_data,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        return True

    async def delete_catalog(self, provider: str) -> bool:
        """删除目录"""
        collection = await self._get_collection()
        result = await collection.delete_one({"provider": provider})
        return bool(result.deleted_count > 0)

    async def init_defaults(self) -> Dict:
        """初始化默认模型目录"""
        defaults: List[ModelCatalogCreateRequest] = [
            ModelCatalogCreateRequest(
                provider="zhipu",
                provider_name="智谱AI",
                models=[
                    ModelCatalogItem(
                        name="glm-4.7",
                        display_name="GLM-4.7",
                        capabilities=["chat", "tool_calling"],
                    ),
                    ModelCatalogItem(
                        name="glm-4-flash",
                        display_name="GLM-4-Flash",
                        capabilities=["chat"],
                    ),
                    ModelCatalogItem(
                        name="glm-4-air",
                        display_name="GLM-4-Air",
                        capabilities=["chat"],
                    ),
                ],
            ),
            ModelCatalogCreateRequest(
                provider="deepseek",
                provider_name="DeepSeek",
                models=[
                    ModelCatalogItem(
                        name="deepseek-chat",
                        display_name="DeepSeek Chat",
                        capabilities=["chat", "tool_calling"],
                    ),
                    ModelCatalogItem(
                        name="deepseek-reasoner",
                        display_name="DeepSeek Reasoner",
                        capabilities=["reasoning"],
                    ),
                ],
            ),
            ModelCatalogCreateRequest(
                provider="openai",
                provider_name="OpenAI",
                models=[
                    ModelCatalogItem(
                        name="gpt-4o",
                        display_name="GPT-4o",
                        capabilities=["chat", "vision", "tool_calling"],
                    ),
                    ModelCatalogItem(
                        name="gpt-4o-mini",
                        display_name="GPT-4o Mini",
                        capabilities=["chat", "tool_calling"],
                    ),
                    ModelCatalogItem(
                        name="o1",
                        display_name="o1",
                        capabilities=["reasoning"],
                    ),
                ],
            ),
            ModelCatalogCreateRequest(
                provider="qwen",
                provider_name="通义千问",
                models=[
                    ModelCatalogItem(
                        name="qwen-max",
                        display_name="Qwen Max",
                        capabilities=["chat", "tool_calling"],
                    ),
                    ModelCatalogItem(
                        name="qwen-plus",
                        display_name="Qwen Plus",
                        capabilities=["chat"],
                    ),
                    ModelCatalogItem(
                        name="qwen-turbo",
                        display_name="Qwen Turbo",
                        capabilities=["chat"],
                    ),
                ],
            ),
        ]

        added = 0
        skipped = 0
        for catalog in defaults:
            existing = await self.get_catalog(catalog.provider)
            if existing:
                skipped += 1
                continue
            await self.save_catalog(catalog)
            added += 1

        return {
            "success": True,
            "message": f"初始化完成: {added} 个新增, {skipped} 个已存在",
        }

    async def get_available_models(self) -> List[AvailableModelsByProvider]:
        """获取所有可用模型（从目录中提取）"""
        catalogs = await self.list_catalogs()
        results = []
        for catalog in catalogs:
            models = [
                AvailableModelItem(name=m.name, display_name=m.display_name)
                for m in catalog.models
                if not m.is_deprecated
            ]
            if models:
                results.append(
                    AvailableModelsByProvider(
                        provider=catalog.provider,
                        provider_name=catalog.provider_name,
                        models=models,
                    )
                )
        return results


# 全局单例
_model_catalog_service: Optional[ModelCatalogService] = None


def get_model_catalog_service() -> ModelCatalogService:
    """获取模型目录服务单例"""
    global _model_catalog_service
    if _model_catalog_service is None:
        _model_catalog_service = ModelCatalogService()
    return _model_catalog_service
