"""
Phase 4: 总结智能体

**版本**: v4.0 (新建)
**最后更新**: 2026-01-16

总结智能体，汇总所有分析结果，提供最终投资建议和价格预测。
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent


from modules.trading_agents.models.state import (
    WorkflowState,
    PhaseExecution,
    AgentExecution,
    TaskStatus,
)
from modules.trading_agents.config import get_enabled_agents
from modules.trading_agents.workflow.events import (
    create_phase_agents_event,
    create_agent_started_event,
    create_agent_completed_event,
)

logger = logging.getLogger(__name__)


class SummarizerAgent:
    """
    总结智能体

    汇总所有分析结果，提供最终投资建议和价格预测。
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化总结智能体

        Args:
            model: LLM 模型
            config: 智能体配置
        """
        self.model = model
        self.config = config or {}
        self.slug = config.get("slug", "summarizer")
        self.name = config.get("name", "总结智能体")
        self.agent = self._create_agent()

    def _create_agent(self):
        """创建智能体实例 (LangChain 1.1.0 create_agent API)"""
        system_prompt_str = self._build_system_prompt()

        # 使用 LangChain 1.1.0 的 create_agent
        graph = create_agent(
            model=self.model,
            tools=[],
            system_prompt=system_prompt_str,
            debug=False
        )

        return graph

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        role_definition = self.config.get("roleDefinition", "")

        prompt = f"""
# 角色
你是{self.name}，你的任务是汇总所有分析结果，提供最终投资建议和价格预测。

# 职责
1. 综合所有分析师报告，提炼核心观点
2. 整合多空辩论和策略分析结果
3. 给出明确的买入/卖出建议
4. 提供未来3天、1周、1个月的价格预测
5. 说明分析结论的置信度

# 推荐等级定义
- **STRONG_BUY**: 预期显著上涨，强烈推荐买入
- **BUY**: 预期上涨，推荐买入
- **HOLD**: 维持现有仓位
- **SELL**: 预期下跌，建议卖出
- **STRONG_SELL**: 预期显著下跌，强烈建议卖出

# 输出格式
```markdown
# 投资分析总结报告

## 核心结论
**推荐等级**: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
**置信度**: 高/中/低
**一句话总结**: [用一句话总结投资建议]

## 价格预测
### 短期预测（3天）
- 预测价位: ¥XX.XX - ¥XX.XX
- 涨跌幅: ±X%
- 风险提示: [说明]

### 中期预测（1周）
- 预测价位: ¥XX.XX - ¥XX.XX
- 涨跌幅: ±X%
- 风险提示: [说明]

### 长期预测（1个月）
- 预测价位: ¥XX.XX - ¥XX.XX
- 涨跌幅: ±X%
- 风险提示: [说明]

## 核心观点汇总
### 看涨因素
- [列出3-5个核心看涨因素]

### 看跌因素
- [列出3-5个核心看跌因素]

### 策略分析
- **激进策略**: [激进策略分析师观点]
- **中性策略**: [中性策略分析师观点]
- **保守策略**: [保守策略分析师观点]

## 风险提示
1. [列出主要风险点]
2. [说明风险控制建议]

## 系统信息
- 分析完成时间
- 涉及的分析师数量
- 数据来源和时效性
```

{role_definition}
"""
        return prompt.strip()

    async def summarize(
        self,
        state: WorkflowState
    ) -> Dict[str, Any]:
        """
        执行总结分析

        Args:
            state: 工作流状态

        Returns:
            总结结果
        """
        logger.info(f"[Phase 4] {self.name}开始总结: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state)
        try:
            # 调用智能体
            prompt_text = messages[0]["content"] if messages else "Please summarize."
            result = await self.agent.ainvoke({"messages": [{"role": "user", "content": prompt_text}]}, config={"recursion_limit": 10})

            # 提取输出
            output = self._extract_output(result)

            # 解析决策
            decision = self._parse_decision(output)

            logger.info(f"[Phase 4] {self.name}总结完成: {state.stock_code}, 推荐: {decision.get('recommendation') if decision else 'N/A'}")

            return {
                "slug": self.slug,
                "name": self.name,
                "output": output,
                "decision": decision,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 4] {self.name}总结失败: {state.stock_code}, error={e}")

            return {
                "slug": self.slug,
                "name": self.name,
                "output": None,
                "decision": None,
                "error": str(e)
            }

    def _build_input_messages(
        self,
        state: WorkflowState
    ) -> list:
        """构建输入消息"""
        # 构建分析师报告摘要
        analyst_summary = "\n\n".join([
            f"## {report['name']}\n{report['content'][:500]}..."
            for report in state.analyst_reports
            if report.get("content")
        ])

        # 构建辩论摘要
        debate_summary = ""
        if state.debate_turns:
            debate_summary = f"""
