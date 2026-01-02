"""
OpenAI 兼容 LLM Provider

支持 OpenAI 标准格式的 API 调用，兼容多种提供商（智谱、DeepSeek、Qwen、Ollama 等）。
"""

import asyncio
import logging
import time
import json
from typing import List, Dict, Any, Optional, AsyncGenerator

import httpx

from .provider import (
    LLMProvider,
    Message,
    Tool,
    ToolCall,
    ChatResponse,
    format_messages_for_logging,
    retry_on_failure,
)
from .thinking_adapter import ThinkingParameterAdapter
from .thinking_parser import ThinkingResponseParser
from core.ai.exceptions import ModelConnectionException

logger = logging.getLogger(__name__)


class OpenAICompatProvider(LLMProvider):
    """
    OpenAI 兼容 LLM Provider

    支持 OpenAI 标准格式的聊天 API，兼容多种提供商。
    """

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model_id: str,
        timeout_seconds: int = 60,
        temperature: float = 0.5,
        max_retries: int = 3,
    ):
        super().__init__(
            api_base_url=api_base_url,
            api_key=api_key,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            max_retries=max_retries,
        )
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=self.api_base_url,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        return self._client

    async def _close_client(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_enabled: bool = False,
        thinking_mode: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """
        聊天补全

        Args:
            messages: 消息列表
            tools: 可用工具列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            thinking_enabled: 是否启用思考模式
            thinking_mode: 思考模式类型
            budget_tokens: Token 预算（Claude）
            reasoning_effort: 推理级别
            **kwargs: 其他参数

        Returns:
            ChatResponse 对象
        """
        logger.debug(
            f"LLM 请求: model={self.model_id}, "
            f"messages={format_messages_for_logging(messages)}, "
            f"tools={len(tools) if tools else 0}, "
            f"thinking={thinking_enabled}"
        )

        async def _request():
            client = self._get_client()

            # 构建请求体
            payload = {
                "model": self.model_id,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                        **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                        **({"reasoning_content": msg.reasoning_content} if msg.reasoning_content else {}),
                    }
                    for msg in messages
                ],
                "temperature": self.get_temperature(temperature),
            }

            # 添加工具（如果有）
            if tools:
                payload["tools"] = [
                    {
                        "type": tool.type,
                        "function": tool.function,
                    }
                    for tool in tools
                ]

            # 添加 max_tokens（如果有）
            if max_tokens:
                payload["max_tokens"] = max_tokens

            # 适配思考参数
            thinking_params = ThinkingParameterAdapter.adapt(
                model_id=self.model_id,
                thinking_enabled=thinking_enabled,
                thinking_mode=thinking_mode,
                budget_tokens=budget_tokens,
                reasoning_effort=reasoning_effort
            )

            # 如果模型支持思考模式，添加思考参数
            if thinking_params:
                payload.update(thinking_params)
                logger.debug(f"已启用思考模式: {thinking_params}")

            # 添加其他 kwargs
            if kwargs:
                payload.update(kwargs)

            # 发送请求
            start_time = time.time()
            response = await client.post("/chat/completions", json=payload)
            elapsed = (time.time() - start_time) * 1000

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"LLM 请求失败: status={response.status_code}, error={error_text}")
                raise ModelConnectionException(
                    model_id=self.model_id,
                    reason=f"HTTP {response.status_code}: {error_text}",
                )

            data = response.json()
            logger.debug(f"LLM 响应: latency={elapsed:.0f}ms, tokens={data.get('usage', {})}")

            return self._parse_response(data, thinking_enabled)

        # 使用重试机制
        try:
            return await retry_on_failure(
                _request,
                max_retries=self.max_retries,
                base_delay=1.0,
                exceptions=(httpx.HTTPError, ModelConnectionException),
            )
        except Exception as e:
            logger.error(f"LLM 请求最终失败: {e}")
            raise

    async def stream_completion(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天补全

        Args:
            messages: 消息列表
            tools: 可用工具列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数

        Yields:
            生成的文本片段
        """
        logger.debug(
            f"LLM 流式请求: model={self.model_id}, "
            f"messages={format_messages_for_logging(messages)}"
        )

        async def _request():
            client = self._get_client()

            # 构建请求体
            payload = {
                "model": self.model_id,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                        **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                    }
                    for msg in messages
                ],
                "temperature": self.get_temperature(temperature),
                "stream": True,
                **(kwargs if kwargs else {}),
            }

            # 添加工具（如果有）
            if tools:
                payload["tools"] = [
                    {
                        "type": tool.type,
                        "function": tool.function,
                    }
                    for tool in tools
                ]

            # 添加 max_tokens（如果有）
            if max_tokens:
                payload["max_tokens"] = max_tokens

            # 发送流式请求
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_str = error_text.decode() if isinstance(error_text, bytes) else str(error_text)
                    logger.error(f"LLM 流式请求失败: status={response.status_code}, error={error_str}")
                    raise ModelConnectionException(
                        model_id=self.model_id,
                        reason=f"HTTP {response.status_code}: {error_str}",
                    )

                # 读取 SSE 流
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError, IndexError) as e:
                            logger.warning(f"解析流式响应失败: {e}, line={data_str}")
                            continue

        try:
            async for chunk in retry_on_failure(
                _request,
                max_retries=self.max_retries,
                base_delay=1.0,
                exceptions=(httpx.HTTPError, ModelConnectionException),
            ):
                yield chunk
        except Exception as e:
            logger.error(f"LLM 流式请求最终失败: {e}")
            raise

    async def test_connection(self) -> bool:
        """
        测试 API 连接

        Returns:
            连接是否成功
        """
        try:
            # 发送一个简单的测试请求
            messages = [Message(role="user", content="Hello")]
            response = await self.chat_completion(messages, max_tokens=5)
            logger.info(f"连接测试成功: model={self.model_id}")
            return True
        except Exception as e:
            logger.error(f"连接测试失败: model={self.model_id}, error={e}")
            return False

    def _parse_response(self, data: Dict[str, Any], thinking_enabled: bool = False) -> ChatResponse:
        """
        解析 API 响应

        Args:
            data: API 响应数据
            thinking_enabled: 是否启用了思考模式

        Returns:
            ChatResponse 对象
        """
        try:
            choice = data["choices"][0]
            message = choice["message"]

            # 如果启用了思考模式，使用 ThinkingResponseParser
            if thinking_enabled:
                parsed = ThinkingResponseParser.parse_response(self.model_id, data)
                content = parsed.get("content", "")
                reasoning_content = parsed.get("reasoning_content")
                thinking_tokens = parsed.get("thinking_tokens")
                usage = parsed.get("usage")
            else:
                # 原有逻辑
                content = message.get("content", "")
                reasoning_content = None
                thinking_tokens = None
                usage = data.get("usage")

            # 解析工具调用
            tool_calls = None
            if "tool_calls" in message:
                tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        type=tc.get("type", "function"),
                        function=tc["function"],
                    )
                    for tc in message["tool_calls"]
                ]

            return ChatResponse(
                content=content,
                tool_calls=tool_calls,
                reasoning_content=reasoning_content,
                thinking_tokens=thinking_tokens,
                usage=usage,
                model=data.get("model", self.model_id),
            )
        except (KeyError, IndexError) as e:
            logger.error(f"解析响应失败: {e}, data={data}")
            raise ModelConnectionException(
                model_id=self.model_id,
                reason=f"解析响应失败: {e}",
            )

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._close_client()


# =============================================================================
# 提供商工厂
# =============================================================================

class LLMProviderFactory:
    """LLM Provider 工厂"""

    @staticmethod
    def create_provider(
        provider_type: str,
        api_base_url: str,
        api_key: str,
        model_id: str,
        **kwargs
    ) -> LLMProvider:
        """
        创建 LLM Provider 实例

        Args:
            provider_type: 提供商类型
            api_base_url: API 基础 URL
            api_key: API 密钥
            model_id: 模型 ID
            **kwargs: 其他参数

        Returns:
            LLM Provider 实例
        """
        # 所有支持 OpenAI 兼容格式的提供商使用同一个实现
        return OpenAICompatProvider(
            api_base_url=api_base_url,
            api_key=api_key,
            model_id=model_id,
            **kwargs
        )

    @staticmethod
    def get_default_base_url(provider_type: str) -> str:
        """
        获取提供商的默认 API Base URL

        Args:
            provider_type: 提供商类型

        Returns:
            默认 API Base URL
        """
        urls = {
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "deepseek": "https://api.deepseek.com/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "openai": "https://api.openai.com/v1",
            "ollama": "http://localhost:11434/v1",
        }
        return urls.get(provider_type, "")

    @staticmethod
    def is_openai_compatible(provider_type: str) -> bool:
        """
        判断提供商是否支持 OpenAI 兼容格式

        Args:
            provider_type: 提供商类型

        Returns:
            是否支持 OpenAI 兼容格式
        """
        # 目前所有主流提供商都支持 OpenAI 兼容格式
        return provider_type in ["zhipu", "deepseek", "qwen", "openai", "ollama", "custom"]
