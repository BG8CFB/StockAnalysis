"""
阶段4智能体实现

总结报告智能体。
"""

import logging

from modules.trading_agents.agents.base import SummaryAgent
from core.ai.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class FinalSummarizer(SummaryAgent):
    """
    总结报告员

    汇总所有分析，生成最终投资建议报告。
    """

    # 默认提示词（当用户未自定义时使用）
    DEFAULT_ROLE_DEFINITION = """你是一位资深投资顾问。

你的任务是汇总所有分析师、研究员和风控官的意见，生成一份清晰、专业的最终投资建议报告。

报告结构：
1. **投资建议**（买入/卖出/持有）- 明确标注在开头
2. **核心观点摘要** - 用3-5句话概括核心观点
3. **分析师观点汇总** - 技术面、基本面、情绪面
4. **交易计划** - 具体的操作建议
5. **风险评估** - 风险等级和主要风险因素
6. **结论** - 总结性建议

要求：
- 语言简洁专业
- 逻辑清晰
- 观点明确
- 避免模棱两可
- 给出可执行的建议
"""

    def __init__(self, llm: LLMProvider, role_definition: str = None):
        # 优先使用传入的 role_definition，否则使用默认值
        final_role_definition = role_definition or self.DEFAULT_ROLE_DEFINITION

        super().__init__(
            slug="phase4_summary",
            name="首席投资顾问",
            role_definition=final_role_definition,
            llm=llm,
        )


def create_phase4_agents(llm: LLMProvider, phase4_config=None) -> list:
    """
    创建阶段4的所有智能体

    Args:
        llm: LLM Provider
        phase4_config: Phase 4 配置对象（包含用户自定义的智能体配置）

    Returns:
        智能体列表
    """
    # 如果没有提供配置，使用默认提示词创建智能体
    if not phase4_config or not phase4_config.agents:
        return [FinalSummarizer(llm)]

    # 从配置中提取智能体提示词
    agent_prompts = {}
    for agent_cfg in phase4_config.agents:
        if agent_cfg.enabled and agent_cfg.role_definition:
            agent_prompts[agent_cfg.slug] = agent_cfg.role_definition

    # 使用配置中的提示词（如果存在），否则使用默认值
    return [FinalSummarizer(llm, agent_prompts.get("phase4_summary"))]
