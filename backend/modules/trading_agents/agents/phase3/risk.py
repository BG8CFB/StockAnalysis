"""
阶段3智能体实现

风险评估团队：激进/保守/中性派及首席风控官。
"""

import logging
from typing import List

from modules.trading_agents.agents.base import BaseAgent
from core.ai.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class ChiefRiskOfficer(BaseAgent):
    """
    首席风控官 (CRO)
    
    综合各方风险观点，给出最终的风险评估报告。
    """

    def __init__(self, llm: LLMProvider):
        role_definition = """你是一位首席风控官 (CRO)。

你的任务是审阅激进派、保守派和中性派风险分析师的讨论记录，对交易计划进行最终的风险定调。

请输出：
1. **风险综述**：总结各方主要顾虑
2. **风险等级**：高/中/低
3. **关键否决项**：是否存在必须终止交易的致命风险？
4. **仓位建议**：基于风险评估调整后的建议仓位（例如：建议从计划的 50% 降低到 30%）
5. **止损红线**：强制执行的止损位
"""

        super().__init__(
            slug="phase3_cro",
            name="首席风控官",
            llm=llm,
        )
        self._role_definition = role_definition

    def get_system_prompt(self) -> str:
        return self._role_definition

    def build_user_message(self, state) -> str:
        message = f"""请对以下股票交易计划进行最终风险评估：
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 交易计划
{state.get('trade_plan', {}).get('content', '（无交易计划）')}

## 风险讨论记录

"""
        # 添加讨论记录
        for turn in state.get("risk_discussion_turns", []):
            message += f"### 讨论轮次 {turn['round_index']}\n"
            message += f"**激进派观点**：\n{turn['aggressive_view']}\n\n"
            message += f"**保守派观点**：\n{turn['conservative_view']}\n\n"
            message += f"**中性派观点**：\n{turn['neutral_view']}\n\n"

        return message

    async def execute(self, state) -> str:
        messages = self.build_messages(state)
        return await self.call_llm(messages)


def create_phase3_agents(llm: LLMProvider) -> List:
    """创建阶段3的所有智能体"""
    from .risk_analysts import AggressiveRiskAgent, ConservativeRiskAgent, NeutralRiskAgent
    from .risk_manager import RiskDiscussionManager
    
    # 注意：这里返回列表主要是为了注册，实际执行流程由 Engine/Manager 控制
    return [
        AggressiveRiskAgent(llm),
        ConservativeRiskAgent(llm),
        NeutralRiskAgent(llm),
        ChiefRiskOfficer(llm)
    ]
