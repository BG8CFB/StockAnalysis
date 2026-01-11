"""
AI 模型配置管理服务

提供 AI 模型的 CRUD 操作和连接测试功能。
API Key 使用加密存储保护。
"""

import logging
import asyncio
import time
from datetime import datetime
from typing import List, Optional, Dict
from bson import ObjectId

from core.db.mongodb import mongodb
from core.ai.llm.openai_compat import OpenAICompatProvider
from core.ai.llm.provider import LLMProvider
from core.ai.model.schemas import (
    AIModelConfigCreate,
    AIModelConfigUpdate,
    AIModelConfigResponse,
    AIModelTestRequest,
    ConnectionTestResponse,
    ListModelsRequest,
    ListModelsResponse,
    ModelInfo,
    PlatformTypeEnum,
    PresetPlatformEnum,
)
from core.security.encryption import encrypt_sensitive_data

logger = logging.getLogger(__name__)


class AIModelService:
    """
    AI 模型配置管理服务

    提供模型的创建、更新、删除、查询和测试功能。
    """

    COLLECTION_NAME = "ai_model_configs"

    def __init__(self):
        """初始化服务"""
        self._db = None
        self._model_cache: Dict[str, LLMProvider] = {}

    async def _get_collection(self):
        """获取数据库集合"""
        return mongodb.get_collection(self.COLLECTION_NAME)

    # ========================================================================
    # CRUD 操作
    # ========================================================================

    async def create_model(
        self,
        user_id: str,
        request: AIModelConfigCreate,
        is_admin: bool = False
    ) -> AIModelConfigResponse:
        """
        创建 AI 模型配置

        Args:
            user_id: 用户 ID
            request: 创建请求
            is_admin: 是否为管理员（用于权限检查）

        Returns:
            创建的模型配置
        """
        collection = await self._get_collection()

        # 权限检查：只有管理员可以创建系统级模型
        if request.is_system and not is_admin:
            raise PermissionError("只有管理员可以创建系统模型（公共AI模型）")

        # 加密 API Key
        encrypted_api_key = encrypt_sensitive_data(request.api_key)

        # 创建文档
        doc = {
            "name": request.name,
            "platform_type": request.platform_type.value,
            "platform_name": request.platform_name.value if request.platform_name else None,
            "provider": request.provider.value if request.provider else None,
            "api_base_url": request.api_base_url,
            "api_key": encrypted_api_key,  # 加密存储
            "model_id": request.model_id,
            "custom_headers": request.custom_headers,
            "max_concurrency": request.max_concurrency,
            "task_concurrency": request.task_concurrency,
            "batch_concurrency": request.batch_concurrency,
            "timeout_seconds": request.timeout_seconds,
            "temperature": request.temperature,
            "enabled": request.enabled,
            "is_system": request.is_system,
            "owner_id": None if request.is_system else user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # 插入数据库
        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(
            f"创建 AI 模型配置: name={request.name}, "
            f"provider={request.provider}, user={user_id}, "
            f"is_system={request.is_system}"
        )

        return AIModelConfigResponse.from_db(doc)

    async def get_model(
        self,
        model_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> Optional[AIModelConfigResponse]:
        """
        获取单个模型配置

        Args:
            model_id: 模型 ID（可以是 MongoDB _id 或 model_id 字段）
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            模型配置或 None
        """
        collection = await self._get_collection()

        # 先尝试按 model_id 字段查找（模型的标识符，如 "glm-4.7"）
        doc = await collection.find_one({"model_id": model_id, "enabled": True})

        # 如果没找到，尝试按 MongoDB _id 查找
        if not doc:
            try:
                object_id = ObjectId(model_id)
                doc = await collection.find_one({"_id": object_id})
            except Exception:
                return None

        if not doc:
            return None

        # 权限检查
        # 系统模型对所有用户可见（is_system=True 的模型）
        # 用户私有模型只能被所有者访问
        if not is_admin and not doc.get("is_system") and doc.get("owner_id") != user_id:
            return None

        return AIModelConfigResponse.from_db(doc)

    async def list_models(
        self,
        user_id: str,
        is_admin: bool = False,
        include_system: bool = True
    ) -> Dict[str, List[AIModelConfigResponse]]:
        """
        列出模型配置

        Args:
            user_id: 用户 ID
            is_admin: 是否为管理员
            include_system: 是否包含系统级模型

        Returns:
            {"system": [...], "user": [...]}
        """
        collection = await self._get_collection()

        # 构建查询条件
        query = {"enabled": True}

        if is_admin:
            # 管理员查看所有模型
            cursor = collection.find(query).sort("created_at", -1)
            all_models = [AIModelConfigResponse.from_db(doc) async for doc in cursor]
            return {
                "system": [m for m in all_models if m.is_system],
                "user": [m for m in all_models if not m.is_system],
            }
        else:
            # 普通用户只能查看系统级模型和自己的模型
            system_models = []
            user_models = []

            if include_system:
                system_cursor = collection.find({
                    **query,
                    "is_system": True,
                }).sort("created_at", -1)
                system_models = [AIModelConfigResponse.from_db(doc) async for doc in system_cursor]

            user_cursor = collection.find({
                **query,
                "is_system": False,
                "owner_id": user_id,
            }).sort("created_at", -1)
            user_models = [AIModelConfigResponse.from_db(doc) async for doc in user_cursor]

            return {
                "system": system_models,
                "user": user_models,
            }

    async def get_default_model(
        self,
        user_id: Optional[str] = None
    ) -> Optional[AIModelConfigResponse]:
        """
        获取默认的 AI 模型配置

        优先返回第一个启用的系统级模型，如果没有则返回用户的第一个模型。

        Args:
            user_id: 用户 ID（可选）

        Returns:
            默认模型配置或 None
        """
        collection = await self._get_collection()

        # 先尝试获取系统级模型
        system_model = await collection.find_one({
            "enabled": True,
            "is_system": True,
        })
        if system_model:
            return AIModelConfigResponse.from_db(system_model)

        # 如果没有系统级模型，尝试获取用户的模型
        if user_id:
            user_model = await collection.find_one({
                "enabled": True,
                "is_system": False,
                "owner_id": user_id,
            })
            if user_model:
                return AIModelConfigResponse.from_db(user_model)

        # 没有可用的模型
        logger.warning(f"未找到可用的默认模型: user_id={user_id}")
        return None

    async def update_model(
        self,
        model_id: str,
        user_id: str,
        request: AIModelConfigUpdate,
        is_admin: bool = False
    ) -> Optional[AIModelConfigResponse]:
        """
        更新模型配置

        Args:
            model_id: 模型 ID
            user_id: 用户 ID
            request: 更新请求
            is_admin: 是否为管理员

        Returns:
            更新后的模型配置或 None
        """
        collection = await self._get_collection()

        try:
            object_id = ObjectId(model_id)
        except Exception:
            return None

        # 获取原配置
        doc = await collection.find_one({"_id": object_id})
        if not doc:
            return None

        # 权限检查
        if not is_admin and doc.get("owner_id") != user_id:
            return None

        # 构建更新数据
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.platform_type is not None:
            update_data["platform_type"] = request.platform_type.value
        if request.platform_name is not None:
            update_data["platform_name"] = request.platform_name.value
        if request.provider is not None:
            update_data["provider"] = request.provider.value
        if request.api_base_url is not None:
            update_data["api_base_url"] = request.api_base_url
        if request.api_key is not None:
            # 加密 API Key 后存储
            update_data["api_key"] = encrypt_sensitive_data(request.api_key)
        if request.model_id is not None:
            update_data["model_id"] = request.model_id
        if request.custom_headers is not None:
            update_data["custom_headers"] = request.custom_headers
        if request.max_concurrency is not None:
            update_data["max_concurrency"] = request.max_concurrency
        if request.task_concurrency is not None:
            update_data["task_concurrency"] = request.task_concurrency
        if request.batch_concurrency is not None:
            update_data["batch_concurrency"] = request.batch_concurrency
        if request.timeout_seconds is not None:
            update_data["timeout_seconds"] = request.timeout_seconds
        if request.temperature is not None:
            update_data["temperature"] = request.temperature
        if request.enabled is not None:
            update_data["enabled"] = request.enabled

        update_data["updated_at"] = datetime.utcnow()

        # 执行更新
        await collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )

        # 清除缓存
        if model_id in self._model_cache:
            del self._model_cache[model_id]

        # 获取更新后的配置
        updated_doc = await collection.find_one({"_id": object_id})

        logger.info(f"更新 AI 模型配置: model_id={model_id}, user={user_id}")

        return AIModelConfigResponse.from_db(updated_doc)

    async def delete_model(
        self,
        model_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> bool:
        """
        删除模型配置

        Args:
            model_id: 模型 ID
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            是否删除成功
        """
        collection = await self._get_collection()

        try:
            object_id = ObjectId(model_id)
        except Exception:
            return False

        # 获取配置
        doc = await collection.find_one({"_id": object_id})
        if not doc:
            return False

        # 权限检查
        if not is_admin and doc.get("owner_id") != user_id:
            return False

        # TODO: 检查是否有进行中的任务使用该模型

        # 删除配置
        result = await collection.delete_one({"_id": object_id})

        # 清除缓存
        if model_id in self._model_cache:
            del self._model_cache[model_id]

        logger.info(f"删除 AI 模型配置: model_id={model_id}, user={user_id}")

        return result.deleted_count > 0

    # ========================================================================
    # 连接测试
    # ========================================================================

    async def test_model_connection(
        self,
        request: AIModelTestRequest
    ) -> ConnectionTestResponse:
        """
        测试 AI 模型连接

        Args:
            request: 测试请求

        Returns:
            测试结果
        """
        start_time = time.time()

        try:
            # 创建 LLM Provider
            provider = OpenAICompatProvider(
                api_base_url=request.api_base_url,
                api_key=request.api_key,
                model_id=request.model_id,
                timeout_seconds=request.timeout_seconds,
            )

            # 发送测试请求
            from core.ai.llm.provider import Message
            test_messages = [
                Message(role="user", content="Hi")
            ]

            await provider.chat_completion(
                messages=test_messages,
                temperature=0.1,
                max_tokens=5,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"模型连接测试成功: provider={request.api_base_url}, "
                f"model={request.model_id}, latency={latency_ms}ms"
            )

            return ConnectionTestResponse(
                success=True,
                message="连接测试成功",
                latency_ms=latency_ms,
            )

        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"模型连接测试超时: model={request.model_id}")
            return ConnectionTestResponse(
                success=False,
                message=f"连接测试超时（超过 {request.timeout_seconds} 秒）",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"模型连接测试失败: model={request.model_id}, error={e}")
            return ConnectionTestResponse(
                success=False,
                message=f"连接测试失败: {str(e)}",
                latency_ms=latency_ms,
            )

    async def list_available_models(
        self,
        request: ListModelsRequest
    ) -> ListModelsResponse:
        """
        获取可用的模型列表

        尝试从 API 获取，失败时使用预设模型列表作为兜底。

        Args:
            request: 获取模型列表请求

        Returns:
            模型列表响应
        """
        import httpx

        # 如果是预设平台，先尝试从 API 获取
        if request.platform_type == PlatformTypeEnum.PRESET and request.platform_name:
            # 预设平台的模型列表配置
            preset_platforms_models = {
                PresetPlatformEnum.OPENAI: [
                    "gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini",
                    "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"
                ],
                PresetPlatformEnum.ANTHROPIC: [
                    "claude-sonnet-4-5-20250514", "claude-opus-4-20250514",
                    "claude-3-5-haiku-20241022", "claude-3-haiku-20240307"
                ],
                PresetPlatformEnum.AZURE_OPENAI: [
                    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-35-turbo"
                ],
                PresetPlatformEnum.BAIDU: [
                    "ernie-4.0-8k", "ernie-3.5-8k", "ernie-speed-8k", "ernie-lite-8k"
                ],
                PresetPlatformEnum.ALIBABA: [
                    "qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"
                ],
                PresetPlatformEnum.TENCENT: [
                    "hunyuan-pro", "hunyuan-standard", "hunyuan-lite"
                ],
                PresetPlatformEnum.DEEPSEEK: [
                    "deepseek-chat", "deepseek-coder"
                ],
                PresetPlatformEnum.MOONSHOT: [
                    "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"
                ],
                PresetPlatformEnum.ZHIPU: [
                    "glm-4-plus",
                    "glm-4-plus-coder",
                    "glm-4-0520",
                    "glm-4-0520-coder",
                    "glm-4-air",
                    "glm-4-flash"
                ],
                PresetPlatformEnum.ZHIPU_CODING: [
                    "glm-4.7"  # 编程套餐专用模型
                ],
            }

            fallback_models = preset_platforms_models.get(request.platform_name, [])

            # 只有支持列出模型的平台才尝试 API 调用
            support_list_models_platforms = [
                PresetPlatformEnum.OPENAI,
                PresetPlatformEnum.AZURE_OPENAI,
                PresetPlatformEnum.ALIBABA,
                PresetPlatformEnum.DEEPSEEK,
                PresetPlatformEnum.MOONSHOT,
            ]

            if request.platform_name in support_list_models_platforms:
                try:
                    # 构建请求头
                    headers = {
                        "Authorization": f"Bearer {request.api_key}",
                        **request.custom_headers
                    }

                    # 构建模型列表端点 URL
                    models_url = f"{request.api_base_url.rstrip('/')}/models"

                    # 发送请求
                    async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                        response = await client.get(models_url, headers=headers)
                        response.raise_for_status()
                        data = response.json()

                        # 解析响应
                        models = []
                        if "data" in data:
                            for item in data["data"]:
                                models.append(ModelInfo(
                                    id=item.get("id", ""),
                                    name=item.get("id", ""),
                                    created_at=item.get("created"),
                                    owned_by=item.get("owned_by")
                                ))

                        logger.info(
                            f"成功从 API 获取模型列表: platform={request.platform_name}, "
                            f"count={len(models)}"
                        )

                        return ListModelsResponse(
                            success=True,
                            message=f"成功获取 {len(models)} 个模型",
                            models=models,
                            is_from_api=True,
                            fallback_used=False
                        )

                except httpx.TimeoutException:
                    logger.warning(f"获取模型列表超时: platform={request.platform_name}")
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"获取模型列表 HTTP 错误: platform={request.platform_name}, "
                        f"status={e.response.status_code}"
                    )
                except Exception as e:
                    logger.warning(f"获取模型列表失败: platform={request.platform_name}, error={e}")

            # API 调用失败，使用预设列表作为兜底
            logger.info(f"使用预设模型列表作为兜底: platform={request.platform_name}")
            models = [
                ModelInfo(
                    id=model_id,
                    name=model_id,
                    created_at=None,
                    owned_by=None
                ) for model_id in fallback_models
            ]
            return ListModelsResponse(
                success=True,
                message=f"API 获取失败，使用预设列表（{len(models)} 个模型）",
                models=models,
                is_from_api=False,
                fallback_used=True
            )

        # 自定义平台，直接返回空列表（用户手动输入）
        return ListModelsResponse(
            success=True,
            message="自定义平台请手动输入模型 ID",
            models=[],
            is_from_api=False,
            fallback_used=False
        )

    # ========================================================================
    # LLM Provider 获取
    # ========================================================================

    async def get_llm_provider(
        self,
        model_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> Optional[LLMProvider]:
        """
        获取 LLM Provider 实例

        Args:
            model_id: 模型配置 ID
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            LLM Provider 实例或 None
        """
        # 检查缓存
        if model_id in self._model_cache:
            return self._model_cache[model_id]

        # 获取模型配置
        model_config = await self.get_model(model_id, user_id, is_admin)
        if not model_config:
            return None

        # 创建 Provider
        provider = OpenAICompatProvider(
            api_base_url=model_config.api_base_url,
            api_key=model_config.api_key,
            model_id=model_config.model_id,
            timeout_seconds=model_config.timeout_seconds,
            temperature=model_config.temperature,
        )

        # 缓存
        self._model_cache[model_id] = provider

        return provider


# =============================================================================
# 全局服务实例
# =============================================================================

_ai_model_service: Optional[AIModelService] = None


def get_model_service() -> AIModelService:
    """获取全局 AI 模型服务实例"""
    global _ai_model_service
    if _ai_model_service is None:
        _ai_model_service = AIModelService()
    return _ai_model_service
