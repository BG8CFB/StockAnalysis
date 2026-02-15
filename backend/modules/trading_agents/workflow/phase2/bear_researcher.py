"""
Phase 2: 看跌分析师

从空头角度寻找风险和卖出信号。

**版本**: v3.2 (LangChain create_tool_calling_agent 重构版)
**最后更新**: 2026-01-15
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from langchain.agents import create_agent
from modules.trading_agents.models.state import WorkflowState, TaskStatus
from modules.trading_agents.workflow.callbacks import WebSocketCallbackHandler

logger = logging.getLogger(__name__)


class BearResearcher:
    """
    看跌分析师

    从空头角度寻找负面因素和估值风险。
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None,
        task_id: str = None,
        websocket_manager: Any = None,
    ):
        """
        初始化看跌分析师

        Args:
            model: LLM 模型
            config: 智能体配置
            task_id: 任务 ID（用于回调推送）
            websocket_manager: WebSocket 管理器实例
        """
        self.model = model
        self.config = config or {}
        self.task_id = task_id
        self.websocket_manager = websocket_manager
        # 创建回调处理器
        self.callbacks = []
        if self.task_id and self.websocket_manager:
            self.callbacks.append(WebSocketCallbackHandler(
                task_id=self.task_id,
                agent_slug="bear_researcher",
                agent_name="看跌分析师",
                websocket_manager=self.websocket_manager,
            ))
        self.agent = self._create_agent()

    def _create_agent(self):
        """创建智能体实例 (LangChain 1.1.0 create_agent API)"""
        system_prompt_str = self._build_system_prompt()
        # 使用 LangChain 1.1.0 的 create_agent
        # 注意: callbacks 不能在这里传递，需要在 ainvoke 时通过 config 传递
        graph = create_agent(
            model=self.model,
            tools=[],
            system_prompt=system_prompt_str,
            debug=False,
        )
        return graph

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        role_definition = self.config.get("roleDefinition", "")

        prompt = f"""
# 角色
你是一名看跌分析师，你的任务是寻找负面因素、估值风险，构建做空投资方案。

# 职责
1. 基于分析师报告和看涨观点，寻找反驳论据
2. 识别潜在的风险和陷阱
3. 给出具体的卖出建议和止损价位

# 工作流程
1. 首先阅读所有分析师的报告
2. 阅读看涨分析师的观点
3. 寻找反驳论据（质疑看涨逻辑，指出风险）
4. 识别潜在风险（基本面恶化、估值过高、政策风险等）
5. 构建完整的做空投资逻辑

# 输出格式
```markdown
# 看跌投资方案

## 核心风险逻辑
[一句话总结看空理由]

## 看涨观点质疑
### 对看涨因素 1 的反驳
- 看涨观点
- 反驳论据
- 结论

### 估值质疑
- ...

## 风险因素分析
### 风险 1
- 描述
- 影响程度
- 触发条件

## 卖出建议
- 推荐等级: HOLD / SELL / STRONG_SELL
- 止损价位
- 做空目标价（如适用）

## 风险提示
[如果市场好转，可能面临的风险]
```

{role_definition}
"""
        return prompt.strip()

    async def analyze(
        self,
        state: WorkflowState,
        analyst_reports: List[Dict[str, Any]],
        bull_view: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行看跌分析

        Args:
            state: 工作流状态
            analyst_reports: 分析师报告列表
            bull_view: 看涨观点（用于反驳）

        Returns:
            分析结果
        """
        logger.info(f"[Phase 2] 看跌分析师开始分析: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state, analyst_reports, bull_view)

        try:
            # 调用智能体 (使用 LangGraph create_agent 的正确输入格式)
            prompt_text = messages[0]["content"] if messages else "Please analyze."
            # 通过 config 传递 callbacks
            config = {"recursion_limit": 10}
            if self.callbacks:
                from langchain_core.callbacks import CallbackManager
                config["configurable"] = {"callbacks": CallbackManager(self.callbacks)}
            result = await self.agent.ainvoke({"messages": [{"role": "user", "content": prompt_text}]}, config=config)

            # 提取输出
            output = self._extract_output(result)

            logger.info(f"[Phase 2] 看跌分析师分析完成: {state.stock_code}")

            return {
                "role": "bear",
                "output": output,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 2] 看跌分析师分析失败: {state.stock_code}, error={e}")

            return {
                "role": "bear",
                "output": None,
                "error": str(e)
            }

    def _build_input_messages(
        self,
        state: WorkflowState,
        analyst_reports: List[Dict[str, Any]],
        bull_view: Optional[str]
    ) -> List[Dict[str, Any]]:
        """构建输入消息"""
        # 构建分析师报告摘要
        reports_summary = "\n\n".join([
            f"## {report['name']}\n{report['content']}"
            for report in analyst_reports
        ])
        bull_section = f"# 看涨观点\n{bull_view}" if bull_view else ""

        prompt = f"""
请基于以下分析师报告，从看跌角度分析股票 {state.stock_code}:

# 分析师报告
{reports_summary}

{bull_section}

请提供你的看跌投资方案，包括：
1. 核心风险逻辑
2. 看涨观点质疑
3. 风险因素分析
4. 卖出建议
5. 风险提示
"""

        return [{"role": "user", "content": prompt.strip()}]

    def _extract_output(self, result: Any) -> Optional[str]:
        """从结果中提取输出"""
        if isinstance(result, dict):
            # AgentExecutor format: {"output": "..."}
            output = result.get("output")
            if output:
                return str(output)

            # LangGraph format
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    return last_message.content
                elif isinstance(last_message, dict):
                    return last_message.get("content")

        if isinstance(result, str):
            return result

        return str(result)