# 多空辩论摘要
共{len(state.debate_turns)}轮辩论
"""

            for turn in state.debate_turns:
                round_num = turn.get('round', 0)
                bull_view = turn.get('bull_view', '')[:300] if turn.get('bull_view') else ''
                bear_view = turn.get('bear_view', '')[:300] if turn.get('bear_view') else ''
                debate_summary += f"""
## 第{round_num}轮
**看涨观点**: {bull_view}...
**看跌观点**: {bear_view}...
"""

        # 构建投资决策摘要
        decision_summary = ""
        if state.investment_decision:
            decision = state.investment_decision
            decision_summary = f"""
# 投资组合经理决策
- 推荐等级: {decision.get('recommendation')}
- 风险等级: {decision.get('risk_level')}
- 买入价位: {decision.get('buy_price')}
- 卖出价位: {decision.get('sell_price')}
"""

        # 构建策略报告摘要
        strategy_summary = ""
        if state.strategy_reports:
            strategy_summary = "\n\n".join([
                f"## {report['name']}\n{report['content'][:300]}..."
                for report in state.strategy_reports
                if report.get("content")
            ])

        # 构建交易计划摘要
        trading_plan_summary = ""
        if state.trading_plan:
            trading_plan_summary = f"""
# 交易执行计划
{state.trading_plan.get('content', '')[:500]}...
"""

        prompt = f"""
请汇总以下所有分析结果，提供最终投资建议和价格预测：

# 股票信息
- 股票代码: {state.stock_code}
- 股票名称: {state.stock_name or '未知'}
- 市场: {state.market}
- 交易日期: {state.trade_date}

# Phase 1: 分析师团队报告
{analyst_summary}

{debate_summary}

{decision_summary}

# Phase 3: 策略风格分析
{strategy_summary}

{trading_plan_summary}

# 风险评估
- 风险批准: {state.risk_approval.get('approved') if state.risk_approval else 'N/A'}
- 最终推荐: {state.final_recommendation or '待定'}
- 风险等级: {state.risk_level or '待定'}

请提供你的总结报告，包括明确的买入/卖出建议和未来价格预测。
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

        # 提取推荐等级
        recommendation = None
        for rec in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
            if rec in output.upper():
                recommendation = rec
                break

        # 提取置信度
        confidence = None
        if "高置信度" in output or "置信度: 高" in output or "置信度：高" in output:
            confidence = "HIGH"
        elif "中置信度" in output or "置信度: 中" in output or "置信度：中" in output:
            confidence = "MEDIUM"
        elif "低置信度" in output or "置信度: 低" in output or "置信度：低" in output:
            confidence = "LOW"

        # 提取价格预测
        price_predictions = {}
        price_patterns = {
            "3天": r"短期预测.*?预测价位[：:]\s*¥?([\d.]+)\s*[-~—到]\s*¥?([\d.]+)",
            "1周": r"中期预测.*?预测价位[：:]\s*¥?([\d.]+)\s*[-~—到]\s*¥?([\d.]+)",
            "1个月": r"长期预测.*?预测价位[：:]\s*¥?([\d.]+)\s*[-~—到]\s*¥?([\d.]+)",
        }

        for period, pattern in price_patterns.items():
            match = re.search(pattern, output, re.DOTALL)
            if match:
                price_predictions[period] = {
                    "min": float(match.group(1)),
                    "max": float(match.group(2))
                }

        if recommendation or confidence or price_predictions:
            return {
                "recommendation": recommendation,
                "confidence": confidence,
                "price_predictions": price_predictions
            }

        return None


