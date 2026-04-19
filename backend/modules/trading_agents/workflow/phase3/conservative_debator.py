"""
Phase 4: 保守策略分析师

**版本**: v4.0 (LangChain 1.1.0 create_agent 重构版)
**最后更新**: 2026-01-15

本金安全优先，防御性资产配置。
"""

import logging
from typing import Any, Dict, Optional

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from modules.trading_agents.models.state import WorkflowState
from modules.trading_agents.workflow.callbacks import WebSocketCallbackHandler

logger = logging.getLogger(__name__)


class ConservativeDebator:
    """
    保守策略分析师

    本金安全优先，防御性资产配置。
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        websocket_manager: Any = None,
    ):
        """
        初始化保守策略分析师

        Args:
            model: LLM 模型
            config: 智能体配置
            task_id: 任务 ID（用于回调推送）
            websocket_manager: WebSocket 管理器实例
        """
        self.model = model
        self.config = config or {}
        self.slug = "conservative-debator"
        self.name = "保守策略分析师"
        self.task_id = task_id
        self.websocket_manager = websocket_manager
        # 创建回调处理器
        self.callbacks = []
        if self.task_id and self.websocket_manager:
            self.callbacks.append(
                WebSocketCallbackHandler(
                    task_id=self.task_id,
                    agent_slug=self.slug,
                    agent_name=self.name,
                    websocket_manager=self.websocket_manager,
                )
            )
        self.agent = self._create_agent()

    def _create_agent(self) -> Any:
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
你是保守策略分析师，你的任务是本金安全优先，防御性资产配置。

# 职责
1. 下行保护：最大回撤控制
2. 股息率：稳定的现金流回报
3. 估值安全：足够的安全边际

# 分析维度
- **下行保护**: 最大回撤控制
- **股息率**: 稳定的现金流
- **估值安全**: 安全边际
- **本金安全**: 防御性资产配置

# 输出格式
```markdown
# 保守策略分析师报告

## 核心观点
[一句话总结你的核心观点]

## 下行风险分析
[最大回撤控制分析]

## 股息收益评估
[稳定的现金流回报评估]

## 结论
[基于保守策略风格得出的结论]

## 建议
[具体的投资建议]
```

{role_definition}
"""
        return prompt.strip()

    async def analyze(
        self, state: WorkflowState, investment_decision: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行策略分析

        Args:
            state: 工作流状态
            investment_decision: 投资决策

        Returns:
            分析结果
        """
        logger.info(f"[Phase 4] 保守策略分析师开始分析: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state, investment_decision)
        try:
            # 调用智能体 (使用 LangGraph create_agent 的正确输入格式)
            prompt_text = messages[0]["content"] if messages else "Please analyze."
            # 通过 config 传递 callbacks
            config: dict[str, Any] = {"recursion_limit": 10}
            if self.callbacks:
                from langchain_core.callbacks import CallbackManager

                config["configurable"] = {"callbacks": CallbackManager(self.callbacks)}  # type: ignore[arg-type]
            result = await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt_text}]}, config=config
            )

            # 提取输出
            output = self._extract_output(result)

            logger.info(f"[Phase 4] 保守策略分析师分析完成: {state.stock_code}")

            return {"slug": self.slug, "name": self.name, "output": output, "error": None}

        except Exception as e:
            logger.error(f"[Phase 4] 保守策略分析师分析失败: {state.stock_code}, error={e}")

            return {"slug": self.slug, "name": self.name, "output": None, "error": str(e)}

    def _build_input_messages(
        self, state: WorkflowState, investment_decision: Optional[Dict[str, Any]]
    ) -> list:
        """构建输入消息"""
        decision_text = ""
        if investment_decision:
            decision_text = f"""
# 投资决策
- 推荐等级: {investment_decision.get('recommendation')}
- 风险等级: {investment_decision.get('risk_level')}
- 买入价位: {investment_decision.get('buy_price')}
- 卖出价位: {investment_decision.get('sell_price')}
"""

        prompt = f"""
请以保守策略分析师的视角，评估以下投资决策：

# 股票信息
- 股票代码: {state.stock_code}
- 股票名称: {state.stock_name or '未知'}
- 市场: {state.market}
- 交易日期: {state.trade_date}

{decision_text}

请提供你的策略分析和建议。
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
                    return str(last_message.content)
                elif isinstance(last_message, dict):
                    return str(last_message.get("content", ""))

        if isinstance(result, str):
            return result

        return str(result)
