"""
AI 模型配置管理服务

提供 AI 模型的 CRUD 操作和连接测试功能。
"""

import logging
import asyncio
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.llm.openai_compat import OpenAICompatProvider
from modules.trading_agents.llm.provider import LLMProvider
from modules.trading_agents.schemas import (
    AIModelConfigCreate,
    AIModelConfigUpdate,
    AIModelConfigResponse,
    AIModelTestRequest,
    ConnectionTestResponse,
    ModelProviderEnum,
)

logger = logging.getLogger(__name__)


class AIModelService:
    """
    AI 模型配置管理服务

    提供模型的创建、更新、删除、查询和测试功能。
    """

    COLLECTION_NAME = "ai_models"

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
        request: AIModelConfigCreate
    ) -> AIModelConfigResponse:
        """
        创建 AI 模型配置

        Args:
            user_id: 用户 ID
            request: 创建请求

        Returns:
            创建的模型配置
        """
        collection = await self._get_collection()

        # 系统级配置需要管理员权限（在前端验证）
        # 创建文档
        doc = {
            "name": request.name,
            "provider": request.provider.value,
            "api_base_url": request.api_base_url,
            "api_key": request.api_key,  # 明文存储，日志脱敏
            "model_id": request.model_id,
            "max_concurrency": request.max_concurrency,
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
            model_id: 模型 ID
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            模型配置或 None
        """
        collection = await self._get_collection()

        try:
            object_id = ObjectId(model_id)
        except Exception:
            return None

        doc = await collection.find_one({"_id": object_id})

        if not doc:
            return None

        # 权限检查
        if not is_admin and doc.get("is_system") and doc.get("owner_id") != user_id:
            return None

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
        if request.provider is not None:
            update_data["provider"] = request.provider.value
        if request.api_base_url is not None:
            update_data["api_base_url"] = request.api_base_url
        if request.api_key is not None:
            update_data["api_key"] = request.api_key
        if request.model_id is not None:
            update_data["model_id"] = request.model_id
        if request.max_concurrency is not None:
            update_data["max_concurrency"] = request.max_concurrency
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
            from modules.trading_agents.llm.provider import Message
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
