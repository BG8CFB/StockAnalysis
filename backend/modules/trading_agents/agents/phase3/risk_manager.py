"""
第三阶段风险讨论管理器

协调激进派、保守派和中性派的讨论。
"""

import logging
from typing import Dict, Any, List

from core.ai.llm.provider import Message

logger = logging.getLogger(__name__)


class RiskDiscussionManager:
    """
    风险讨论管理器
    
    管理多方风险评估讨论流程。
    """
    
    def __init__(
        self,
        aggressive_agent,
        conservative_agent,
        neutral_agent,
        max_rounds: int = 1
    ):
        self.aggressive = aggressive_agent
        self.conservative = conservative_agent
        self.neutral = neutral_agent
        self.max_rounds = max_rounds

    async def run_discussion(self, state: Dict[str, Any]) -> None:
        """
        运行风险讨论
        
        Args:
            state: 工作流状态
        """
        logger.info(f"开始风险讨论，最大轮次：{self.max_rounds}")
        
        if "risk_discussion_turns" not in state:
            state["risk_discussion_turns"] = []
            
        # 初始发言（并行）
        await self._run_round(state, round_idx=1)
        
        # 如果需要多轮，可以在此扩展
        # 目前简化为一轮各自陈述，然后由 CRO 总结
        
        logger.info("风险讨论完成")

    async def _run_round(self, state: Dict[str, Any], round_idx: int) -> None:
        """运行一轮讨论"""
        import asyncio
        
        tasks = [
            self.aggressive.execute(state),
            self.conservative.execute(state),
            self.neutral.execute(state)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        turn = {
            "round_index": round_idx,
            "aggressive_view": results[0] if not isinstance(results[0], Exception) else f"Error: {results[0]}",
            "conservative_view": results[1] if not isinstance(results[1], Exception) else f"Error: {results[1]}",
            "neutral_view": results[2] if not isinstance(results[2], Exception) else f"Error: {results[2]}",
        }
        
        state["risk_discussion_turns"].append(turn)
