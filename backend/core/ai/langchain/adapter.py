"""
LangChain 适配器

负责创建和配置 LangChain ChatModel 实例。
支持所有 OpenAI 兼容的模型（智谱、DeepSeek、千问、Claude 等）。
"""

import logging
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class LangChainAdapter:
    """LangChain 适配器

    负责创建和配置 LangChain ChatModel 实例。
    支持所有 OpenAI 兼容的模型。
    """

    # 默认 API 端点
    DEFAULT_BASE_URLS = {
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        "zhipu_coding": "https://open.bigmodel.cn/api/coding/paas/v4",
        "deepseek": "https://api.deepseek.com",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "moonshot": "https://api.moonshot.cn/v1",
        "openai": "https://api.openai.com/v1",
    }

    @classmethod
    def create_chat_model(
        cls,
        model_id: str,
        api_key: str,
        platform: str,
        api_base_url: Optional[str] = None,
        temperature: float = 0.5,
        timeout_seconds: int = 60,
        max_retries: int = 3,
        thinking_enabled: bool = False,
        reasoning_effort: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        **kwargs,
    ):
        """
        创建 LangChain ChatModel 实例

        Args:
            model_id: 模型 ID (如 glm-4.7)
            api_key: API 密钥
            platform: 平台名称 (zhipu, openai, anthropic, etc.)
            api_base_url: 自定义 API 端点
            temperature: 温度参数
            timeout_seconds: 超时时间
            max_retries: 最大重试次数
            thinking_enabled: 启用思考模式（思考内容会返回给用户）
            reasoning_effort: 推理级别 (OpenAI o1/o3)
            budget_tokens: token 预算 (Claude)
            **kwargs: 其他参数

        Returns:
            ChatModel 实例 (ChatOpenAI 或 ChatAnthropic)
        """
        # 标准化平台名称
        platform_lower = platform.lower()

        # Claude 使用专门的 ChatAnthropic 类
        if "claude" in platform_lower or "anthropic" in platform_lower:
            return cls._create_anthropic_model(
                model_id=model_id,
                api_key=api_key,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                thinking_enabled=thinking_enabled,
                budget_tokens=budget_tokens,
                **kwargs,
            )

        # 其他平台使用 ChatOpenAI (OpenAI 兼容接口)
        return cls._create_openai_model(
            model_id=model_id,
            api_key=api_key,
            platform=platform,
            api_base_url=api_base_url,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            thinking_enabled=thinking_enabled,
            reasoning_effort=reasoning_effort,
            **kwargs,
        )

    @classmethod
    def _create_openai_model(
        cls,
        model_id: str,
        api_key: str,
        platform: str,
        api_base_url: Optional[str] = None,
        temperature: float = 0.5,
        timeout_seconds: int = 60,
        max_retries: int = 3,
        thinking_enabled: bool = False,
        reasoning_effort: Optional[str] = None,
        **kwargs,
    ) -> ChatOpenAI:
        """创建 ChatOpenAI 实例"""
        # 确定 API 端点
        base_url = api_base_url or cls.DEFAULT_BASE_URLS.get(platform)

        # 构建模型参数
        model_kwargs = {}

        # 添加思考参数
        if thinking_enabled:
            model_kwargs.update(
                cls._build_thinking_params(model_id, reasoning_effort)
            )

        logger.debug(
            f"创建 ChatOpenAI: model={model_id}, platform={platform}, "
            f"base_url={base_url}, thinking={thinking_enabled}"
        )

        # 提取 extra_body 参数（用于 GLM-4.7 thinking 等）
        extra_body = model_kwargs.pop("thinking", None)
        if extra_body:
            model_kwargs["extra_body"] = {"thinking": extra_body}

        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            timeout=timeout_seconds,
            max_retries=max_retries,
            model_kwargs=model_kwargs if model_kwargs else {},
            **kwargs,
        )

    @classmethod
    def _create_anthropic_model(
        cls,
        model_id: str,
        api_key: str,
        temperature: float = 0.5,
        timeout_seconds: int = 60,
        max_retries: int = 3,
        thinking_enabled: bool = False,
        budget_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatAnthropic:
        """创建 ChatAnthropic 实例"""
        # 构建模型参数
        model_kwargs = {}

        # Claude 思考参数
        if thinking_enabled:
            budget = budget_tokens or 20000
            model_kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
            logger.debug(f"Claude 思考模式: budget_tokens={budget}")

        logger.debug(f"创建 ChatAnthropic: model={model_id}, " f"thinking={thinking_enabled}")

        return ChatAnthropic(
            model=model_id,
            api_key=api_key,
            temperature=temperature,
            timeout=timeout_seconds,
            max_retries=max_retries,
            model_kwargs=model_kwargs if model_kwargs else {},
            **kwargs,
        )

    @classmethod
    def _build_thinking_params(
        cls,
        model_id: str,
        reasoning_effort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        构建思考参数（支持多模型思考模式）

        统一支持以下思考能力：
        - GLM-4.7: 交错式思考（思考内容会返回给用户）
        - GLM-4.x: 基础思考模式
        - DeepSeek: 思考模式（V3.2+ 支持工具调用）
        - OpenAI o1/o3: 推理级别控制
        - Claude: 扩展思考模式

        Args:
            model_id: 模型 ID
            reasoning_effort: 推理级别 (low/medium/high)

        Returns:
            模型参数字典，包含 "thinking" 或 "reasoning" 键
        """
        model_id_lower = model_id.lower()

        # GLM-4.7 思考模式（思考内容会返回给用户）
        if "glm-4.7" in model_id_lower:
            return {
                "thinking": {
                    "type": "enabled",
                    "clear_thinking": False,  # 保留思考内容并返回
                }
            }

        # GLM-4.6 及早期版本的思考模式
        if "glm-4" in model_id_lower:
            return {
                "thinking": {
                    "type": "enabled",
                }
            }

        # DeepSeek 思考模式（支持所有 DeepSeek 模型）
        if "deepseek" in model_id_lower:
            return {
                "thinking": {
                    "type": "enabled",
                }
            }

        # OpenAI o1/o3 推理级别
        if any(x in model_id_lower for x in ["o1", "o3"]):
            effort = reasoning_effort or "medium"
            return {
                "reasoning": {
                    "effort": effort,
                }
            }

        # 其他模型（Qwen、Moonshot 等）如果支持思考模式
        return {}

    @classmethod
    def get_default_base_url(cls, platform: str) -> Optional[str]:
        """
        获取平台的默认 API 端点

        Args:
            platform: 平台名称

        Returns:
            API 端点 URL，如果未配置则返回 None
        """
        return cls.DEFAULT_BASE_URLS.get(platform)

    @classmethod
    def register_base_url(cls, platform: str, url: str):
        """
        注册新的 API 端点

        Args:
            platform: 平台名称
            url: API 端点 URL
        """
        cls.DEFAULT_BASE_URLS[platform] = url
        logger.info(f"注册 API 端点: {platform} -> {url}")
