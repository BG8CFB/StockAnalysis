"""
Phase 4: 风险管理委员会主席

**版本**: v4.0 (LangChain 1.1.0 create_agent 重构版)
**最后更新**: 2026-01-15

综合评估风险，行使一票否决权。
"""

import logging
from typing import Dict, Any, Optional, List

from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent
from modules.trading_agents.models.state import WorkflowState
from modules.trading_agents.workflow.callbacks import WebSocketCallbackHandler

logger = logging.getLogger(__name__)


class RiskManager:
    """
    风险管理委员会主席

    综合评估风险，行使一票否决权。
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None,
        task_id: str = None,
        websocket_manager: Any = None,
    ):
        """
        初始化风险管理委员会主席

        Args:
            model: LLM 模型
            config: 智能体配置
            task_id: 任务 ID（用于回调推送）
            websocket_manager: WebSocket 管理器实例
        """
        self.model = model
        self.config = config or {}
        self.slug = "risk-manager"
        self.name = "风险管理委员会主席"
        self.task_id = task_id
        self.websocket_manager = websocket_manager
        # 创建回调处理器
        self.callbacks = []
        if self.task_id and self.websocket_manager:
            self.callbacks.append(WebSocketCallbackHandler(
                task_id=self.task_id,
                agent_slug=self.slug,
                agent_name=self.name,
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
你是风险管理委员会主席，你的任务是综合评估投资风险，并行使一票否决权。

# 职责
1. 评估整体风险水平（低/中/高）
2. 识别关键风险点
3. 给出风险控制建议
4. 在风险过高时行使否决权

# 推荐等级定义
- **STRONG_BUY**: 预期显著上涨，强烈推荐买入
- **BUY**: 预期上涨，推荐买入
- **HOLD**: 维持现有仓位
- **SELL**: 预期下跌，建议卖出
- **STRONG_SELL**: 预期显著下跌，强烈建议卖出

# 风险等级定义
- **LOW**: 低风险，本金安全性高
- **MEDIUM**: 中等风险，正常波动范围
- **HIGH**: 高风险，存在较大本金损失风险

# 输出格式
```markdown
# 风险评估报告

## 整体风险评级
**风险等级**: LOW / MEDIUM / HIGH
**是否批准**: ✅ 批准 / ❌ 否决

## 关键风险点
### 风险 1
- 描述
- 影响程度
- 应对措施

## 风险控制建议
[具体的风险控制措施]

## 最终推荐
**推荐等级**: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
**目标价位**: 买入 ¥XX.XX, 卖出 ¥XX.XX

## 结论
[综合风险评估结论]
```

{role_definition}
"""
        return prompt.strip()

    async def assess(
        self,
        state: WorkflowState,
        strategy_reports: List[Dict[str, Any]],
        investment_decision: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行风险评估

        Args:
            state: 工作流状态
            strategy_reports: 策略报告列表
            investment_decision: 投资决策

        Returns:
            评估结果
        """
        logger.info(f"[Phase 4] 风险管理委员会主席开始评估: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state, strategy_reports, investment_decision)
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

            # 解析决策
            decision = self._parse_decision(output)

            logger.info(
                f"[Phase 4] 风险管理委员会主席评估完成: {state.stock_code}, "
                f"批准: {decision.get('approved') if decision else 'N/A'}"
            )

            return {
                "output": output,
                "decision": decision,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 4] 风险管理委员会主席评估失败: {state.stock_code}, error={e}")

            return {
                "output": None,
                "decision": None,
                "error": str(e)
            }

    def _build_input_messages(
        self,
        state: WorkflowState,
        strategy_reports: List[Dict[str, Any]],
        investment_decision: Optional[Dict[str, Any]]
    ) -> list:
        """构建输入消息"""
        # 构建策略报告摘要
        reports_summary = "\n\n".join([
            f"## {report['name']}\n{report['output']}"
            for report in strategy_reports
            if report.get("output")
        ])

        decision_text = ""
        if investment_decision:
            decision_text = f"""
# 初始投资决策
- 推荐等级: {investment_decision.get('recommendation')}
- 风险等级: {investment_decision.get('risk_level')}
- 买入价位: {investment_decision.get('buy_price')}
- 卖出价位: {investment_decision.get('sell_price')}
"""

        prompt = f"""
请综合评估以下投资策略和决策：

# 股票信息
- 股票代码: {state.stock_code}
- 股票名称: {state.stock_name or '未知'}
- 市场: {state.market}
- 交易日期: {state.trade_date}

{decision_text}

# 策略分析师报告
{reports_summary}

请提供你的风险评估和最终推荐。
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

    def _parse_decision(self, output: Optional[str]) -> Optional[Dict[str, Any]]:
        """解析决策结果"""
        if not output:
            return None

        import re
        import json

        # 检查是否批准
        approved = None
        if "否决" in output or "❌" in output:
            approved = False
        elif "批准" in output or "✅" in output:
            approved = True

        # 提取推荐等级
        recommendation = None
        for rec in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
            if rec in output.upper():
                recommendation = rec
                break

        # 提取风险等级
        risk_level = None
        for risk in ["LOW", "MEDIUM", "HIGH"]:
            if risk in output.upper():
                risk_level = risk
                break

        if recommendation or approved is not None:
            return {
                "approved": approved if approved is not None else True,
                "recommendation": recommendation,
                "risk_level": risk_level
            }

        return None
