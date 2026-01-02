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
    batch_id = None
    data_collection_model_id = None
    debate_model_id = None

    try:
        # 1. 加载用户智能体配置（用于提示词、工具等）
        config_service = get_agent_config_service()
        agent_config = await config_service.get_user_config(user_id, create_if_missing=True)

        if not agent_config:
            raise Exception("无法加载用户智能体配置")

        # 2. 加载用户模型偏好
        from core.user.settings_service import get_user_settings_service
        settings_service = get_user_settings_service()
        user_settings = await settings_service.get_user_settings(user_id)

        # 3. 确定使用的两个 AI 模型
        model_service = get_model_service()

        # 确定数据收集模型（第一阶段）
        if request.data_collection_model:
            # 优先级1：任务参数指定
            data_collection_model = await model_service.get_model(
                request.data_collection_model, user_id, is_admin=False
            )
            if not data_collection_model:
                raise Exception(f"未找到指定的数据收集模型: {request.data_collection_model}")
        elif user_settings and user_settings.trading_agents_settings:
            # 优先级2：用户模型偏好
            model_id = user_settings.trading_agents_settings.data_collection_model_id
            if model_id:
                data_collection_model = await model_service.get_model(model_id, user_id, is_admin=False)
            else:
                # 优先级3：系统默认
                data_collection_model = await model_service.get_default_model(user_id=user_id)
        else:
            # 优先级3：系统默认
            data_collection_model = await model_service.get_default_model(user_id=user_id)

        # 确定辩论模型（第二三四阶段）
        if request.debate_model:
            # 优先级1：任务参数指定
            debate_model = await model_service.get_model(
                request.debate_model, user_id, is_admin=False
            )
            if not debate_model:
                raise Exception(f"未找到指定的辩论模型: {request.debate_model}")
        elif user_settings and user_settings.trading_agents_settings:
            # 优先级2：用户模型偏好
            model_id = user_settings.trading_agents_settings.debate_model_id
            if model_id:
                debate_model = await model_service.get_model(model_id, user_id, is_admin=False)
            else:
                # 优先级3：系统默认
                debate_model = await model_service.get_default_model(user_id=user_id)
        else:
            # 优先级3：系统默认
            debate_model = await model_service.get_default_model(user_id=user_id)

        if not data_collection_model or not debate_model:
            raise Exception("未找到可用的 AI 模型配置")

        data_collection_model_id = str(data_collection_model.id)
        debate_model_id = str(debate_model.id)

        logger.info(
            f"任务 {task_id} 模型配置: "
            f"数据收集={data_collection_model.name}({data_collection_model_id}), "
            f"辩论={debate_model.name}({debate_model_id})"
        )

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

        debate_execution = await concurrency_controller.request_execution(
            model_id=debate_model_id,
            task_id=task_id,
            user_id=user_id,
            model_config=debate_config,
        )

        # 检查是否都能立即执行
        if not data_collection_execution["can_execute"] or not debate_execution["can_execute"]:
            logger.info(
                f"任务 {task_id} 需要排队: "
                f"数据收集模型队列={data_collection_execution['queue_position']}, "
                f"辩论模型队列={debate_execution['queue_position']}"
            )
            # TODO: 实现排队等待逻辑
            # 目前先等待一会儿再重试
            await asyncio.sleep(5)

            # 重新请求
            data_collection_execution = await concurrency_controller.request_execution(
                model_id=data_collection_model_id,
                task_id=task_id,
                user_id=user_id,
                model_config=data_collection_config,
            )
            debate_execution = await concurrency_controller.request_execution(
                model_id=debate_model_id,
                task_id=task_id,
                user_id=user_id,
                model_config=debate_config,
            )

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
