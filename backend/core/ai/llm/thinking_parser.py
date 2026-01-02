"""
思考响应解析器

解析不同模型的思考模式响应，提取思考内容和统计信息。
支持 GLM-4.7、DeepSeek、OpenAI、Claude 等主流思考模型。
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ThinkingResponseParser:
    """
    思考响应解析器

    从不同模型的 API 响应中提取思考内容、token 统计等信息。
    """

    @staticmethod
    def parse_response(
        model_id: str,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        解析响应中的思考内容

        Args:
            model_id: 模型 ID
            response_data: 原始 API 响应数据

        Returns:
            包含思考内容的字典：
            {
                "content": str,  # 最终答案
                "reasoning_content": Optional[str],  # 思考内容
                "thinking_tokens": Optional[int],  # 思考 token 数量
                "usage": Optional[Dict]  # 完整 usage 信息
            }
        """
        model_id_lower = model_id.lower()

        # GLM-4.7 和 DeepSeek 使用相同格式
        if any(x in model_id_lower for x in ["glm", "deepseek"]):
            return ThinkingResponseParser._parse_reasoning_content_field(response_data)

        # OpenAI 使用 usage 统计格式
        if any(x in model_id_lower for x in ["o1", "o3", "gpt-5", "openai"]):
            return ThinkingResponseParser._parse_usage_based(response_data)

        # Claude 使用 content blocks 格式
        if "claude" in model_id_lower:
            return ThinkingResponseParser._parse_content_blocks(response_data)

        # 默认：尝试提取 reasoning_content 字段
        return ThinkingResponseParser._parse_reasoning_content_field(response_data)

    @staticmethod
    def _parse_reasoning_content_field(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析包含 reasoning_content 字段的响应（GLM-4.7、DeepSeek）

        响应格式：
        {
          "choices": [{
            "message": {
              "content": "最终答案",
              "reasoning_content": "思考过程..."
            }
          }],
          "usage": {...}
        }
        """
        try:
            choice = response_data.get("choices", [{}])[0]
            message = choice.get("message", {})

            content = message.get("content", "")
            reasoning_content = message.get("reasoning_content")
            usage = response_data.get("usage")

            return {
                "content": content,
                "reasoning_content": reasoning_content,
                "thinking_tokens": None,  # GLM/DeepSeek 不单独统计
                "usage": usage
            }
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"解析响应失败: {e}")
            return {
                "content": "",
                "reasoning_content": None,
                "thinking_tokens": None,
                "usage": None
            }

    @staticmethod
    def _parse_usage_based(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析基于 usage 统计的响应（OpenAI o1/o3）

        响应格式：
        {
          "choices": [{
            "message": {"content": "最终答案"}
          }],
          "usage": {
            "output_tokens_details": {
              "reasoning_tokens": 1024
            }
          }
        }
        """
        try:
            choice = response_data.get("choices", [{}])[0]
            message = choice.get("message", {})

            content = message.get("content", "")
            usage = response_data.get("usage", {})
            output_details = usage.get("output_tokens_details", {})
            thinking_tokens = output_details.get("reasoning_tokens")

            return {
                "content": content,
                "reasoning_content": None,  # OpenAI 不返回思考内容
                "thinking_tokens": thinking_tokens,
                "usage": usage
            }
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"解析 OpenAI 响应失败: {e}")
            return {
                "content": "",
                "reasoning_content": None,
                "thinking_tokens": None,
                "usage": None
            }

    @staticmethod
    def _parse_content_blocks(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 content blocks 格式的响应（Claude）

        响应格式：
        {
          "content": [
            {"type": "thinking", "thinking": "思考过程...", "signature": "..."},
            {"type": "text", "text": "最终答案"}
          ],
          "usage": {...}
        }
        """
        try:
            content_blocks = response_data.get("content", [])
            usage = response_data.get("usage")

            # 提取所有 thinking blocks
            thinking_blocks = []
            text_content = []

            for block in content_blocks:
                if block.get("type") == "thinking":
                    thinking_blocks.append(block.get("thinking", ""))
                elif block.get("type") == "text":
                    text_content.append(block.get("text", ""))

            # 合并思考内容
            reasoning_content = "\n\n".join(thinking_blocks) if thinking_blocks else None
            # 合并文本内容
            content = "\n\n".join(text_content) if text_content else ""

            return {
                "content": content,
                "reasoning_content": reasoning_content,
                "thinking_tokens": None,  # Claude 也可能在 usage 中统计
                "usage": usage
            }
        except (KeyError, TypeError) as e:
            logger.error(f"解析 Claude 响应失败: {e}")
            return {
                "content": "",
                "reasoning_content": None,
                "thinking_tokens": None,
                "usage": None
            }

    @staticmethod
    def should_preserve_reasoning(model_id: str, is_new_user_turn: bool = False) -> bool:
        """
        判断是否应该在下一轮中回传 reasoning_content

        Args:
            model_id: 模型 ID
            is_new_user_turn: 是否是新的用户问题（不是工具调用的继续）

        Returns:
            是否应该保留 reasoning_content
        """
        model_id_lower = model_id.lower()

        # GLM-4.7：始终保留（保留式思考）
        if "glm-4.7" in model_id_lower or "glm47" in model_id_lower:
            return True

        # DeepSeek：工具调用循环内保留，新用户问题时清除
        if "deepseek" in model_id_lower:
            return not is_new_user_turn

        # OpenAI：不需要保留（模型自动丢弃）
        if any(x in model_id_lower for x in ["o1", "o3", "gpt-5", "openai"]):
            return False

        # Claude Opus 4.5+：默认保留
        if "claude" in model_id_lower:
            # 简化处理：所有 Claude 都保留
            return True

        # 其他模型：不保留
        return False

    @staticmethod
    def build_message_with_reasoning(
        role: str,
        content: str,
        reasoning_content: Optional[str],
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
        should_preserve: bool = True
    ) -> Dict[str, Any]:
        """
        构建包含 reasoning_content 的消息

        Args:
            role: 消息角色
            content: 消息内容
            reasoning_content: 思考内容
            tool_calls: 工具调用
            tool_call_id: 工具调用 ID
            should_preserve: 是否保留 reasoning_content

        Returns:
            消息字典
        """
        message = {
            "role": role,
            "content": content
        }

        # 根据保留策略添加 reasoning_content
        if should_preserve and reasoning_content:
            message["reasoning_content"] = reasoning_content

        # 添加工具调用相关字段
        if tool_calls:
            message["tool_calls"] = tool_calls

        if tool_call_id:
            message["tool_call_id"] = tool_call_id

        return message
