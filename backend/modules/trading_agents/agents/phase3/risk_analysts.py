"""
第三阶段风险分析师

包含不同风险偏好的分析师：激进派、保守派、中性派。
"""

import logging
from typing import Dict, Any

from modules.trading_agents.agents.base import BaseAgent
from core.ai.llm.provider import LLMProvider, Message

logger = logging.getLogger(__name__)


class BaseRiskAgent(BaseAgent):
    """风险分析师基类"""

    async def execute(self, state: Dict[str, Any]) -> str:
        """执行风险分析师逻辑"""
        messages = self.build_messages(state)
        return await self.call_llm(messages)

    def build_user_message(self, state: Dict[str, Any]) -> str:
        """构建基础上下文消息"""
        message = f"""请分析以下股票的风险：
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 交易计划
{state.get('trade_plan', {}).get('content', '（无交易计划）')}

## 研究经理裁决
{state.get('manager_decision', '（无裁决）')}

请基于你的风险偏好立场，指出上述计划中潜在的问题和风险。
"""
        return message


class AggressiveRiskAgent(BaseRiskAgent):
    """
    激进派风险分析师
    
    倾向于为了高收益容忍高风险，关注机会成本。
    """
    
    def __init__(self, llm: LLMProvider):
        role_definition = """你是一位激进派的风险分析师。

你的理念是“盈亏同源，不敢承担风险就没有收益”。
在风险评估讨论中，你的任务是：
1. 避免过于保守导致错失良机（机会成本风险）
2. 强调潜在的高赔率
3. 指出如果过于谨慎可能带来的负面影响
4. 在可控范围内支持更积极的仓位

但你仍然是风控团队的一员，不是无脑赌徒。你要做的是在“风险”和“收益”之间寻找更有利于进攻的平衡点。
"""
        super().__init__(
            slug="phase3_aggressive",
            name="激进派风控",
            llm=llm
        )
        self._role_definition = role_definition

    def get_system_prompt(self) -> str:
        return self._role_definition


class ConservativeRiskAgent(BaseRiskAgent):
    """
    保守派风险分析师
    
    首要目标是本金安全，厌恶不确定性。
    """
    
    def __init__(self, llm: LLMProvider):
        role_definition = """你是一位保守派的风险分析师。

你的理念是“本金安全第一，宁可错过不做错”。
在风险评估讨论中，你的任务是：
1. 识别一切可能的下行风险（黑天鹅、灰犀牛）
2. 质疑所有乐观的假设
3. 强调最坏情况下的回撤
4. 呼吁更低的仓位和更严格的止损

你是团队中的“刹车片”，负责泼冷水，确保交易计划不会导致灾难性亏损。
"""
        super().__init__(
            slug="phase3_conservative",
            name="保守派风控",
            llm=llm
        )
        self._role_definition = role_definition

    def get_system_prompt(self) -> str:
        return self._role_definition


class NeutralRiskAgent(BaseRiskAgent):
    """
    中性派风险分析师
    
    客观中立，关注风险收益比的合理性。
    """
    
    def __init__(self, llm: LLMProvider):
        role_definition = """你是一位中性派的风险分析师。

你的理念是“风险收益比（盈亏比）决定一切”。
在风险评估讨论中，你的任务是：
1. 平衡激进派和保守派的观点
2. 用概率思维评估风险
3. 关注流动性风险、操作风险等技术性细节
4. 确保交易计划在逻辑上是自洽的

你是团队中的“天平”，负责在过度贪婪和过度恐惧之间寻找客观的真理。
"""
        super().__init__(
            slug="phase3_neutral",
            name="中性派风控",
            llm=llm
        )
        self._role_definition = role_definition

    def get_system_prompt(self) -> str:
        return self._role_definition
