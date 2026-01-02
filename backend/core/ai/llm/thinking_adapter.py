"""
思考参数适配器

将统一的思考配置转换为各模型特定的 API 参数格式。
支持 GLM-4.7、DeepSeek、OpenAI o1/o3、Claude 等主流思考模型。
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ThinkingEffortLevel(str, Enum):
    """OpenAI 推理级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ThinkingParameterAdapter:
    """
    思考参数适配器

    根据模型 ID 和思考配置，自动生成符合该模型 API 规范的思考参数。
    """

    @staticmethod
    def adapt(
        model_id: str,
        thinking_enabled: bool,
        thinking_mode: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        适配思考参数

        Args:
            model_id: 模型 ID
            thinking_enabled: 是否启用思考
            thinking_mode: 思考模式 (preserved/clear_on_new/auto)
            budget_tokens: Token 预算（Claude）
            reasoning_effort: 推理级别 (low/medium/high，OpenAI)

        Returns:
            模型特定的思考参数，如果不支持思考则返回 None
        """
        if not thinking_enabled:
            return None

        # 标准化模型 ID（转为小写便于匹配）
        model_id_lower = model_id.lower()

        # GLM-4.7 系列判断
        if "glm-4.7" in model_id_lower or "glm47" in model_id_lower:
            return ThinkingParameterAdapter._adapt_glm47(thinking_mode)

        # DeepSeek 系列判断
        if "deepseek" in model_id_lower:
            return ThinkingParameterAdapter._adapt_deepseek()

        # OpenAI o1/o3 系列判断
        if any(x in model_id_lower for x in ["o1", "o3", "gpt-5"]):
            return ThinkingParameterAdapter._adapt_openai(reasoning_effort)

        # Claude 系列判断
        if "claude" in model_id_lower:
            return ThinkingParameterAdapter._adapt_claude(budget_tokens)

        # 其他模型，暂不支持思考模式
        logger.debug(f"模型 {model_id} 暂不支持思考模式")
        return None

    @staticmethod
    def _adapt_glm47(thinking_mode: Optional[str]) -> Dict[str, Any]:
        """
        适配 GLM-4.7 参数

        GLM-4.7 支持两种思考模式：
        - preserved (clear_thinking: false): 保留式思考，适合长任务
        - clear_on_new (clear_thinking: true): 清除式思考，适合批量任务
        """
        # 默认使用保留式思考
        clear_thinking = False

        if thinking_mode == "clear_on_new":
            clear_thinking = True
        elif thinking_mode == "preserved":
            clear_thinking = False
        # auto 模式下，默认为保留式

        return {
            "thinking": {
                "type": "enabled",
                "clear_thinking": clear_thinking
            }
        }

    @staticmethod
    def _adapt_deepseek() -> Dict[str, Any]:
        """
        适配 DeepSeek R1 参数

        DeepSeek 使用简单的 thinking.type 参数
        """
        return {
            "thinking": {
                "type": "enabled"
            }
        }

    @staticmethod
    def _adapt_openai(reasoning_effort: Optional[str]) -> Dict[str, Any]:
        """
        适配 OpenAI o1/o3 参数

        使用 reasoning.effort 参数，可选值：low, medium, high
        默认为 medium
        """
        effort = reasoning_effort or ThinkingEffortLevel.MEDIUM.value

        # 验证 effort 值
        valid_efforts = [e.value for e in ThinkingEffortLevel]
        if effort not in valid_efforts:
            logger.warning(f"无效的 reasoning_effort 值: {effort}，使用默认值 medium")
            effort = ThinkingEffortLevel.MEDIUM.value

        return {
            "reasoning": {
                "effort": effort
            }
        }

    @staticmethod
    def _adapt_claude(budget_tokens: Optional[int]) -> Dict[str, Any]:
        """
        适配 Claude 参数

        Claude 使用 thinking.type 和 thinking.budget_tokens 参数
        推荐的 budget_tokens 起始值为 20000
        """
        budget = budget_tokens or 20000

        # 验证 budget_tokens 范围
        if budget < 1024:
            logger.warning(f"budget_tokens 过小: {budget}，使用最小值 1024")
            budget = 1024
        elif budget > 200000:
            logger.warning(f"budget_tokens 过大: {budget}，使用最大值 200000")
            budget = 200000

        return {
            "thinking": {
                "type": "enabled",
                "budget_tokens": budget
            }
        }

    @staticmethod
    def get_default_config(model_id: str) -> Dict[str, Any]:
        """
        获取模型的默认思考配置

        Args:
            model_id: 模型 ID

        Returns:
            默认配置字典，包含推荐的参数值
        """
        model_id_lower = model_id.lower()

        if "glm-4.7" in model_id_lower or "glm47" in model_id_lower:
            return {
                "thinking_mode": "preserved",  # 推荐保留式
                "description": "GLM-4.7 支持保留式和清除式思考，长任务推荐保留式"
            }

        if "deepseek" in model_id_lower:
            return {
                "thinking_mode": "auto",
                "description": "DeepSeek 自动处理思考模式"
            }

        if any(x in model_id_lower for x in ["o1", "o3", "gpt-5"]):
            return {
                "reasoning_effort": "medium",
                "description": "OpenAI 推理级别：low(快速)、medium(平衡)、high(完整)"
            }

        if "claude" in model_id_lower:
            return {
                "budget_tokens": 20000,
                "description": "Claude 推荐 budget_tokens: 20000"
            }

        return {
            "description": "此模型暂不支持思考模式"
        }
