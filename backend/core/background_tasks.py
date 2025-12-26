# -*- coding: utf-8 -*-
"""
后台任务管理

负责创建和执行分析任务的后台任务逻辑。
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from modules.trading_agents.core.task_manager import get_task_manager
from modules.trading_agents.schemas import AnalysisTaskCreate
from modules.trading_agents.services.agent_config_service import get_agent_config_service
from modules.trading_agents.services.model_service import get_model_service
from modules.trading_agents.core.agent_engine import AgentWorkflowEngine
from modules.trading_agents.tools.registry import get_tool_registry
from modules.trading_agents.agents import create_phase1_agents, create_phase2_agents, create_phase3_agents, create_phase4_agents
from modules.trading_agents.services.report_service import get_report_service
from modules.trading_agents.websocket import get_ws_manager

logger = logging.getLogger(__name__)


async def create_analysis_task_background(
    user_id: str,
    request: AnalysisTaskCreate,
    config: Dict[str, Any]
) -> str:
    """
    后台任务：创建并执行分析任务

    此函数会在后台异步执行，避免阻塞 HTTP 响应。
    """
    task_manager = get_task_manager()
    ws_manager = get_ws_manager()

    # 1. 创建任务记录
    task_id = await task_manager.create_task(
        user_id=user_id,
        request=request,
        config=config
    )
    logger.info(f"Background task created: task_id={task_id}")

    # 2. 标记任务为运行中
    await task_manager.mark_task_running(task_id)

    # 3. 在后台异步执行工作流（不阻塞响应）
    asyncio.create_task(
        execute_analysis_workflow(
            task_id=task_id,
            user_id=user_id,
            request=request
        )
    )

    return task_id


async def execute_analysis_workflow(
    task_id: str,
    user_id: str,
    request: AnalysisTaskCreate
) -> None:
    """
    执行分析工作流

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        request: 分析任务请求
    """
    task_manager = get_task_manager()
    ws_manager = get_ws_manager()
    report_service = get_report_service()

    try:
        # 1. 加载用户智能体配置
        config_service = get_agent_config_service()
        user_config = await config_service.get_user_config(user_id, create_if_missing=True)

        if not user_config:
            raise Exception("无法加载用户智能体配置")

        # 2. 获取用户配置的 AI 模型
        model_service = get_model_service()
        model_id = user_config.phase1.model_id if user_config.phase1 else None

        if not model_id:
            # 使用默认模型
            model = await model_service.get_default_model(user_id=user_id)
        else:
            model = await model_service.get_model(model_id, user_id, is_admin=False)

        if not model:
            raise Exception("未找到可用的 AI 模型配置")

        # 3. 获取 LLM Provider 实例
        llm = await model_service.get_llm_provider(
            model_id=str(model.id),
            user_id=user_id,
            is_admin=False
        )

        if not llm:
            raise Exception("无法创建 LLM Provider 实例")

        # 4. 获取可用工具列表
        tool_registry = get_tool_registry()
        available_tools = tool_registry.list_available_tools()
        logger.info(f"可用工具数量: {len(available_tools)}")

        # 5. 创建工作流引擎
        workflow = AgentWorkflowEngine(
            llm=llm,
            config=user_config,
            ws_manager=ws_manager,
        )

        # 6. 注册所有阶段的智能体
        # 阶段1：分析师团队（需要工具）
        phase1_agents = create_phase1_agents(llm, tools=available_tools)
        for agent in phase1_agents:
            workflow.register_agent(agent)

        # 阶段2：辩论团队（不需要工具）
        if user_config.phase2 and user_config.phase2.enabled:
            phase2_agents = create_phase2_agents(llm)
            for agent in phase2_agents:
                workflow.register_agent(agent)

        # 阶段3：风险评估（不需要工具）
        if user_config.phase3 and user_config.phase3.enabled:
            phase3_agents = create_phase3_agents(llm)
            for agent in phase3_agents:
                workflow.register_agent(agent)

        # 阶段4：总结（不需要工具）
        if user_config.phase4 and user_config.phase4.enabled:
            phase4_agents = create_phase4_agents(llm)
            for agent in phase4_agents:
                workflow.register_agent(agent)

        # 7. 执行工作流
        result = await workflow.execute_workflow(
            task_id=task_id,
            user_id=user_id,
            request=request
        )

        # 7. 从结果中提取推荐和价格信息
        final_recommendation = None
        buy_price = None
        sell_price = None

        # 尝试从 trade_plan 中提取信息
        if result.get("trade_plan"):
            trade_plan = result["trade_plan"]
            # 简单的解析逻辑（可根据实际格式调整）
            if "买入" in trade_plan or "BUY" in trade_plan.upper():
                from modules.trading_agents.schemas import RecommendationEnum
                final_recommendation = RecommendationEnum.BUY

        # 8. 完成任务
        await task_manager.complete_task(
            task_id=task_id,
            final_recommendation=final_recommendation,
            buy_price=buy_price,
            sell_price=sell_price,
            token_usage=result.get("token_usage"),
        )

        # 9. 创建分析报告
        try:
            from modules.trading_agents.schemas import RecommendationEnum, RiskLevelEnum

            # 解析风险等级（从风险评估报告中）
            risk_level = RiskLevelEnum.MEDIUM
            if result.get("risk_assessment"):
                risk_text = result["risk_assessment"].lower()
                if "高" in risk_text or "high" in risk_text:
                    risk_level = RiskLevelEnum.HIGH
                elif "低" in risk_text or "low" in risk_text:
                    risk_level = RiskLevelEnum.LOW

            # 注意：create_report 从任务中获取 stock_code 和 trade_date
            await report_service.create_report(
                user_id=user_id,
                task_id=task_id,
                final_report=result.get("final_report", ""),
                recommendation=final_recommendation or RecommendationEnum.HOLD,
                risk_level=risk_level,
                buy_price=buy_price,
                sell_price=sell_price,
                token_usage=result.get("token_usage", {}),
            )
        except Exception as e:
            logger.error(f"创建分析报告失败: task_id={task_id}, error={e}")
            # 报告创建失败不影响任务完成状态

        logger.info(f"分析任务执行成功: task_id={task_id}")

    except Exception as e:
        logger.error(f"分析任务执行失败: task_id={task_id}, error={e}")

        # 标记任务失败
        await task_manager.fail_task(
            task_id=task_id,
            error_message=str(e),
            error_details={"type": type(e).__name__}
        )