async def execute_phase4(
    state: WorkflowState,
    model: BaseChatModel,
    config: Dict[str, Any]
) -> WorkflowState:
    """
    执行 Phase 4: 总结智能体（必须执行）

    Args:
        state: 工作流状态
        model: LLM 模型
        config: 智能体配置

    Returns:
        更新后的工作流状态
    """
    # 获取 WebSocket 管理器
    from modules.trading_agents.api.websocket_manager import websocket_manager

    logger.info(f"[Phase 4] 开始执行, 任务ID: {state.task_id}")

    # 更新状态
    state.current_phase = 4
    state.status = TaskStatus.RUNNING

    # Phase 4 是必须执行的，不检查 enabled 配置
    # 获取智能体配置
    agents_config = get_enabled_agents(config, "phase4")

    # 发送阶段智能体列表事件
    phase_agents_event = create_phase_agents_event(
        task_id=state.task_id,
        phase=4,
        phase_name="总结智能体",
        execution_mode="serial",
        max_concurrency=1,
        agents=agents_config
    )
    await websocket_manager.broadcast_event(state.task_id, phase_agents_event)
    logger.info(f"[Phase 4] 已发送智能体列表事件, 智能体数量: {len(agents_config)}")

    # 创建总结智能体实例
    summarizer = None
    for agent_config in agents_config:
        slug = agent_config["slug"]
        if slug == "summarizer":
            summarizer = SummarizerAgent(model, agent_config)
            break

    # 如果没有配置总结智能体，使用默认配置创建
    if not summarizer:
        logger.warning("[Phase 4] 未配置总结智能体，使用默认配置")
        summarizer = SummarizerAgent(model, {
            "slug": "summarizer",
            "name": "总结智能体",
            "roleDefinition": ""
        })

    # 创建阶段执行记录
    phase4_execution = PhaseExecution(
        phase=4,
        phase_name="总结智能体",
        started_at=datetime.utcnow(),
        execution_mode="serial",
        max_concurrency=1
    )

    # 发送总结智能体开始事件
    await websocket_manager.broadcast_event(state.task_id, create_agent_started_event(
        task_id=state.task_id,
        agent_slug=summarizer.slug,
        agent_name=summarizer.name
    ))

    # 执行总结智能体
    result = await summarizer.summarize(state)

    # 发送总结智能体完成事件
    if result.get("output"):
        await websocket_manager.broadcast_event(state.task_id, create_agent_completed_event(
            task_id=state.task_id,
            agent_slug=summarizer.slug,
            agent_name=summarizer.name,
            token_usage={}  # 暂无 token 用量
        ))

    # 更新状态
    if result.get("output"):
        state.summary_report = {
            "content": result["output"],
            "timestamp": datetime.utcnow().isoformat()
        }

    if result.get("decision"):
        decision = result["decision"]
        # 更新最终推荐（总结智能体的最终建议）
        if decision.get("recommendation"):
            state.final_recommendation = decision["recommendation"]
        if decision.get("confidence"):
            state.summary_confidence = decision["confidence"]
        if decision.get("price_predictions"):
            state.price_predictions = decision["price_predictions"]

    # 更新执行记录
    phase4_execution.completed_at = datetime.utcnow()
    phase4_execution.status = TaskStatus.COMPLETED

    # 添加智能体执行记录
    phase4_execution.agents.append(
        AgentExecution(
            slug=summarizer.slug,
            name=summarizer.name,
            started_at=phase4_execution.started_at,
            completed_at=phase4_execution.completed_at,
            status=TaskStatus.COMPLETED
        )
    )

    state.phase_executions.append(phase4_execution)

    # 更新进度
    state.progress = 100.0
    state.status = TaskStatus.COMPLETED
    state.completed_at = datetime.utcnow()

    logger.info(f"[Phase 4] 完成, 最终推荐: {state.final_recommendation}")

    return state
