"""
思考内容管理器

统一管理 AI 模型的 reasoning_content（思考内容）。
支持自动附加、保留式思考、历史清理等功能。
"""

import logging
from typing import Any, Dict, List, Optional

from .types import AIMessage

logger = logging.getLogger(__name__)


class ThinkingContentManager:
    """
    思考内容管理器

    负责管理多轮对话中的思考内容（reasoning_content），支持：
    - 自动附加思考内容到消息
    - 保留式思考（多轮对话保留思考块）
    - 历史思考内容清理
    """

    def __init__(self, preserved_mode: bool = True):
        """
        初始化管理器

        Args:
            preserved_mode: 是否启用保留式思考（默认启用）
                - True: 保留历史思考内容（提升缓存命中率）
                - False: 每轮清除思考内容
        """
        self.preserved_mode = preserved_mode

    def attach_thinking_to_message(
        self, message: AIMessage, reasoning_content: Optional[str]
    ) -> AIMessage:
        """
        附加思考内容到消息

        Args:
            message: 原始消息
            reasoning_content: 思考内容

        Returns:
            附加了思考内容的消息
        """
        if reasoning_content:
            message.reasoning_content = reasoning_content
            logger.debug(f"附加思考内容: {len(reasoning_content)} 字符")
        return message

    def prepare_messages_with_thinking(
        self, messages: List[AIMessage], clear_history: bool = False
    ) -> List[AIMessage]:
        """
        准备包含思考内容的消息列表

        Args:
            messages: 原始消息列表
            clear_history: 是否清除历史思考内容（新问题开始时使用）

        Returns:
            处理后的消息列表
        """
        if clear_history:
            # 清除所有消息中的思考内容
            for msg in messages:
                if msg.reasoning_content:
                    msg.reasoning_content = None
            logger.debug("已清除历史思考内容")
        elif not self.preserved_mode:
            # 非保留模式：清除除最后一条外的所有思考内容
            for msg in messages[:-1]:
                if msg.reasoning_content:
                    msg.reasoning_content = None

        return messages

    def extract_thinking_from_response(self, response: Any) -> Optional[str]:
        """
        从模型响应中提取思考内容

        Args:
            response: LangChain 响应对象

        Returns:
            思考内容字符串，如果不存在则返回 None
        """
        # 尝试从 response_metadata 获取
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if isinstance(metadata, dict) and "reasoning_content" in metadata:
                return str(metadata["reasoning_content"])

        # 尝试从 additional_kwargs 获取（某些 LangChain 版本）
        if hasattr(response, "additional_kwargs"):
            additional = response.additional_kwargs
            if isinstance(additional, dict) and "reasoning_content" in additional:
                return str(additional["reasoning_content"])

        # 尝试直接获取
        if hasattr(response, "reasoning_content"):
            return str(response.reasoning_content)

        return None

    def should_preserve_thinking(self, model_id: str) -> bool:
        """
        判断模型是否应该使用保留式思考

        Args:
            model_id: 模型 ID

        Returns:
            是否保留思考内容
        """
        # GLM-4.7 推荐保留式思考（提升缓存命中率）
        if "glm-4.7" in model_id.lower():
            return True

        # 其他模型根据配置决定
        return self.preserved_mode

    def create_thinking_message(
        self,
        content: str,
        reasoning_content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> AIMessage:
        """
        创建包含思考内容的助手消息

        Args:
            content: 回答内容
            reasoning_content: 思考内容（可选）
            tool_calls: 工具调用（可选）

        Returns:
            AIMessage 对象
        """
        return AIMessage(
            role="assistant",
            content=content,
            reasoning_content=reasoning_content,
            tool_calls=tool_calls,
        )


# =============================================================================
# 全局单例
# =============================================================================

_thinking_manager: Optional[ThinkingContentManager] = None


def get_thinking_manager(preserved_mode: bool = True) -> ThinkingContentManager:
    """
    获取思考内容管理器单例

    Args:
        preserved_mode: 是否启用保留式思考（仅首次创建时生效）

    Returns:
        ThinkingContentManager 实例
    """
    global _thinking_manager
    if _thinking_manager is None:
        _thinking_manager = ThinkingContentManager(preserved_mode=preserved_mode)
        logger.info(f"思考内容管理器初始化: preserved_mode={preserved_mode}")
    return _thinking_manager
