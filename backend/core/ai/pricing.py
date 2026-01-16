"""
AI 模型价格配置和成本计算

内置主流模型定价，支持用户自定义价格。
提供 Token 成本计算功能。

价格单位统一为：per 1M tokens（每百万tokens）
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional


class PriceUnit(str, Enum):
    """价格单位"""
    PER_1K_TOKENS = "per_1k"  # 每 1K tokens
    PER_1M_TOKENS = "per_1m"  # 每 1M tokens


@dataclass
class ModelPrice:
    """单个模型的价格配置"""

    # 输入价格
    input_price: Decimal  # 价格数值
    input_unit: PriceUnit  # 价格单位

    # 输出价格
    output_price: Decimal
    output_unit: PriceUnit

    # 思考价格（如果模型支持思考能力）
    thinking_price: Optional[Decimal] = None
    thinking_unit: Optional[PriceUnit] = None

    # 货币单位
    currency: str = "CNY"  # 默认人民币

    # 更新时间
    updated_at: Optional[datetime] = None

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0
    ) -> Decimal:
        """
        计算成本

        Args:
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            thinking_tokens: 思考 token 数（如果支持）

        Returns:
            成本（单位：分，或根据货币单位）
        """
        cost = Decimal("0")

        # 输入成本
        if self.input_unit == PriceUnit.PER_1K_TOKENS:
            cost += Decimal(input_tokens) / 1000 * self.input_price
        elif self.input_unit == PriceUnit.PER_1M_TOKENS:
            cost += Decimal(input_tokens) / 1000000 * self.input_price

        # 输出成本
        if self.output_unit == PriceUnit.PER_1K_TOKENS:
            cost += Decimal(output_tokens) / 1000 * self.output_price
        elif self.output_unit == PriceUnit.PER_1M_TOKENS:
            cost += Decimal(output_tokens) / 1000000 * self.output_price

        # 思考成本
        if thinking_tokens > 0 and self.thinking_price and self.thinking_unit:
            if self.thinking_unit == PriceUnit.PER_1K_TOKENS:
                cost += Decimal(thinking_tokens) / 1000 * self.thinking_price
            elif self.thinking_unit == PriceUnit.PER_1M_TOKENS:
                cost += Decimal(thinking_tokens) / 1000000 * self.thinking_price

        # 转换为分（假设价格单位为元）
        return cost * 100


# =============================================================================
# 内置模型定价（2025年最新官方价格）
# 所有价格统一使用 per_1M（每百万tokens）作为单位
# 仅支持国内模型
# =============================================================================

BUILTIN_MODEL_PRICES: Dict[str, ModelPrice] = {
    # =========================================================================
    # 智谱 AI (GLM 系列) - 价格来源: https://bigmodel.cn/pricing
    # 2025年7月 GLM-4.5 发布，价格进一步下降
    # =========================================================================
    "glm-4.5": ModelPrice(
        input_price=Decimal("0.8"),  # 0.8元/百万tokens (2025年7月新价格)
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("2"),  # 2元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 7, 30),
    ),
    "glm-4-plus": ModelPrice(
        input_price=Decimal("5"),  # 5元/百万tokens
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("15"),  # 15元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 4, 24),
    ),
    "glm-4-plus-coder": ModelPrice(
        input_price=Decimal("5"),
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("15"),
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 4, 24),
    ),
    "glm-4-air": ModelPrice(
        input_price=Decimal("1"),  # 1元/百万tokens
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("2"),  # 2元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 4, 24),
    ),
    "glm-4-flash": ModelPrice(
        input_price=Decimal("0.1"),  # 0.1元/百万tokens
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("0.2"),  # 0.2元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 4, 24),
    ),
    # GLM-4.7 编程套餐（智谱AI编程专用模型）
    "glm-4.7": ModelPrice(
        input_price=Decimal("5"),  # 估计价格
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("15"),
        output_unit=PriceUnit.PER_1M_TOKENS,
        thinking_price=Decimal("15"),  # 思考token单独计价
        thinking_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 1, 1),
    ),
    "glm-4.6": ModelPrice(
        input_price=Decimal("5"),
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("15"),
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 1, 1),
    ),

    # =========================================================================
    # DeepSeek - 价格来源: https://api-docs.deepseek.com/zh-cn/quick_start/pricing
    # 2025年9月V3.2-Exp降价后价格
    # =========================================================================
    "deepseek-chat": ModelPrice(
        input_price=Decimal("4"),  # 4元/百万tokens (缓存未命中，2025年9月价格)
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("12"),  # 12元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 9, 6),
    ),
    "deepseek-coder": ModelPrice(
        input_price=Decimal("4"),
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("12"),
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 9, 6),
    ),
    "deepseek-reasoner": ModelPrice(
        input_price=Decimal("4"),  # 4元/百万tokens (估计)
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("12"),  # 12元/百万tokens (估计)
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 9, 6),
    ),

    # =========================================================================
    # 通义千问 - 价格来源: https://help.aliyun.com/zh/model-studio/model-pricing
    # 2025年价格
    # =========================================================================
    "qwen-max": ModelPrice(
        input_price=Decimal("2.4"),  # 2.4元/百万tokens (0.0024元/千)
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("9.6"),  # 9.6元/百万tokens (0.0096元/千)
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 11, 13),
    ),
    "qwen-plus": ModelPrice(
        input_price=Decimal("0.8"),  # 0.8元/百万tokens
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("2"),  # 2元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 1, 1),
    ),
    "qwen-turbo": ModelPrice(
        input_price=Decimal("0.4"),  # 0.4元/百万tokens (估计)
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("1"),  # 1元/百万tokens (估计)
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 1, 1),
    ),

    # =========================================================================
    # Moonshot AI (Kimi) - 价格来源: https://platform.moonshot.cn/docs/pricing/chat
    # 2025年11月价格
    # =========================================================================
    "moonshot-v1-8k": ModelPrice(
        input_price=Decimal("1.2"),  # 1.2元/百万tokens
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("3"),  # 3元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 11, 13),
    ),
    "moonshot-v1-32k": ModelPrice(
        input_price=Decimal("2.4"),  # 2.4元/百万tokens
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("6"),  # 6元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 11, 13),
    ),
    "moonshot-v1-128k": ModelPrice(
        input_price=Decimal("10"),  # 10元/百万tokens
        input_unit=PriceUnit.PER_1M_TOKENS,
        output_price=Decimal("30"),  # 30元/百万tokens
        output_unit=PriceUnit.PER_1M_TOKENS,
        currency="CNY",
        updated_at=datetime(2025, 11, 13),
    ),
}


class ModelPricingService:
    """模型价格服务"""

    def __init__(self):
        # 内置价格
        self._builtin_prices = BUILTIN_MODEL_PRICES.copy()
        # 用户自定义价格（从数据库加载）
        self._custom_prices: Dict[str, ModelPrice] = {}

    def get_price(self, model_id: str) -> Optional[ModelPrice]:
        """
        获取模型价格配置

        优先级：用户自定义 > 内置价格

        Args:
            model_id: 模型 ID

        Returns:
            价格配置，如果未找到则返回 None
        """
        # 先检查用户自定义
        if model_id in self._custom_prices:
            return self._custom_prices[model_id]

        # 检查内置价格
        if model_id in self._builtin_prices:
            return self._builtin_prices[model_id]

        return None

    def set_custom_price(self, model_id: str, price: ModelPrice):
        """
        设置用户自定义价格

        Args:
            model_id: 模型 ID
            price: 价格配置
        """
        self._custom_prices[model_id] = price

    def calculate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0
    ) -> Optional[Decimal]:
        """
        计算模型调用成本

        Args:
            model_id: 模型 ID
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            thinking_tokens: 思考 token 数

        Returns:
            成本（单位：分），如果模型未配置价格则返回 None
        """
        price = self.get_price(model_id)
        if not price:
            return None

        return price.calculate_cost(input_tokens, output_tokens, thinking_tokens)

    def list_priced_models(self) -> Dict[str, ModelPrice]:
        """
        列出所有有定价的模型

        Returns:
            模型ID到价格配置的映射
        """
        result = {}
        result.update(self._builtin_prices)
        result.update(self._custom_prices)
        return result


# =============================================================================
# 全局单例
# =============================================================================

_pricing_service: Optional[ModelPricingService] = None


def get_pricing_service() -> ModelPricingService:
    """获取价格服务单例"""
    global _pricing_service
    if _pricing_service is None:
        _pricing_service = ModelPricingService()
    return _pricing_service
