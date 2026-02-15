"""
Phase 2: 研究经理（投资组合经理）

综合正反双方观点，做出最终投资决策。

**版本**: v4.0 (LangChain 1.1.0 create_agent 重构版)
**最后更新**: 2026-01-15
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from langchain.agents import create_agent
from modules.trading_agents.models.state import WorkflowState, TaskStatus
from modules.trading_agents.workflow.callbacks import WebSocketCallbackHandler

logger = logging.getLogger(__name__)


class ResearchManager:
    """
    研究经理（投资组合经理）

    综合分析看涨和看跌双方的观点，做出最终的投资决策。
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None,
        task_id: str = None,
        websocket_manager: Any = None,
    ):
        """
        初始化研究经理

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
                agent_slug="research_manager",
                agent_name="研究经理",
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
你是一名投资组合经理，你的任务是综合分析看涨和看跌双方的观点，做出最终的投资决策。

# 职责
1. 权衡双方论据的强度和可信度
2. 评估风险收益比
3. 给出明确的投资建议：买入/持有/卖出
4. 给出目标价位和风险等级

# 工作流程
1. 阅读看涨分析师的投资方案
2. 阅读看跌分析师的投资方案
3. 权衡双方论据（看涨因素的可靠性、看跌风险的严重性）
4. 评估风险收益比
5. 做出最终投资决策

# 推荐等级定义
- **STRONG_BUY**: 预期显著上涨（>20%），强烈推荐买入
- **BUY**: 预期上涨（>5%），推荐买入
- **HOLD**: 维持现有仓位，涨跌空间有限
- **SELL**: 预期下跌（>5%），建议卖出
- **STRONG_SELL**: 预期显著下跌（>20%），强烈建议卖出

# 风险等级定义
- **LOW**: 低风险，本金安全性高
- **MEDIUM**: 中等风险，正常波动范围
- **HIGH**: 高风险，存在较大本金损失风险

# 输出格式（JSON）
```json
{{
    "recommendation": "STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL",
    "risk_level": "LOW/MEDIUM/HIGH",
    "buy_price": 10.50,
    "sell_price": 12.00,
    "reasoning": "决策理由",
    "key_factors": ["关键因素1", "关键因素2"],
    "risk_warnings": ["风险提示1", "风险提示2"]
}}
```

# 最终报告格式
```markdown
# 投资决策报告

## 投资建议
**推荐等级**: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
**风险等级**: LOW / MEDIUM / HIGH
**目标价位**: 买入 ¥10.50, 卖出 ¥12.00

## 决策理由
[综合说明做出此决策的理由]

## 关键因素
### 看涨因素
1. [因素1]
2. [因素2]

### 看跌风险
1. [风险1]
2. [风险2]

## 风险收益评估
- 预期收益: [百分比]
- 风险等级: [LOW/MEDIUM/HIGH]
- 风险收益比: [数值]

## 操作建议
[具体操作建议]

## 风险提示
[列出主要风险]
```

{role_definition}
"""
        return prompt.strip()

    async def decide(
        self,
        state: WorkflowState,
        bull_view: str,
        bear_view: str
    ) -> Dict[str, Any]:
        """
        做出投资决策

        Args:
            state: 工作流状态
            bull_view: 看涨观点
            bear_view: 看跌观点

        Returns:
            决策结果
        """
        logger.info(f"[Phase 2] 研究经理开始决策: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state, bull_view, bear_view)
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

            # 解析决策（尝试从输出中提取 JSON）
            decision = self._parse_decision(output)

            logger.info(
                f"[Phase 2] 研究经理决策完成: {state.stock_code}, "
                f"推荐: {decision.get('recommendation')}, "
                f"风险: {decision.get('risk_level')}"
            )

            return {
                "role": "manager",
                "output": output,
                "decision": decision,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 2] 研究经理决策失败: {state.stock_code}, error={e}")

            return {
                "role": "manager",
                "output": None,
                "decision": None,
                "error": str(e)
            }

    def _build_input_messages(
        self,
        state: WorkflowState,
        bull_view: str,
        bear_view: str
    ) -> List[Dict[str, Any]]:
        """构建输入消息"""
        prompt = f"""
请基于以下看涨和看跌观点，做出投资决策：

# 股票信息
- 股票代码: {state.stock_code}
- 股票名称: {state.stock_name or '未知'}
- 市场: {state.market}
- 交易日期: {state.trade_date}

# 看涨观点
{bull_view}

# 看跌观点
{bear_view}

请综合评估，做出最终投资决策。
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

        # 尝试从输出中提取 JSON
        json_pattern = r'\{[^}]*"recommendation"[^}]*\}'
        matches = re.findall(json_pattern, output, re.DOTALL)

        for match in matches:
            try:
                decision = json.loads(match)
                # 验证必需字段
                if "recommendation" in decision:
                    return decision
            except json.JSONDecodeError:
                continue

        # 如果没有找到 JSON，尝试从文本中提取
        recommendation = None
        risk_level = None

        # 提取推荐等级
        for rec in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
            if rec in output.upper():
                recommendation = rec
                break

        # 提取风险等级
        for risk in ["LOW", "MEDIUM", "HIGH"]:
            if risk in output.upper():
                risk_level = risk
                break

        # 提取价位
        buy_price = self._extract_price(output, "买入")
        sell_price = self._extract_price(output, "卖出")

        if recommendation:
            return {
                "recommendation": recommendation,
                "risk_level": risk_level or "MEDIUM",
                "buy_price": buy_price,
                "sell_price": sell_price
            }

        return None

    def _extract_price(self, text: str, keyword: str) -> Optional[float]:
        """从文本中提取价格"""
        import re

        # 查找 "买入 ¥10.50" 或 "买入价: 10.50" 等模式
        patterns = [
            rf'{keyword}\s*[:：]?\s*[¥￥]?\s*(\d+\.?\d*)',
            rf'{keyword}\s*价\s*[:：]?\s*[¥￥]?\s*(\d+\.?\d*)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    return float(matches[0])
                except ValueError:
                    continue

        return None
