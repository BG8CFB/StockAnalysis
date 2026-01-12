"""
Phase 3: 风险评估运行器

固定流程：三派评估（可并行）→ CRO 总结
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from modules.trading_agents.scheduler.state import WorkflowState


logger = logging.getLogger(__name__)


async def run_phase3(state: WorkflowState) -> WorkflowState:
    """
    运行 Phase 3: 风险评估

    流程:
    1. 激进派评估
    2. 保守派评估
    3. 中性派评估
    4. 首席风控官总结

    Args:
        state: 工作流状态

    Returns:
        更新后的工作流状态
    """
    logger.info(f"[Phase 3] 开始风险评估")
    model_id = state.get_model_id("phase3")

    # 三派评估（可并行）
    logger.info("[Phase 3] 三派风险评估（激进 + 保守 + 中性）")
    aggressive_task = _generate_aggressive_assessment(state, model_id)
    conservative_task = _generate_conservative_assessment(state, model_id)
    neutral_task = _generate_neutral_assessment(state, model_id)

    aggressive_report, conservative_report, neutral_report = await asyncio.gather(
        aggressive_task, conservative_task, neutral_task
    )

    state.risk_assessments = [
        {"type": "aggressive", "report": aggressive_report},
        {"type": "conservative", "report": conservative_report},
        {"type": "neutral", "report": neutral_report},
    ]

    # CRO 总结
    logger.info("[Phase 3] 首席风控官总结")
    cro_summary = await _generate_cro_summary(state, model_id)
    state.cro_summary = cro_summary

    logger.info(f"[Phase 3] 完成")
    return state


async def _generate_aggressive_assessment(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成激进派风险评估"""
    from core.ai import get_ai_service, AIMessage

    # 构建上下文
    context = _build_phase_context(state)

    prompt = f"""你是激进派风险分析师。

{context}

请从激进派的角度进行风险评估：
1. 重点关注潜在收益
2. 对风险有较高的容忍度
3. 寻找高增长机会
4. 给出激进的投资建议

请输出风险评估报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是激进派风险分析师。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase3", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


async def _generate_conservative_assessment(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成保守派风险评估"""
    from core.ai import get_ai_service, AIMessage

    context = _build_phase_context(state)

    prompt = f"""你是保守派风险分析师。

{context}

请从保守派的角度进行风险评估：
1. 重点关注风险控制
2. 优先考虑资本安全
3. 谨慎评估收益预期
4. 给出保守的投资建议

请输出风险评估报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是保守派风险分析师。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase3", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


async def _generate_neutral_assessment(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成中性派风险评估"""
    from core.ai import get_ai_service, AIMessage

    context = _build_phase_context(state)

    prompt = f"""你是中性派风险分析师。

{context}

请从中性派的角度进行风险评估：
1. 平衡收益和风险
2. 给出客观的分析
3. 提供量化的风险评估
4. 给出中性的投资建议

请输出风险评估报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是中性派风险分析师。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase3", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


async def _generate_cro_summary(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成首席风控官总结"""
    from core.ai import get_ai_service, AIMessage

    # 构建三派评估摘要
    assessments_summary = _build_assessments_summary(state)

    prompt = f"""你是首席风控官（CRO）。

## 股票信息
- 股票代码：{state.stock_code}
- 交易日期：{state.trade_date}

## 三派风险评估摘要
{assessments_summary}

请作为首席风控官：
1. 综合三派的评估意见
2. 给出最终的风险评级
3. 明确指出主要风险点
4. 提供风险控制建议
5. 给出投资建议（买入/卖出/持有）

请输出风控总结报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是首席风控官（CRO）。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase3", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


def _build_phase_context(state: WorkflowState) -> str:
    """构建前两阶段的上下文"""
    parts = [
        f"## 股票信息\n",
        f"- 股票代码：{state.stock_code}\n",
        f"- 交易日期：{state.trade_date}\n",
    ]

    # Phase 1 报告摘要
    if state.analyst_reports:
        parts.append("\n## 第一阶段分析师报告摘要\n")
        for report in state.analyst_reports[:3]:  # 只取前3份
            parts.append(f"### {report['agent_name']}\n")
            parts.append(f"{report['content'][:300]}...\n")

    # Phase 2 交易计划摘要
    if state.trade_plan:
        parts.append("\n## 第二阶段交易计划\n")
        parts.append(f"{state.trade_plan.get('content', '')[:500]}...\n")

    return "\n".join(parts)


def _build_assessments_summary(state: WorkflowState) -> str:
    """构建三派评估摘要"""
    parts = []

    for assessment in state.risk_assessments:
        type_name = {
            "aggressive": "激进派",
            "conservative": "保守派",
            "neutral": "中性派",
        }.get(assessment["type"], assessment["type"])

        parts.append(f"\n### {type_name}评估\n")
        parts.append(f"{assessment['report'].get('content', '')[:400]}...\n")

    return "\n".join(parts)
