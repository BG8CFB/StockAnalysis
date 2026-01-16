"""
AI 统一服务

提供统一的 AI 调用接口，内部使用 LangChain 实现。
支持聊天补全、流式输出、连接验证、价格计算和使用统计等功能。
"""

import logging
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from .concurrency import ConcurrencyManager
from .langchain.adapter import LangChainAdapter
from .pricing import get_pricing_service
from .types import AIMessage, AIResponse, AIStreamChunk, AITool, create_message
from .usage import get_usage_service

logger = logging.getLogger(__name__)


class AIService:
    """AI 统一服务

    提供统一的 AI 调用接口，内部使用 LangChain 实现。
    """

    def __init__(self):
        self.concurrency_manager = ConcurrencyManager()
        self._model_cache: Dict[str, BaseChatModel] = {}
        self._config_cache: Dict[str, Dict] = {}

        # 服务组件
        self._pricing_service = get_pricing_service()
        self._usage_service = get_usage_service()

        # 是否启用使用统计（默认启用）
        self._enable_usage_tracking = True

    # 配置服务将在实际运行时注入
    _config_service = None

    @classmethod
    def set_config_service(cls, config_service):
        """设置配置服务"""
        cls._config_service = config_service

    def set_usage_tracking_enabled(self, enabled: bool):
        """设置是否启用使用统计"""
        self._enable_usage_tracking = enabled

    async def chat_completion(
        self,
        user_id: str,
        messages: List[AIMessage],
        model_id: Optional[str] = None,
        tools: Optional[List[AITool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_id: Optional[str] = None,
        phase: Optional[str] = None,
        agent_slug: Optional[str] = None,
        **kwargs,
    ) -> AIResponse:
        """
        聊天补全

        Args:
            user_id: 用户 ID
            messages: 消息列表
            model_id: 模型 ID（可选，从配置获取）
            tools: 工具列表（可选）
            temperature: 温度参数（可选）
            max_tokens: 最大 token 数（可选）
            task_id: 任务 ID（可选，用于统计）
            phase: 阶段（可选，用于统计）
            agent_slug: 智能体标识（可选，用于统计）
            **kwargs: 其他参数

        Returns:
            AIResponse 响应对象
        """
        # 获取模型配置
        config = await self._get_model_config(user_id, model_id)

        # 获取并发令牌
        async with self.concurrency_manager.acquire(config, user_id):
            # 创建或获取 ChatModel
            chat_model = await self._get_or_create_model(config)

            # 转换消息格式
            lc_messages = [msg.to_langchain() for msg in messages]

            # 构建调用参数
            invoke_kwargs: Dict[str, Any] = {}

            # 添加工具（如果有）
            if tools:
                invoke_kwargs["tools"] = [tool.to_langchain_format() for tool in tools]

            # 调用模型
            logger.debug(
                f"AI 调用: user={user_id}, model={config['model_id']}, "
                f"messages={len(lc_messages)}, tools={len(tools) if tools else 0}"
            )

            response = await chat_model.ainvoke(lc_messages, **invoke_kwargs)

            # 解析响应
            parsed_response = self._parse_response(response, config)

            # 记录使用情况和成本（异步，不阻塞响应）
            if self._enable_usage_tracking:
                try:
                    await self._usage_service.record_from_response(
                        user_id=user_id,
                        model_id=config["model_id"],
                        model_name=config.get("model_name", config["model_id"]),
                        response=response,
                        task_id=task_id,
                        phase=phase,
                        agent_slug=agent_slug,
                        tool_calls=parsed_response.tool_calls,
                    )
                except Exception as e:
                    logger.warning(f"记录使用统计失败: {e}")

            return parsed_response

    async def stream_completion(
        self, user_id: str, messages: List[AIMessage], model_id: Optional[str] = None, **kwargs
    ) -> AsyncIterator[AIStreamChunk]:
        """
        流式聊天补全

        Args:
            user_id: 用户 ID
            messages: 消息列表
            model_id: 模型 ID（可选）
            **kwargs: 其他参数

        Yields:
            AIStreamChunk 流式响应块
        """
        # 获取模型配置
        config = await self._get_model_config(user_id, model_id)

        # 获取并发令牌
        async with self.concurrency_manager.acquire(config, user_id):
            # 创建或获取 ChatModel
            chat_model = await self._get_or_create_model(config)

            # 转换消息格式
            lc_messages = [msg.to_langchain() for msg in messages]

            logger.debug(
                f"AI 流式调用: user={user_id}, model={config['model_id']}, "
                f"messages={len(lc_messages)}"
            )

            # 流式调用
            async for chunk in chat_model.astream(lc_messages):
                # 提取思考内容（如果存在）
                reasoning_content = None
                if (
                    hasattr(chunk, "additional_kwargs")
                    and "reasoning_content" in chunk.additional_kwargs
                ):
                    reasoning_content = chunk.additional_kwargs["reasoning_content"]

                yield AIStreamChunk(
                    content=chunk.content or "",
                    reasoning_content=reasoning_content,
                    is_complete=False,
                )

            # 发送完成标记
            yield AIStreamChunk(content="", is_complete=True)

    async def validate_connection(self, user_id: str, model_id: Optional[str] = None) -> bool:
        """
        验证连接

        Args:
            user_id: 用户 ID
            model_id: 模型 ID（可选）

        Returns:
            连接是否成功
        """
        try:
            messages = [create_message(role="user", content="test")]
            await self.chat_completion(user_id, messages, model_id, max_tokens=1)
            logger.info(f"连接验证成功: user={user_id}, model={model_id}")
            return True
        except Exception as e:
            logger.warning(f"连接验证失败: user={user_id}, model={model_id}, error={e}")
            return False

    async def _get_model_config(self, user_id: str, model_id: Optional[str]) -> Dict:
        """获取模型配置"""
        # 优先从环境变量读取配置（用于测试）
        import os

        env_api_key = os.getenv("ZHIPU_API_KEY", "")
        env_api_base = os.getenv("ZHIPU_API_BASE", "")
        env_model = os.getenv("ZHIPU_MODEL", "")

        if env_api_key:
            platform = "zhipu_coding" if "coding" in env_api_base.lower() else "zhipu"
            return {
                "model_id": env_model or model_id or "glm-4.7",
                "platform": platform,
                "api_key": env_api_key,
                "api_base_url": env_api_base or "https://open.bigmodel.cn/api/coding/paas/v4",
                "temperature": 0.5,
                "timeout_seconds": 120,
                "max_retries": 3,
                "thinking_enabled": True,
            }

        # 如果有配置服务，使用配置服务
        if self._config_service:
            if model_id:
                config = await self._config_service.get_model(model_id, user_id)
                if config:
                    return self._config_to_dict(config)

            # 尝试获取用户默认配置
            config = await self._config_service.get_user_default(user_id)
            if config:
                return self._config_to_dict(config)

            # 尝试获取系统默认配置
            config = await self._config_service.get_system_default()
            if config:
                return self._config_to_dict(config)

        # 返回默认配置（用于测试）
        return {
            "model_id": model_id or "glm-4.7",
            "platform": "zhipu",
            "api_key": "",
            "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
            "temperature": 0.5,
            "timeout_seconds": 60,
            "max_retries": 3,
            "thinking_enabled": True,
        }

    def _config_to_dict(self, config) -> Dict:
        """将配置对象转换为字典"""
        if hasattr(config, "model_dump"):
            return config.model_dump()
        elif hasattr(config, "dict"):
            return config.dict()
        else:
            # 假设是字典
            return dict(config)

    async def _get_or_create_model(self, config: Dict) -> BaseChatModel:
        """获取或创建 ChatModel 实例"""
        cache_key = (
            f"{config.get('platform', 'unknown')}:"
            f"{config.get('model_id', 'unknown')}:"
            f"{str(config.get('api_key', ''))[:8]}"
        )

        if cache_key not in self._model_cache:
            logger.debug(f"创建新的 ChatModel: {cache_key}")
            self._model_cache[cache_key] = LangChainAdapter.create_chat_model(
                model_id=config["model_id"],
                api_key=config.get("api_key", ""),
                platform=config.get("platform", "zhipu"),
                api_base_url=config.get("api_base_url"),
                temperature=config.get("temperature", 0.5),
                timeout_seconds=config.get("timeout_seconds", 60),
                max_retries=config.get("max_retries", 3),
                thinking_enabled=config.get("thinking_enabled", False),
            )

        return self._model_cache[cache_key]

    def _parse_response(self, response: Any, config: Dict) -> AIResponse:
        """解析 LangChain 响应"""
        # 获取内容
        content = response.content or ""

        # 解析思考内容（GLM-4.7）
        reasoning_content = None
        thinking_tokens = None

        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if "reasoning_content" in metadata:
                reasoning_content = metadata["reasoning_content"]
            if "reasoning_tokens" in metadata:
                thinking_tokens = metadata["reasoning_tokens"]

        # 解析工具调用
        tool_calls = None
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = [
                {
                    "id": tc.id or "",
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.args,
                    },
                }
                for tc in response.tool_calls
            ]

        # 解析 usage
        usage = None
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            if usage:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        # 计算成本（用于统计，当前不返回）
        _cost = None
        if total_tokens > 0:
            try:
                _cost = self._pricing_service.calculate_cost(
                    model_id=config["model_id"],
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    thinking_tokens=thinking_tokens or 0,
                )
            except Exception as e:
                logger.warning(f"计算成本失败: {e}")

        # 解析原始响应
        raw_response = None
        if hasattr(response, "response_metadata"):
            raw_response = response.response_metadata

        return AIResponse(
            content=content,
            reasoning_content=reasoning_content,
            thinking_tokens=thinking_tokens,
            usage=usage,
            tool_calls=tool_calls,
            raw_response=raw_response,
        )

    async def get_user_usage_stats(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取用户使用统计

        Args:
            user_id: 用户 ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            统计信息
        """
        return await self._usage_service.get_user_stats(user_id, start_date, end_date)

    async def get_task_usage_stats(
        self,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        获取任务使用统计

        Args:
            task_id: 任务 ID

        Returns:
            统计信息
        """
        return await self._usage_service.get_task_stats(task_id)

    def get_concurrency_stats(self) -> Dict:
        """获取并发统计"""
        return self.concurrency_manager.get_stats()

    def clear_user_cache(self, user_id: str):
        """
        清除用户相关缓存

        Args:
            user_id: 用户 ID
        """
        # 清除并发管理的用户信号量
        self.concurrency_manager.clear_user_semaphore(user_id)

        # 清除模型缓存中该用户的配置缓存
        keys_to_remove = [k for k in self._config_cache.keys() if k.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self._config_cache[key]

        logger.debug(f"清除用户缓存: user={user_id}")

    def get_model(self, model_id: str, user_id: str = "system") -> BaseChatModel:
        """
        获取 LangChain ChatModel 实例

        Args:
            model_id: 模型 ID
            user_id: 用户 ID（默认为 system）

        Returns:
            LangChain ChatModel 实例

        Note:
            这是一个同步方法，用于简化 scheduler 等需要直接获取模型实例的场景。
        """
        import asyncio
        import os

        # 优先从环境变量读取配置（始终优先）
        env_api_key = os.getenv("ZHIPU_API_KEY", "")
        env_api_base = os.getenv("ZHIPU_API_BASE", "")
        env_model = os.getenv("ZHIPU_MODEL", "")

        if env_api_key:
            platform = "zhipu_coding" if "coding" in env_api_base.lower() else "zhipu"
            config = {
                "model_id": env_model or model_id or "glm-4.7",
                "platform": platform,
                "api_key": env_api_key,
                "api_base_url": env_api_base or "https://open.bigmodel.cn/api/coding/paas/v4",
                "temperature": 0.5,
                "timeout_seconds": 120,
                "max_retries": 3,
                "thinking_enabled": True,
            }
            return self._create_model_sync(config)

        # 尝试获取模型配置
        config = None
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在运行中的事件循环，使用默认配置
                config = {
                    "model_id": model_id,
                    "platform": "zhipu",
                    "api_key": "",
                    "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
                    "temperature": 0.5,
                    "timeout_seconds": 60,
                    "max_retries": 3,
                    "thinking_enabled": True,
                }
            else:
                config = loop.run_until_complete(self._get_model_config(user_id, model_id))
        except RuntimeError:
            # 没有事件循环，创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                config = loop.run_until_complete(self._get_model_config(user_id, model_id))
            finally:
                loop.close()

        # 如果获取配置失败，使用默认配置
        if not config:
            config = {
                "model_id": model_id,
                "platform": "zhipu",
                "api_key": "",
                "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
                "temperature": 0.5,
                "timeout_seconds": 60,
                "max_retries": 3,
                "thinking_enabled": True,
            }

        # 创建模型实例
        return self._create_model_sync(config)

    def _create_model_sync(self, config: Dict) -> BaseChatModel:
        """同步创建 ChatModel 实例"""
        from .langchain.adapter import LangChainAdapter

        return LangChainAdapter.create_chat_model(
            model_id=config["model_id"],
            api_key=config.get("api_key", ""),
            platform=config.get("platform", "zhipu"),
            api_base_url=config.get("api_base_url"),
            temperature=config.get("temperature", 0.5),
            timeout_seconds=config.get("timeout_seconds", 60),
            max_retries=config.get("max_retries", 3),
            thinking_enabled=config.get("thinking_enabled", False),
        )


# =============================================================================
# 全局单例
# =============================================================================

_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取 AI 服务单例"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


def set_ai_service(service: AIService):
    """设置 AI 服务实例（用于测试）"""
    global _ai_service
    _ai_service = service
