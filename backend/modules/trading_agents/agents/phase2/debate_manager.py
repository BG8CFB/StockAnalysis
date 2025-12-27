"""
第二阶段辩论管理器

控制辩论轮次循环，管理看涨和看跌研究员的交互。
"""

import logging
from typing import Dict, Any

from core.ai.llm.provider import Message

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt 构造器
# =============================================================================

class DebatePromptBuilder:
    """
    辩论提示词构造器

    为看涨和看跌研究员构造包含对方观点的提示词。
    """

    @staticmethod
    def build_bull_prompt(
        state: Dict[str, Any],
        round_idx: int = 0,
    ) -> str:
        """
        构造看涨研究员的提示词

        Args:
            state: 工作流状态
            round_idx: 当前辩论轮次

        Returns:
            完整的提示词
        """
        prompt = """你是一位经验丰富的看涨研究员。

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

        # 添加上下文信息
        prompt += f"""

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 分析师报告摘要
"""

        # 添加所有分析师的报告
        reports = state.get("analyst_reports", [])
        if reports:
            for report in reports:
                agent_name = report.get("agent_name", "分析师")
                content = report.get("content", "")
                prompt += f"\n### {agent_name}\n{content}\n"

        # 添加对手观点（如果是反驳轮次）
        if round_idx > 0 and state.get("debate_turns"):
            last_turn = state["debate_turns"][-1]
            bear_view = last_turn.get("bear_argument", "")

            if bear_view:
                prompt += f"""

## 对手观点（上一轮看跌研究员的观点）

<opponent_view>
{bear_view}
</opponent_view>

请针对以上观点进行反驳。
"""

        return prompt

    @staticmethod
    def build_bear_prompt(
        state: Dict[str, Any],
        round_idx: int = 0,
    ) -> str:
        """
        构造看跌研究员的提示词

        Args:
            state: 工作流状态
            round_idx: 当前辩论轮次

        Returns:
            完整的提示词
        """
        prompt = """你是一位经验丰富的看跌研究员。

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

        # 添加上下文信息
        prompt += f"""

## 股票信息
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

## 分析师报告摘要
"""

        # 添加所有分析师的报告
        reports = state.get("analyst_reports", [])
        if reports:
            for report in reports:
                agent_name = report.get("agent_name", "分析师")
                content = report.get("content", "")
                prompt += f"\n### {agent_name}\n{content}\n"

        # 添加对手观点（如果是反驳轮次）
        if round_idx > 0 and state.get("debate_turns"):
            last_turn = state["debate_turns"][-1]
            bull_view = last_turn.get("bull_argument", "")

            if bull_view:
                prompt += f"""

## 对手观点（上一轮看涨研究员的观点）

<opponent_view>
{bull_view}
</opponent_view>

请针对以上观点进行反驳。
"""

        return prompt


# =============================================================================
# 辩论管理器（用于独立管理辩论流程）
# =============================================================================

class DebateManager:
    """
    辩论管理器

    控制辩论轮次，管理看涨和看跌研究员的交互。
    """

    def __init__(
        self,
        bull_agent,
        bear_agent,
        max_rounds: int = 1,
    ):
        """
        初始化辩论管理器

        Args:
            bull_agent: 看涨研究员智能体
            bear_agent: 看跌研究员智能体
            max_rounds: 最大辩论轮次
        """
        self.bull_agent = bull_agent
        self.bear_agent = bear_agent
        self.max_rounds = max_rounds

    async def run_debate(self, state: Dict[str, Any]) -> None:
        """
        运行辩论流程

        Args:
            state: 工作流状态（会被更新）

        流程：
        1. Round 0: 生成初始观点
        2. Round 1..N: 交叉反驳
        3. 更新状态中的辩论历史
        """
        logger.info(f"开始辩论，最大轮次：{self.max_rounds}")

        # 初始化辩论历史
        if "debate_turns" not in state:
            state["debate_turns"] = []

        # 生成初始观点（Round 0）
        await self._generate_initial_views(state)

        # 进行多轮辩论
        for round_idx in range(1, self.max_rounds + 1):
            logger.info(f"辩论轮次 {round_idx}/{self.max_rounds}")
            await self._run_rebuttal_round(state, round_idx)

        logger.info("辩论完成")

    async def _generate_initial_views(self, state: Dict[str, Any]) -> None:
        """
        生成初始观点（Round 0）

        Args:
            state: 工作流状态
        """
        logger.info("生成初始观点")

        # 看涨方初始观点
        bull_prompt = DebatePromptBuilder.build_bull_prompt(state, round_idx=0)
        bull_view = await self.bull_agent.call_llm([
            Message(role="system", content=bull_prompt),
            Message(role="user", content="请基于分析师报告给出你的初始看涨观点。"),
        ])
        state["initial_bull_view"] = bull_view

        # 看跌方初始观点
        bear_prompt = DebatePromptBuilder.build_bear_prompt(state, round_idx=0)
        bear_view = await self.bear_agent.call_llm([
            Message(role="system", content=bear_prompt),
            Message(role="user", content="请基于分析师报告给出你的初始看跌观点。"),
        ])
        state["initial_bear_view"] = bear_view

        logger.info(f"初始观点生成完成：bull={len(bull_view)} chars, bear={len(bear_view)} chars")

    async def _run_rebuttal_round(self, state: Dict[str, Any], round_idx: int) -> None:
        """
        运行一轮反驳辩论

        Args:
            state: 工作流状态
            round_idx: 当前轮次
        """
        # 看涨方反驳
        bull_prompt = DebatePromptBuilder.build_bull_prompt(state, round_idx=round_idx)
        bull_arg = await self.bull_agent.call_llm([
            Message(role="system", content=bull_prompt),
            Message(role="user", content=f"请进行第 {round_idx} 轮看涨反驳。"),
        ])

        # 看跌方反驳
        bear_prompt = DebatePromptBuilder.build_bear_prompt(state, round_idx=round_idx)
        bear_arg = await self.bear_agent.call_llm([
            Message(role="system", content=bear_prompt),
            Message(role="user", content=f"请进行第 {round_idx} 轮看跌反驳。"),
        ])

        # 记录本轮辩论
        debate_turn = {
            "round_index": round_idx,
            "bull_argument": bull_arg,
            "bear_argument": bear_arg,
        }
        state["debate_turns"].append(debate_turn)

        logger.info(f"辩论轮次 {round_idx} 完成：bull={len(bull_arg)} chars, bear={len(bear_arg)} chars")


# =============================================================================
# LangGraph 节点函数
# =============================================================================

async def node_generate_initial_views(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph 节点：生成初始观点（Round 0）

    Args:
        state: 工作流状态

    Returns:
        更新后的状态
    """
    logger.info("LangGraph 节点：生成初始观点")

    # 这个节点会被 agent_engine.py 中的逻辑调用
    # 实际的辩论逻辑由 _execute_phase2 中的代码处理
    # 这里只是为了与 LangGraph 集成而保留的接口
    return state


async def node_debate_round(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph 节点：执行一轮辩论

    Args:
        state: 工作流状态

    Returns:
        更新后的状态
    """
    logger.info("LangGraph 节点：执行辩论轮次")

    # 这个节点会被 agent_engine.py 中的逻辑调用
    # 实际的辩论逻辑由 _execute_phase2 中的代码处理
    # 这里只是为了与 LangGraph 集成而保留的接口
    return state
