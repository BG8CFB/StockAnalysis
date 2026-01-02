"""
阶段2智能体实现

研究员辩论和交易计划智能体。
"""

import logging

from modules.trading_agents.agents.base import DebateAgent, BaseAgent
from core.ai.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class BullDebater(DebateAgent):
    """
    看涨研究员

    在辩论中代表看涨观点，反驳看跌方的论点。
    """

    # 默认提示词（当用户未自定义时使用）
    DEFAULT_ROLE_DEFINITION = """你是一位经验丰富的看涨研究员。

你的任务是在投资辩论中代表看涨观点，论证股票的投资价值。

请：
1. 基于分析师报告中的看涨论据
2. 针对看跌研究员的观点进行反驳
3. 提出更有力的看涨证据
4. 给出明确的看涨建议

输出格式：
- 首先总结你的核心看涨论点
- 然后逐条反驳对手的观点
- 最后给出强有力的看涨结论
"""

    def __init__(self, llm: LLMProvider, role_definition: str = None):
        # 优先使用传入的 role_definition，否则使用默认值
        final_role_definition = role_definition or self.DEFAULT_ROLE_DEFINITION

        super().__init__(
            slug="phase2_bull",
            name="看涨研究员",
            role_definition=final_role_definition,
            llm=llm,
        )


class BearDebater(DebateAgent):
    """
    看跌研究员

    在辩论中代表看跌观点，反驳看涨方的论点。
    """

    # 默认提示词（当用户未自定义时使用）
    DEFAULT_ROLE_DEFINITION = """你是一位经验丰富的看跌研究员。

你的任务是在投资辩论中代表看跌观点，提示投资风险。

请：
1. 基于分析师报告中的看跌论据
2. 针对看涨研究员的观点进行反驳
3. 提出更有力的风险证据
4. 给出明确的看跌建议

输出格式：
- 首先总结你的核心看跌论点
- 然后逐条反驳对手的观点
- 最后给出强有力的看跌结论
"""

    def __init__(self, llm: LLMProvider, role_definition: str = None):
        # 优先使用传入的 role_definition，否则使用默认值
        final_role_definition = role_definition or self.DEFAULT_ROLE_DEFINITION

        super().__init__(
            slug="phase2_bear",
            name="看跌研究员",
            role_definition=final_role_definition,
            llm=llm,
        )


class TradePlanner(BaseAgent):
    """
    交易员

    综合辩论结果和研究经理的裁决，制定具体的交易计划。
    """

    # 默认提示词（当用户未自定义时使用）
    DEFAULT_ROLE_DEFINITION = """你是一位专业的交易员。

你的任务是综合看涨和看涨研究员的辩论结果，并参考研究经理的裁决，制定具体的交易计划。

请分析：
1. 双方的论点强度
2. 研究经理的倾向性
3. 风险收益比

然后给出具体的交易计划：
- 操作建议（买入/卖出/持有）
- 建议价格区间
- 仓位配置
- 止损止盈位
- 持有周期
"""

    def __init__(self, llm: LLMProvider, role_definition: str = None):
        # 优先使用传入的 role_definition，否则使用默认值
        final_role_definition = role_definition or self.DEFAULT_ROLE_DEFINITION
        self._role_definition = final_role_definition

        super().__init__(
            slug="phase2_planner",
            name="交易员",
            llm=llm,
        )

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self._role_definition

    def build_user_message(self, state) -> str:
        """构建用户消息（包含辩论历史和裁决）"""
        message = f"""请为以下股票制定交易计划：
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 研究经理裁决
{state.get('manager_decision', '（无裁决）')}

## 辩论记录

"""

        # 添加初始观点
        if state.get("initial_bull_view"):
            message += f"### 初始看涨观点\n{state['initial_bull_view']}\n\n"

        if state.get("initial_bear_view"):
            message += f"### 初始看跌观点\n{state['initial_bear_view']}\n\n"

        # 添加辩论轮次
        for turn in state.get("debate_turns", []):
            message += f"### 第{turn['round_index']}轮辩论\n\n"
            message += f"**看涨方**：{turn['bull_argument']}\n\n"
            message += f"**看跌方**：{turn['bear_argument']}\n\n"

        return message

    async def execute(self, state) -> str:
        """执行交易员逻辑"""
        messages = self.build_messages(state)
        return await self.call_llm(messages)


def create_phase2_agents(llm: LLMProvider, phase2_config=None) -> list:
    """
    创建阶段2的所有智能体

    Args:
        llm: LLM Provider
        phase2_config: Phase 2 配置对象（包含用户自定义的智能体配置）

    Returns:
        智能体列表
    """
    from .research_manager import ResearchManager

    # 如果没有提供配置，使用默认提示词创建智能体
    if not phase2_config or not phase2_config.agents:
        return [
            BullDebater(llm),
            BearDebater(llm),
            ResearchManager(llm),
            TradePlanner(llm),
        ]

    # 从配置中提取智能体提示词
    agent_prompts = {}
    for agent_cfg in phase2_config.agents:
        if agent_cfg.enabled and agent_cfg.role_definition:
            agent_prompts[agent_cfg.slug] = agent_cfg.role_definition

    # 使用配置中的提示词（如果存在），否则使用默认值
    return [
        BullDebater(llm, agent_prompts.get("phase2_bull")),
        BearDebater(llm, agent_prompts.get("phase2_bear")),
        ResearchManager(llm, agent_prompts.get("phase2_manager")),
        TradePlanner(llm, agent_prompts.get("phase2_planner")),
    ]
