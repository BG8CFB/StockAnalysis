"""
LLM 厂家管理服务

MongoDB 集合 llm_providers 的 CRUD 操作。
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from core.ai.provider_models import (
    AggregatorType,
    InitAggregatorsResult,
    LLMProviderCreateRequest,
    LLMProviderResponse,
    LLMProviderUpdateRequest,
    MigrateEnvResult,
    SupportedFeature,
)
from core.db.mongodb import mongodb
from core.security.encryption import decrypt_sensitive_data, encrypt_sensitive_data

logger = logging.getLogger(__name__)

COLLECTION_NAME = "llm_providers"


def _mask_value(value: Optional[str]) -> Optional[str]:
    """脱敏敏感值"""
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def _doc_to_response(doc: Dict) -> LLMProviderResponse:
    """将 MongoDB 文档转为响应模型"""
    api_key_encrypted = doc.get("api_key", "")
    api_key_plain = ""
    if api_key_encrypted:
        try:
            from core.security.encryption import is_encrypted

            if is_encrypted(api_key_encrypted):
                api_key_plain = decrypt_sensitive_data(api_key_encrypted)
            else:
                api_key_plain = api_key_encrypted
        except Exception:
            api_key_plain = ""

    api_secret_encrypted = doc.get("api_secret", "")
    api_secret_plain = ""
    if api_secret_encrypted:
        try:
            from core.security.encryption import is_encrypted

            if is_encrypted(api_secret_encrypted):
                api_secret_plain = decrypt_sensitive_data(api_secret_encrypted)
            else:
                api_secret_plain = api_secret_encrypted
        except Exception:
            api_secret_plain = ""

    features_raw = doc.get("supported_features", [])
    features = []
    for f in features_raw:
        try:
            features.append(SupportedFeature(f))
        except ValueError:
            pass

    agg_type = doc.get("aggregator_type")
    agg_enum = None
    if agg_type:
        try:
            agg_enum = AggregatorType(agg_type)
        except ValueError:
            pass

    return LLMProviderResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        display_name=doc["display_name"],
        description=doc.get("description"),
        website=doc.get("website"),
        api_doc_url=doc.get("api_doc_url"),
        logo_url=doc.get("logo_url"),
        is_active=doc.get("is_active", True),
        supported_features=features,
        default_base_url=doc.get("default_base_url"),
        api_key=_mask_value(api_key_plain),
        api_secret=_mask_value(api_secret_plain),
        extra_config={
            "has_api_key": bool(api_key_plain),
            "has_api_secret": bool(api_secret_plain),
        },
        is_aggregator=doc.get("is_aggregator", False),
        aggregator_type=agg_enum,
        model_name_format=doc.get("model_name_format"),
        created_at=(
            doc.get("created_at", datetime.now(timezone.utc)).isoformat()
            if doc.get("created_at")
            else None
        ),
        updated_at=(
            doc.get("updated_at", datetime.now(timezone.utc)).isoformat()
            if doc.get("updated_at")
            else None
        ),
    )


class LLMProviderService:
    """LLM 厂家管理服务"""

    async def _get_collection(self) -> Any:
        return mongodb.get_collection(COLLECTION_NAME)

    async def list_providers(self) -> List[LLMProviderResponse]:
        """获取所有厂家"""
        collection = await self._get_collection()
        cursor = collection.find({}).sort("created_at", 1)
        docs = await cursor.to_list(length=None)
        return [_doc_to_response(doc) for doc in docs]

    async def get_provider(self, provider_id: str) -> Optional[LLMProviderResponse]:
        """获取单个厂家"""
        collection = await self._get_collection()
        try:
            doc = await collection.find_one({"_id": ObjectId(provider_id)})
        except Exception:
            doc = await collection.find_one({"name": provider_id})
        if not doc:
            return None
        return _doc_to_response(doc)

    async def get_provider_with_credentials(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """获取厂家完整凭证（内部使用）"""
        collection = await self._get_collection()
        try:
            doc = await collection.find_one({"_id": ObjectId(provider_id)})
        except Exception:
            doc = await collection.find_one({"name": provider_id})
        if not doc:
            return None

        api_key_encrypted = doc.get("api_key", "")
        api_key = ""
        if api_key_encrypted:
            try:
                from core.security.encryption import is_encrypted

                if is_encrypted(api_key_encrypted):
                    api_key = decrypt_sensitive_data(api_key_encrypted)
                else:
                    api_key = api_key_encrypted
            except Exception:
                api_key = ""

        doc["api_key_decrypted"] = api_key
        return dict(doc)

    async def create_provider(self, data: LLMProviderCreateRequest) -> str:
        """创建厂家，返回 ID"""
        collection = await self._get_collection()

        # 检查 name 是否重复
        existing = await collection.find_one({"name": data.name})
        if existing:
            raise ValueError(f"厂家标识 '{data.name}' 已存在")

        now = datetime.now(timezone.utc)
        doc = {
            "name": data.name,
            "display_name": data.display_name,
            "description": data.description,
            "website": data.website,
            "api_doc_url": data.api_doc_url,
            "logo_url": data.logo_url,
            "is_active": data.is_active,
            "supported_features": [f.value for f in data.supported_features],
            "default_base_url": data.default_base_url,
            "api_key": encrypt_sensitive_data(data.api_key) if data.api_key else "",
            "api_secret": encrypt_sensitive_data(data.api_secret) if data.api_secret else "",
            "is_aggregator": data.is_aggregator,
            "aggregator_type": data.aggregator_type.value if data.aggregator_type else None,
            "model_name_format": data.model_name_format,
            "created_at": now,
            "updated_at": now,
        }

        result = await collection.insert_one(doc)
        return str(result.inserted_id)

    async def update_provider(self, provider_id: str, data: LLMProviderUpdateRequest) -> bool:
        """更新厂家"""
        collection = await self._get_collection()

        update_fields: Dict = {"updated_at": datetime.now(timezone.utc)}

        for field_name in [
            "name",
            "display_name",
            "description",
            "website",
            "api_doc_url",
            "logo_url",
            "is_active",
            "default_base_url",
            "is_aggregator",
            "model_name_format",
        ]:
            val = getattr(data, field_name, None)
            if val is not None:
                update_fields[field_name] = val

        if data.supported_features is not None:
            update_fields["supported_features"] = [f.value for f in data.supported_features]

        if data.api_key is not None:
            update_fields["api_key"] = encrypt_sensitive_data(data.api_key)

        if data.api_secret is not None:
            update_fields["api_secret"] = encrypt_sensitive_data(data.api_secret)

        if data.aggregator_type is not None:
            update_fields["aggregator_type"] = data.aggregator_type.value

        try:
            result = await collection.update_one(
                {"_id": ObjectId(provider_id)},
                {"$set": update_fields},
            )
        except Exception:
            result = await collection.update_one(
                {"name": provider_id},
                {"$set": update_fields},
            )

        return bool(result.modified_count > 0 or result.matched_count > 0)

    async def toggle_provider(self, provider_id: str, is_active: bool) -> bool:
        """切换厂家启用状态"""
        collection = await self._get_collection()
        try:
            result = await collection.update_one(
                {"_id": ObjectId(provider_id)},
                {"$set": {"is_active": is_active, "updated_at": datetime.now(timezone.utc)}},
            )
        except Exception:
            result = await collection.update_one(
                {"name": provider_id},
                {"$set": {"is_active": is_active, "updated_at": datetime.now(timezone.utc)}},
            )
        return bool(result.matched_count > 0)

    async def delete_provider(self, provider_id: str) -> bool:
        """删除厂家"""
        collection = await self._get_collection()
        try:
            result = await collection.delete_one({"_id": ObjectId(provider_id)})
        except Exception:
            result = await collection.delete_one({"name": provider_id})
        return bool(result.deleted_count > 0)

    async def test_connection(self, provider_id: str) -> Dict:
        """测试厂家 API 连接"""
        provider = await self.get_provider_with_credentials(provider_id)
        if not provider:
            return {"success": False, "message": "厂家不存在"}

        import httpx

        base_url = provider.get("default_base_url", "")
        api_key = provider.get("api_key_decrypted", "")

        if not base_url:
            return {"success": False, "message": "未配置 API Base URL"}

        if not api_key:
            return {"success": False, "message": "未配置 API Key"}

        import time

        start_time = time.time()
        try:
            # 尝试调用 /models 端点（OpenAI 兼容格式）
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                elapsed = int((time.time() - start_time) * 1000)

                if resp.status_code == 200:
                    return {
                        "success": True,
                        "message": f"连接成功 ({resp.status_code})",
                        "response_time": elapsed,
                    }
                return {
                    "success": False,
                    "message": f"API 返回状态码 {resp.status_code}",
                    "response_time": elapsed,
                    "details": {"status_code": resp.status_code},
                }
        except Exception as e:
            elapsed = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
                "response_time": elapsed,
            }

    async def fetch_models(self, provider_id: str) -> Dict:
        """从厂家 API 拉取可用模型列表"""
        provider = await self.get_provider_with_credentials(provider_id)
        if not provider:
            return {"success": False, "message": "厂家不存在", "models": []}

        import httpx

        base_url = provider.get("default_base_url", "")
        api_key = provider.get("api_key_decrypted", "")

        if not base_url or not api_key:
            return {"success": False, "message": "未配置 API Base URL 或 API Key", "models": []}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    body = resp.json()
                    raw_models = body.get("data", [])
                    models = []
                    for m in raw_models:
                        model_id = m.get("id", "")
                        if model_id:
                            models.append(
                                {
                                    "name": model_id,
                                    "display_name": m.get("name", model_id),
                                    "description": m.get("description", ""),
                                }
                            )
                    return {
                        "success": True,
                        "message": f"获取到 {len(models)} 个模型",
                        "models": models,
                    }
                return {
                    "success": False,
                    "message": f"API 返回状态码 {resp.status_code}",
                    "models": [],
                }
        except Exception as e:
            return {"success": False, "message": f"获取失败: {str(e)}", "models": []}

    async def migrate_from_env(self) -> MigrateEnvResult:
        """将环境变量配置迁移到 DB"""
        migrated = 0
        skipped = 0

        env_mappings = [
            ("ZHIPU_API_KEY", "zhipu", "智谱AI", "https://open.bigmodel.cn/api/paas/v4"),
            ("DEEPSEEK_API_KEY", "deepseek", "DeepSeek", "https://api.deepseek.com/v1"),
            ("OPENAI_API_KEY", "openai", "OpenAI", "https://api.openai.com/v1"),
            (
                "QWEN_API_KEY",
                "qwen",
                "通义千问",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        ]

        for env_key, provider_name, display_name, default_url in env_mappings:
            api_key = os.getenv(env_key, "")
            if not api_key:
                skipped += 1
                continue

            try:
                await self.create_provider(
                    LLMProviderCreateRequest(  # type: ignore[call-arg]
                        name=provider_name,
                        display_name=display_name,
                        is_active=True,
                        default_base_url=default_url,
                        api_key=api_key,
                        supported_features=[SupportedFeature.CHAT, SupportedFeature.STREAMING],
                    )
                )
                migrated += 1
            except ValueError:
                # 已存在，跳过
                skipped += 1

        return MigrateEnvResult(
            success=True,
            message=f"迁移完成: {migrated} 个成功, {skipped} 个跳过",
            migrated_count=migrated,
            skipped_count=skipped,
        )

    async def init_aggregators(self) -> InitAggregatorsResult:
        """初始化聚合渠道厂家"""
        added = 0
        skipped = 0

        aggregators = [
            {
                "name": "302ai",
                "display_name": "302.AI",
                "default_base_url": "https://api.302.ai/v1",
                "aggregator_type": AggregatorType.AI302,
                "supported_features": [
                    SupportedFeature.CHAT,
                    SupportedFeature.STREAMING,
                    SupportedFeature.TOOL_CALLING,
                ],
            },
            {
                "name": "openrouter",
                "display_name": "OpenRouter",
                "default_base_url": "https://openrouter.ai/api/v1",
                "aggregator_type": AggregatorType.OPENROUTER,
                "supported_features": [
                    SupportedFeature.CHAT,
                    SupportedFeature.STREAMING,
                    SupportedFeature.TOOL_CALLING,
                    SupportedFeature.VISION,
                ],
            },
            {
                "name": "siliconflow",
                "display_name": "SiliconFlow",
                "default_base_url": "https://api.siliconflow.cn/v1",
                "aggregator_type": AggregatorType.SILICONFLOW,
                "supported_features": [
                    SupportedFeature.CHAT,
                    SupportedFeature.STREAMING,
                    SupportedFeature.EMBEDDING,
                ],
            },
        ]

        for agg in aggregators:
            try:
                await self.create_provider(
                    LLMProviderCreateRequest(  # type: ignore[call-arg]
                        name=agg["name"],
                        display_name=agg["display_name"],
                        is_active=True,
                        is_aggregator=True,
                        aggregator_type=agg["aggregator_type"],
                        default_base_url=agg["default_base_url"],
                        supported_features=agg["supported_features"],
                    )
                )
                added += 1
            except ValueError:
                skipped += 1

        return InitAggregatorsResult(
            success=True,
            message=f"初始化完成: {added} 个新增, {skipped} 个已存在",
            added_count=added,
            skipped_count=skipped,
        )


# 全局单例
_llm_provider_service: Optional[LLMProviderService] = None


def get_llm_provider_service() -> LLMProviderService:
    """获取 LLM 厂家管理服务单例"""
    global _llm_provider_service
    if _llm_provider_service is None:
        _llm_provider_service = LLMProviderService()
    return _llm_provider_service
