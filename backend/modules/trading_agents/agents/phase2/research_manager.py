"""
第二阶段研究经理

负责在辩论结束后进行裁决，评估双方论点，为交易员提供决策依据。
"""

import logging
from typing import Dict, Any

from modules.trading_agents.agents.base import BaseAgent
from core.ai.llm.provider import LLMProvider, Message

logger = logging.getLogger(__name__)


class ResearchManager(BaseAgent):
    """
    研究经理

    在多空辩论结束后，综合双方观点，做出客观裁决。
    """

    # 默认提示词（当用户未自定义时使用）
    DEFAULT_ROLE_DEFINITION = """你是一位资深的研究经理。

你的任务是：
1. 审阅看涨和看跌研究员的辩论记录
2. 评估双方论据的质量和说服力
3. 识别关键的市场分歧点
4. 做出客观的投资裁决（偏向看涨/偏向看跌/中性/不确定）

你的裁决将直接指导交易员制定具体的交易计划。请务必客观、公正，不要偏袒任何一方，只看事实和逻辑。

输出格式：
- **辩论总结**：简要回顾双方核心论点
- **关键分歧**：列出双方争议最大的点
- **裁决结果**：明确的倾向性判断
- **指导意见**：给交易员的高层建议（如"建议轻仓试错"或"建议坚决回避"）
"""

    def __init__(self, llm: LLMProvider, role_definition: str = None):
        # 优先使用传入的 role_definition，否则使用默认值
        final_role_definition = role_definition or self.DEFAULT_ROLE_DEFINITION

        super().__init__(
            slug="phase2_manager",
            name="研究经理",
            llm=llm,
        )
        self._role_definition = final_role_definition

    def get_system_prompt(self) -> str:
        return self._role_definition

    def build_user_message(self, state: Dict[str, Any]) -> str:
        """构建包含完整辩论历史的消息"""
        message = f"""请对以下股票的投资辩论进行裁决：
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 辩论记录

"""
        # 1. 初始观点
        if state.get("initial_bull_view"):
            message += f"### 初始看涨观点\n{state['initial_bull_view']}\n\n"
        if state.get("initial_bear_view"):
            message += f"### 初始看跌观点\n{state['initial_bear_view']}\n\n"

        # 2. 辩论过程
        for turn in state.get("debate_turns", []):
            message += f"### 第 {turn['round_index']} 轮辩论\n"
            message += f"**看涨方反驳**：\n{turn['bull_argument']}\n\n"
            message += f"**看跌方反驳**：\n{turn['bear_argument']}\n\n"

        message += "请根据以上记录，给出你的最终裁决。"
        return message

    async def execute(self, state: Dict[str, Any]) -> str:
        """执行裁决"""
        messages = self.build_messages(state)
        return await self.call_llm(messages)
