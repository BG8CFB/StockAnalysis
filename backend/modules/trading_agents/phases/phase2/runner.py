"""
Phase 2: 研究与辩论运行器

固定流程：看涨/看跌初始观点 → 辩论轮次 → 研究经理裁决 → 交易计划
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from modules.trading_agents.scheduler.state import WorkflowState


logger = logging.getLogger(__name__)


async def run_phase2(state: WorkflowState) -> WorkflowState:
    """
    运行 Phase 2: 研究与辩论

    流程:
    1. 看涨初始观点 + 看跌初始观点（并行）
    2. 循环辩论（可配置轮次）
    3. 研究经理裁决
    4. 交易计划制定

    Args:
        state: 工作流状态

    Returns:
        更新后的工作流状态
    """
    logger.info(f"[Phase 2] 开始研究与辩论")
    model_id = state.get_model_id("phase2")

    # 1. 初始观点（并行）
    logger.info("[Phase 2] 生成初始观点（看涨 + 看跌）")
    bull_task = _generate_bull_view(state, model_id)
    bear_task = _generate_bear_view(state, model_id)

    bull_report, bear_report = await asyncio.gather(bull_task, bear_task)

    state.bull_base_report = bull_report
    state.bear_base_report = bear_report

    # 2. 辩论轮次
    max_rounds = state.max_debate_rounds
    logger.info(f"[Phase 2] 开始辩论，共 {max_rounds} 轮")

    for round_num in range(max_rounds):
        logger.info(f"[Phase 2] 辩论第 {round_num + 1} 轮")

        # 并行执行看涨反驳和看跌反驳
        bull_rebuttal_task = _generate_bull_rebuttal(
            state, model_id, round_num, bear_report
        )
        bear_rebuttal_task = _generate_bear_rebuttal(
            state, model_id, round_num, bull_report
        )

        bull_rebuttal, bear_rebuttal = await asyncio.gather(
            bull_rebuttal_task, bear_rebuttal_task
        )

        # 记录辩论轮次
        debate_turn = {
            "round": round_num + 1,
            "bull_rebuttal": bull_rebuttal,
            "bear_rebuttal": bear_rebuttal,
            "timestamp": datetime.now().isoformat(),
        }
        state.debate_turns.append(debate_turn)

        # 更新用于下一轮的引用
        bull_report = bull_rebuttal
        bear_report = bear_rebuttal

    # 3. 研究经理裁决
    logger.info("[Phase 2] 研究经理裁决")
    manager_decision = await _generate_manager_decision(state, model_id)
    state.manager_decision = manager_decision

    # 4. 交易计划
    logger.info("[Phase 2] 制定交易计划")
    trade_plan = await _generate_trade_plan(state, model_id)
    state.trade_plan = trade_plan

    logger.info(f"[Phase 2] 完成，共 {len(state.debate_turns)} 轮辩论")
    return state


async def _generate_bull_view(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成看涨初始观点"""
    from core.ai import get_ai_service, AIMessage

    # 获取 Phase 1 报告摘要
    context = _build_phase1_context(state)

    prompt = f"""你是一位经验丰富的看涨研究员。

{context}

请基于第一阶段分析师团队的报告，构建看涨投资逻辑。

请：
1. 仔细阅读第一阶段所有分析师的报告
2. 提炼其中的看涨论据和投资机会
3. 构建完整的看涨投资逻辑
4. 给出明确的看涨建议

请输出完整的看涨分析报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是一位经验丰富的看涨研究员。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase2", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


async def _generate_bear_view(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成看跌初始观点"""
    from core.ai import get_ai_service, AIMessage

    context = _build_phase1_context(state)

    prompt = f"""你是一位经验丰富的看跌研究员。

{context}

请基于第一阶段分析师团队的报告，构建看跌投资逻辑。

请：
1. 仔细阅读第一阶段所有分析师的报告
2. 提炼其中的看跌论据和风险因素
3. 构建完整的看跌投资逻辑
4. 给出明确的看跌建议

请输出完整的看跌分析报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是一位经验丰富的看跌研究员。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase2", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


async def _generate_bull_rebuttal(
    state: WorkflowState,
    model_id: str,
    round_num: int,
    opponent_view: Dict[str, Any]
) -> Dict[str, Any]:
    """生成看涨反驳"""
    from core.ai import get_ai_service, AIMessage

    opponent_content = opponent_view.get("content", "")

    prompt = f"""你是看涨研究员。

