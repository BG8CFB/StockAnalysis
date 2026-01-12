"""
Phase 4: 总结报告运行器

汇总所有阶段信息，生成最终投资建议
"""

import logging
from typing import Dict, Any
from datetime import datetime
import re

from modules.trading_agents.scheduler.state import WorkflowState, RecommendationType


logger = logging.getLogger(__name__)


async def run_phase4(state: WorkflowState) -> WorkflowState:
    """
    运行 Phase 4: 总结报告

    汇总所有阶段信息，生成最终投资建议。

    Args:
        state: 工作流状态

    Returns:
        更新后的工作流状态
    """
    logger.info(f"[Phase 4] 生成最终总结报告")
    model_id = state.get_model_id("phase4")

    # 生成最终报告
    final_report = await _generate_final_report(state, model_id)

    state.final_report = final_report

    # 从报告中提取投资建议
    recommendation = _extract_recommendation(final_report.get("content", ""))
    state.recommendation = recommendation

    logger.info(f"[Phase 4] 完成，投资建议: {recommendation}")
    return state


async def _generate_final_report(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成最终总结报告"""
    from core.ai import get_ai_service, AIMessage

    # 构建完整上下文
    context = _build_full_context(state)

    prompt = f"""你是首席投资分析师，负责总结整个分析流程并给出最终投资建议。

{context}

请汇总以上所有信息，生成最终投资分析报告，包括：

1. **执行摘要**
   - 股票代码和基本信息
   - 最终投资建议（强烈买入/买入/持有/卖出/强烈卖出）
   - 核心论点（3-5 条）

2. **分析师团队观点汇总**
   - 技术分析要点
   - 基本面分析要点
   - 其他关键发现

3. **辩论过程总结**
   - 看涨论点
   - 看跌论点
   - 研究经理裁决

4. **风险评估**
   - 首席风控官的风险评级
   - 主要风险点
   - 风险控制建议

5. **交易计划**
   - 具体操作建议
   - 入场点位
   - 止损位
   - 目标价

6. **最终投资建议**
   - 明确的建议：强烈买入/买入/持有/卖出/强烈卖出
   - 建议理由
   - 适用投资者类型

请输出完整的最终投资分析报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是首席投资分析师。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase4", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


def _extract_recommendation(report_content: str) -> str:
    """
    从报告内容中提取投资建议

    Args:
        report_content: 报告内容

    Returns:
        投资建议（STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL）
    """
    content_lower = report_content.lower()

    # 定义关键词映射
    keywords = {
        RecommendationType.STRONG_BUY.value: ["强烈买入", "强烈建议买入", "strong buy"],
        RecommendationType.BUY.value: ["买入", "建议买入", "buy"],
        RecommendationType.HOLD.value: ["持有", "观望", "hold"],
        RecommendationType.SELL.value: ["卖出", "建议卖出", "sell"],
        RecommendationType.STRONG_SELL.value: ["强烈卖出", "强烈建议卖出", "strong sell"],
    }

    # 按优先级检查（强烈买入 > 买入 > 持有 > 卖出 > 强烈卖出）
    for rec_type, kw_list in keywords.items():
        for kw in kw_list:
            if kw in content_lower:
                return rec_type

    # 默认返回持有
    return RecommendationType.HOLD.value


def _build_full_context(state: WorkflowState) -> str:
    """构建完整的上下文信息"""
    parts = [
        "## 股票信息\n",
        f"- 股票代码：{state.stock_code}\n",
        f"- 交易日期：{state.trade_date}\n",
        f"- 任务 ID：{state.task_id}\n",
    ]

    # Phase 1: 分析师报告
    if state.analyst_reports:
        parts.append("\n## 第一阶段：分析师团队报告\n")
        for report in state.analyst_reports:
            parts.append(f"\n### {report['agent_name']}\n")
            parts.append(f"{report['content'][:800]}...\n")

    # Phase 2: 研究与辩论
    if state.bull_base_report and state.bear_base_report:
        parts.append("\n## 第二阶段：研究与辩论\n")

        parts.append("\n### 看涨观点\n")
        parts.append(f"{state.bull_base_report.get('content', '')[:500]}...\n")

        parts.append("\n### 看跌观点\n")
        parts.append(f"{state.bear_base_report.get('content', '')[:500]}...\n")

        if state.debate_turns:
            parts.append(f"\n### 辩论轮次（共 {len(state.debate_turns)} 轮）\n")
            for turn in state.debate_turns:
                parts.append(f"\n#### 第 {turn['round']} 轮\n")
                parts.append(f"看涨反驳: {turn['bull_rebuttal'].get('content', '')[:200]}...\n")
                parts.append(f"看跌反驳: {turn['bear_rebuttal'].get('content', '')[:200]}...\n")

        if state.manager_decision:
            parts.append("\n### 研究经理裁决\n")
            parts.append(f"{state.manager_decision.get('content', '')[:500]}...\n")

        if state.trade_plan:
            parts.append("\n### 交易计划\n")
            parts.append(f"{state.trade_plan.get('content', '')[:500]}...\n")

    # Phase 3: 风险评估
    if state.risk_assessments:
        parts.append("\n## 第三阶段：风险评估\n")

        type_names = {
            "aggressive": "激进派",
            "conservative": "保守派",
            "neutral": "中性派",
        }

        for assessment in state.risk_assessments:
            type_name = type_names.get(assessment["type"], assessment["type"])
            parts.append(f"\n### {type_name}评估\n")
            parts.append(f"{assessment['report'].get('content', '')[:500]}...\n")

        if state.cro_summary:
            parts.append("\n### 首席风控官总结\n")
            parts.append(f"{state.cro_summary.get('content', '')[:600]}...\n")

    return "\n".join(parts)
