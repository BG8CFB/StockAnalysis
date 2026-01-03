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
from core.ai.model import get_model_service
from modules.trading_agents.core.agent_engine import AgentWorkflowEngine
from modules.trading_agents.services.report_service import get_report_service
from modules.trading_agents.websocket import get_ws_manager
from modules.trading_agents.tools import get_tool_registry

logger = logging.getLogger(__name__)


async def _resolve_model_with_fallback(
    model_service,
    requested_model_id: Optional[str],
    user_settings,
    model_type: str,  # "data_collection" or "debate"
    user_id: str
):
    """
    解析模型（带回退机制）

    回退顺序：
    1. 任务参数指定的模型
    2. 用户默认模型
    3. 系统默认模型

    Args:
        model_service: 模型服务
        requested_model_id: 任务参数指定的模型 ID
        user_settings: 用户设置
        model_type: 模型类型（用于日志）
        user_id: 用户 ID

    Returns:
        可用的模型

    Raises:
        Exception: 所有模型都不可用时
    """
    model = None
    source = None
    user_model_id = None

    # 优先级1：任务参数指定
    if requested_model_id:
        model = await model_service.get_model(requested_model_id, user_id, is_admin=False)
        if model:
            source = f"任务参数指定({model.name})"
            logger.info(f"使用{model_type}模型: {source}")
            return model
        else:
            logger.warning(f"任务参数指定的{model_type}模型不可用: {requested_model_id}")

    # 优先级2：用户默认模型
    if user_settings and user_settings.trading_agents_settings:
        user_model_id = getattr(
            user_settings.trading_agents_settings,
            f"{model_type}_model_id",
            None
        )
        if user_model_id:
            model = await model_service.get_model(user_model_id, user_id, is_admin=False)
            if model:
                source = f"用户默认模型({model.name})"
                logger.info(f"使用{model_type}模型: {source}")
                return model
            else:
                logger.warning(f"用户默认的{model_type}模型不可用: {user_model_id}")

    # 优先级3：系统默认模型
    model = await model_service.get_default_model(user_id=user_id)
    if model:
        source = f"系统默认模型({model.name})"
        logger.info(f"使用{model_type}模型: {source}")
        return model

    # 全部不可用
    raise Exception(
        f"无可用的{model_type}模型。"
        f"任务参数指定: {requested_model_id}, "
        f"用户默认: {user_model_id if user_settings else 'None'}, "
        f"系统默认: 不可用"
    )


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
    ws_manager = await get_ws_manager()
    report_service = get_report_service()

    # 用于并发控制
    # 统一处理：单股任务使用 task_id 作为自己的 batch_id
    # 这样可以确保单股任务和批量任务使用相同的资源管理逻辑
    batch_id = task_id  # 默认值，单股任务使用 task_id 作为 batch_id
    data_collection_model_id = None
    debate_model_id = None

    try:
        # 1. 加载用户智能体配置（用于提示词、工具等）
        config_service = get_agent_config_service()
        agent_config = await config_service.get_user_config(user_id, create_if_missing=True)

        if not agent_config:
            raise Exception("无法加载用户智能体配置")

        # 2. 加载用户模型偏好
        from core.settings.services.user_service import get_user_settings_service
        settings_service = get_user_settings_service()
        user_settings = await settings_service.get_user_settings(user_id)

        # 3. 确定使用的两个 AI 模型（带回退机制）
        model_service = get_model_service()

        # 确定数据收集模型（带回退）
        data_collection_model = await _resolve_model_with_fallback(
            model_service=model_service,
            requested_model_id=request.data_collection_model,
            user_settings=user_settings,
            model_type="data_collection",
            user_id=user_id
        )

        # 确定辩论模型（带回退）
        debate_model = await _resolve_model_with_fallback(
            model_service=model_service,
            requested_model_id=request.debate_model,
            user_settings=user_settings,
            model_type="debate",
            user_id=user_id
        )

        data_collection_model_id = str(data_collection_model.id)
        debate_model_id = str(debate_model.id)

        # 3. 请求并发控制（两个模型都需要获取槽位）
        from modules.trading_agents.core.concurrency_controller import get_concurrency_controller
        concurrency_controller = get_concurrency_controller()

        # 为数据收集模型请求并发
        data_collection_config = {
            "max_concurrency": data_collection_model.max_concurrency,
            "task_concurrency": data_collection_model.task_concurrency,
            "batch_concurrency": data_collection_model.batch_concurrency,
        }

        data_collection_execution = await concurrency_controller.request_execution(
            model_id=data_collection_model_id,
            task_id=task_id,
            user_id=user_id,
            model_config=data_collection_config,
        )

        # 为辩论模型请求并发
        debate_config = {
            "max_concurrency": debate_model.max_concurrency,
            "task_concurrency": debate_model.task_concurrency,
            "batch_concurrency": debate_model.batch_concurrency,
        }

        # 使用并发控制的等待机制（自动排队等待）
        # 两个模型都需要获取到槽位才能继续
        logger.info(f"任务 {task_id} 请求并发控制槽位...")

        try:
            # 等待数据收集模型槽位（超时 5 分钟）
            await concurrency_controller.wait_for_execution(
                model_id=data_collection_model_id,
                task_id=task_id,
                user_id=user_id,
                model_config=data_collection_config,
                timeout=300.0,
            )
            logger.info(f"任务 {task_id} 获取到数据收集模型槽位")

            # 等待辩论模型槽位（超时 5 分钟）
            await concurrency_controller.wait_for_execution(
                model_id=debate_model_id,
                task_id=task_id,
                user_id=user_id,
                model_config=debate_config,
                timeout=300.0,
            )
            logger.info(f"任务 {task_id} 获取到辩论模型槽位")

        except asyncio.TimeoutError as e:
            # 等待超时，标记任务失败
            logger.error(f"任务 {task_id} 等待并发槽位超时: {e}")
            raise Exception(f"任务等待执行超时，请稍后重试") from e

        # 4. 获取两个 LLM Provider 实例
        data_collection_llm = await model_service.get_llm_provider(
            model_id=data_collection_model_id,
            user_id=user_id,
            is_admin=False
        )

        debate_llm = await model_service.get_llm_provider(
            model_id=debate_model_id,
            user_id=user_id,
            is_admin=False
        )

        if not data_collection_llm or not debate_llm:
            raise Exception("无法创建 LLM Provider 实例")

        # 5. 获取可用工具列表
        tool_registry = get_tool_registry()
        available_tools = tool_registry.list_available_tools()
        logger.info(f"可用工具数量: {len(available_tools)}")

        # 6. 准备思考配置（从模型配置中读取）
        data_collection_thinking_config = {
            "thinking_enabled": data_collection_model.thinking_enabled,
            "thinking_mode": data_collection_model.thinking_mode,
        }

        debate_thinking_config = {
            "thinking_enabled": debate_model.thinking_enabled,
            "thinking_mode": debate_model.thinking_mode,
        }

        if data_collection_model.thinking_enabled or debate_model.thinking_enabled:
            logger.info(
                f"任务 {task_id} 使用思考模式: "
                f"数据收集模型(thinking_enabled={data_collection_model.thinking_enabled}, mode={data_collection_model.thinking_mode}), "
                f"辩论模型(thinking_enabled={debate_model.thinking_enabled}, mode={debate_model.thinking_mode})"
            )

        # 7. 创建工作流引擎
        # 注意：引擎会在 execute_workflow 时动态初始化智能体（包括 MCP 连接）
        workflow = AgentWorkflowEngine(
            llm=debate_llm,  # 主引擎使用辩论模型
            config=agent_config,
            ws_manager=ws_manager,
            data_collection_llm=data_collection_llm,  # 第一阶段使用数据收集模型
            data_collection_model_config=data_collection_thinking_config,
            debate_model_config=debate_thinking_config,
        )

        # 8. 执行工作流（智能体会在 execute_workflow 内部动态初始化）
        result = await workflow.execute_workflow(
            task_id=task_id,
            user_id=user_id,
            request=request
        )

        # 9. 从结果中提取推荐和价格信息
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

        # 10. 完成任务
        await task_manager.complete_task(
            task_id=task_id,
            final_recommendation=final_recommendation,
            buy_price=buy_price,
            sell_price=sell_price,
            token_usage=result.get("token_usage"),
        )

        # 11. 创建分析报告
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

    finally:
        # 释放并发资源（两个模型都需要释放）
        try:
            from modules.trading_agents.core.concurrency_controller import get_concurrency_controller
            concurrency_controller = get_concurrency_controller()

            # 释放数据收集模型槽位
            if data_collection_model_id:
                try:
                    await concurrency_controller.release_execution(
                        model_id=data_collection_model_id,
                        task_id=task_id,
                        user_id=user_id,
                        batch_id=batch_id,
                    )
                    logger.info(
                        f"已释放任务 {task_id} 的数据收集模型并发槽位: "
                        f"model_id={data_collection_model_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"释放数据收集模型并发槽位失败: task_id={task_id}, error={e}"
                    )

            # 释放辩论模型槽位
            if debate_model_id:
                try:
                    await concurrency_controller.release_execution(
                        model_id=debate_model_id,
                        task_id=task_id,
                        user_id=user_id,
                        batch_id=batch_id,
                    )
                    logger.info(
                        f"已释放任务 {task_id} 的辩论模型并发槽位: "
                        f"model_id={debate_model_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"释放辩论模型并发槽位失败: task_id={task_id}, error={e}"
                    )
        except Exception as e:
            logger.error(f"释放并发资源时发生错误: task_id={task_id}, error={e}")

        # 释放 MCP 连接（确保 finally 块中执行，防止资源泄漏）
        try:
            from modules.trading_agents.tools.mcp_tool_filter import release_task_connections
            await release_task_connections(task_id)
            logger.info(f"已释放任务 {task_id} 的 MCP 连接")
        except Exception as e:
            logger.error(f"释放 MCP 连接失败: task_id={task_id}, error={e}")