对方（看跌研究员）的观点：

{opponent_content}

请针对对方的观点进行反驳，强化你的看涨论点。

请输出你的反驳报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是一位经验丰富的看涨研究员。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase2", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


async def _generate_bear_rebuttal(
    state: WorkflowState,
    model_id: str,
    round_num: int,
    opponent_view: Dict[str, Any]
) -> Dict[str, Any]:
    """生成看跌反驳"""
    from core.ai import get_ai_service, AIMessage

    opponent_content = opponent_view.get("content", "")

    prompt = f"""你是看跌研究员。

对方（看涨研究员）的观点：

{opponent_content}

请针对对方的观点进行反驳，强化你的看跌论点。

请输出你的反驳报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是一位经验丰富的看跌研究员。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase2", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


async def _generate_manager_decision(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成研究经理裁决"""
    from core.ai import get_ai_service, AIMessage

    # 构建辩论摘要
    debate_summary = _build_debate_summary(state)

    prompt = f"""你是研究经理，负责裁决双方的观点。

## 股票信息
- 股票代码：{state.stock_code}
- 交易日期：{state.trade_date}

## 辩论摘要
{debate_summary}

请作为研究经理：
1. 综合评估双方的论点和论据
2. 给出客观的裁决意见
3. 指出双方论点的强项和弱项
4. 提供你的专业判断

请输出裁决报告（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是研究经理，负责裁决辩论双方的观点。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase2", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


async def _generate_trade_plan(
    state: WorkflowState,
    model_id: str
) -> Dict[str, Any]:
    """生成交易计划"""
    from core.ai import get_ai_service, AIMessage

    debate_summary = _build_debate_summary(state)
    manager_decision = state.manager_decision.get("content", "") if state.manager_decision else ""

    prompt = f"""你是交易计划制定专家。

## 股票信息
- 股票代码：{state.stock_code}
- 交易日期：{state.trade_date}

## 辩论摘要
{debate_summary}

## 研究经理裁决
{manager_decision}

请基于以上信息，制定详细的交易计划，包括：
1. 交易建议（买入/卖出/持有）
2. 建议的入场点位
3. 止损位设置
4. 目标价位
5. 持仓周期建议
6. 风险提示

请输出交易计划（Markdown 格式）。
"""

    messages = [
        AIMessage(role="system", content="你是交易计划制定专家。"),
        AIMessage(role="user", content=prompt),
    ]

    ai_service = get_ai_service()
    response = await ai_service.chat_completion(
        user_id=state.user_id,
        messages=messages,
        model_id=model_id,
    )

    if response.usage:
        state.add_token_usage("phase2", model_id, response.usage)

    return {
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
    }


def _build_phase1_context(state: WorkflowState) -> str:
    """构建 Phase 1 报告上下文"""
    context_parts = ["## 第一阶段分析师报告摘要\n"]

    for report in state.analyst_reports:
        context_parts.append(f"""
### {report['agent_name']}
{report['content']}
""")

    return "\n".join(context_parts)


def _build_debate_summary(state: WorkflowState) -> str:
    """构建辩论摘要"""
    parts = ["## 辩论过程摘要\n"]

    # 初始观点
    if state.bull_base_report:
        parts.append("### 看涨初始观点\n")
        parts.append(state.bull_base_report.get("content", "")[:500] + "...\n")

    if state.bear_base_report:
        parts.append("### 看跌初始观点\n")
        parts.append(state.bear_base_report.get("content", "")[:500] + "...\n")

    # 辩论轮次
    for turn in state.debate_turns:
        parts.append(f"\n### 第 {turn['round']} 轮辩论\n")
        parts.append(f"**看涨反驳**: {turn['bull_rebuttal'].get('content', '')[:300]}...\n\n")
        parts.append(f"**看跌反驳**: {turn['bear_rebuttal'].get('content', '')[:300]}...\n")

    return "\n".join(parts)
