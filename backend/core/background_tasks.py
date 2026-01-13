# -*- coding: utf-8 -*-
"""
后台任务管理

负责创建和执行分析任务的后台任务逻辑。
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from modules.trading_agents.manager.task_manager import get_task_manager
from modules.trading_agents.schemas import AnalysisTaskCreate
from modules.trading_agents.services.agent_config_service import get_agent_config_service
from core.ai.model import get_model_service
from modules.trading_agents.pusher import get_ws_manager

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
    # 🔍 立即添加入口日志，确认函数被调用
    logger.info("="*60)
    logger.info(f"🔍 [DEBUG] create_analysis_task_background 被调用")
    logger.info(f"  user_id: {user_id}")
    logger.info(f"  stock_code: {request.stock_code}")
    logger.info(f"  trade_date: {request.trade_date}")
    logger.info("="*60)

    try:
        print(f"[PRINT] [DEBUG] 步骤1: 获取 task_manager...", flush=True)
        logger.info(f"[DEBUG] 步骤1: 获取 task_manager...")
        task_manager = get_task_manager()
        print(f"[PRINT] [DEBUG] ✅ task_manager 获取成功", flush=True)
        logger.info(f"[DEBUG] ✅ task_manager 获取成功")

        print(f"[PRINT] [DEBUG] 步骤2: 获取 ws_manager...", flush=True)
        logger.info(f"[DEBUG] 步骤2: 获取 ws_manager...")
        ws_manager = await get_ws_manager()
        print(f"[PRINT] [DEBUG] ✅ ws_manager 获取成功", flush=True)
        logger.info(f"[DEBUG] ✅ ws_manager 获取成功")

        # 1. 创建任务记录
        print(f"[PRINT] [DEBUG] 步骤3: 准备创建任务记录...", flush=True)
        logger.info(f"[DEBUG] 步骤3: 准备创建任务记录...")
        task_id = await task_manager.create_task(
            user_id=user_id,
            request=request,
            config=config
        )
        print(f"[PRINT] [DEBUG] ✅ 任务记录创建成功: task_id={task_id}", flush=True)
        logger.info(f"[DEBUG] ✅ 任务记录创建成功: task_id={task_id}")

        # 2. 标记任务为运行中
        print(f"[PRINT] [DEBUG] 步骤4: 准备标记任务为运行中: task_id={task_id}", flush=True)
        logger.info(f"[DEBUG] 步骤4: 准备标记任务为运行中: task_id={task_id}")
        await task_manager.mark_task_running(task_id)
        print(f"[PRINT] [DEBUG] ✅ 任务已标记为运行中: task_id={task_id}", flush=True)
        logger.info(f"[DEBUG] ✅ 任务已标记为运行中: task_id={task_id}")

        # 3. 在后台异步执行工作流（不阻塞响应）
        # 注意：必须保存 Task 对象的引用，否则会被垃圾回收
        print(f"[PRINT] [DEBUG] 步骤5: 准备创建后台工作流任务: task_id={task_id}", flush=True)
        logger.info(f"[DEBUG] 步骤5: 准备创建后台工作流任务: task_id={task_id}")

        # 使用 asyncio.create_task 创建后台任务
        task = asyncio.create_task(
            execute_analysis_workflow(
                task_id=task_id,
                user_id=user_id,
                request=request
            ),
            name=f"workflow-{task_id}"  # 给任务命名，方便调试
        )
        print(f"[PRINT] [DEBUG] ✅ 后台工作流任务创建成功: task_id={task_id}, task_obj={id(task)}, done={task.done()}", flush=True)
        logger.info(f"[DEBUG] ✅ 后台工作流任务创建成功: task_id={task_id}, task_obj={id(task)}, done={task.done()}")

        # 添加回调来追踪任务状态
        def task_callback(t):
            print(f"[PRINT] [DEBUG] 📞 任务完成回调: task_id={task_id}, done={t.done()}, cancelled={t.cancelled()}", flush=True)
            logger.info(f"[DEBUG] 📞 任务完成回调: task_id={task_id}, done={t.done()}, cancelled={t.cancelled()}")

        task.add_done_callback(task_callback)
        print(f"[PRINT] [DEBUG] ✅ 任务回调已注册", flush=True)
        logger.info(f"[DEBUG] ✅ 任务回调已注册")

        print(f"[PRINT] [DEBUG] 🎯 准备返回 task_id: {task_id}", flush=True)
        logger.info(f"[DEBUG] 🎯 准备返回 task_id: {task_id}")
        return task_id

    except Exception as e:
        print(f"[PRINT] [DEBUG] ❌ create_analysis_task_background 发生异常: {e}", flush=True)
        import traceback
        print(f"[PRINT] traceback:", flush=True)
        traceback.print_exc()
        logger.error(f"[DEBUG] ❌ create_analysis_task_background 发生异常: {e}", exc_info=True)
        raise


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
    logger.info(f"="*60)
    logger.info(f"execute_analysis_workflow 开始: task_id={task_id}, user_id={user_id}")
    logger.info(f"="*60)

    task_manager = get_task_manager()

    # 用于并发控制
    batch_id = task_id
    data_collection_model_id = None
    debate_model_id = None

    try:
        # 1. 加载用户智能体配置
        logger.info(f"[{task_id}] 步骤1: 加载用户智能体配置...")
        config_service = get_agent_config_service()
        agent_config = await config_service.get_user_config(user_id, create_if_missing=True)

        if not agent_config:
            raise Exception("无法加载用户智能体配置")

        # **关键修复**: 将 Pydantic 对象转换为字典，确保后续处理兼容
        if hasattr(agent_config, 'model_dump'):
            agent_config = agent_config.model_dump(mode='json')
        elif hasattr(agent_config, 'dict'):
            agent_config = agent_config.dict()

        logger.info(f"[{task_id}] ✅ 用户智能体配置加载成功")

        # 2. 加载用户模型偏好
        logger.info(f"[{task_id}] 步骤2: 加载用户模型偏好...")
        from core.settings.services.user_service import get_user_settings_service
        settings_service = get_user_settings_service()
        user_settings = await settings_service.get_user_settings(user_id)
        logger.info(f"[{task_id}] ✅ 用户模型偏好加载成功")

        # 3. 确定使用的两个 AI 模型（带回退机制）
        logger.info(f"[{task_id}] 步骤3: 解析AI模型...")
        model_service = get_model_service()

        # 确定数据收集模型（带回退）
        logger.info(f"[{task_id}] 3.1 解析数据收集模型...")
        data_collection_model = await _resolve_model_with_fallback(
            model_service=model_service,
            requested_model_id=request.data_collection_model,
            user_settings=user_settings,
            model_type="data_collection",
            user_id=user_id
        )
        logger.info(f"[{task_id}] ✅ 数据收集模型解析成功")

        # 确定辩论模型（带回退）
        logger.info(f"[{task_id}] 3.2 解析辩论模型...")
        debate_model = await _resolve_model_with_fallback(
            model_service=model_service,
            requested_model_id=request.debate_model,
            user_settings=user_settings,
            model_type="debate",
            user_id=user_id
        )
        logger.info(f"[{task_id}] ✅ 辩论模型解析成功")

        data_collection_model_id = str(data_collection_model.id)
        debate_model_id = str(debate_model.id)

        logger.info(f"任务 {task_id} 模型解析完成: data_collection={data_collection_model_id}, debate={debate_model_id}")

        # 请求并发控制
        from modules.trading_agents.manager.concurrency_controller import get_concurrency_controller
        concurrency_controller = get_concurrency_controller()

        # 为数据收集模型请求并发
        data_collection_config = {
            "max_concurrency": data_collection_model.max_concurrency,
            "task_concurrency": data_collection_model.task_concurrency,
            "batch_concurrency": data_collection_model.batch_concurrency,
        }

        # 为辩论模型请求并发
        debate_config = {
            "max_concurrency": debate_model.max_concurrency,
            "task_concurrency": debate_model.task_concurrency,
            "batch_concurrency": debate_model.batch_concurrency,
        }

        logger.info(f"任务 {task_id} 请求并发控制槽位...")

        try:
            # 等待数据收集模型槽位（超时 5 分钟）
            logger.info(f"任务 {task_id} 等待数据收集模型槽位...")
            await concurrency_controller.wait_for_execution(
                model_id=data_collection_model_id,
                task_id=task_id,
                user_id=user_id,
                model_config=data_collection_config,
                timeout=300.0,
            )
            logger.info(f"任务 {task_id} 获取到数据收集模型槽位")

            # 等待辩论模型槽位（超时 5 分钟）
            logger.info(f"任务 {task_id} 等待辩论模型槽位...")
            await concurrency_controller.wait_for_execution(
                model_id=debate_model_id,
                task_id=task_id,
                user_id=user_id,
                model_config=debate_config,
                timeout=300.0,
            )
            logger.info(f"任务 {task_id} 获取到辩论模型槽位")

        except asyncio.TimeoutError as e:
            logger.error(f"任务 {task_id} 等待并发槽位超时: {e}")
            raise Exception(f"任务等待执行超时，请稍后重试") from e
        except Exception as e:
            logger.error(f"任务 {task_id} 等待并发槽位时发生异常: {e}", exc_info=True)
            raise Exception(f"任务等待并发槽位失败: {e}") from e

        # 5. 使用新调度器执行工作流
        logger.info(f"任务 {task_id} 开始执行工作流...")

        # 准备配置参数
        model_config = {
            "data_collection_model": data_collection_model_id,
            "debate_model": debate_model_id,
        }

        try:
            # 使用新的 WorkflowScheduler 执行工作流
            from modules.trading_agents.scheduler.workflow_scheduler import create_workflow_scheduler
            from modules.trading_agents.phases import run_phase1, run_phase2, run_phase3, run_phase4
            from modules.trading_agents.pusher import get_ws_manager

            # 获取 WebSocket 管理器用于进度推送
            ws_manager = await get_ws_manager()

            # 创建调度器
            scheduler = create_workflow_scheduler() \
                .with_phase1_runner(run_phase1) \
                .with_phase2_runner(run_phase2) \
                .with_phase3_runner(run_phase3) \
                .with_phase4_runner(run_phase4) \
                .with_progress_callback(lambda data: asyncio.create_task(
                    ws_manager.broadcast_progress(task_id, data)
                )) \
                .build()

            # 获取阶段开关
            stages_config = request.stages
            enable_phase1 = stages_config.stage1.enabled if stages_config else True
            enable_phase2 = stages_config.stage2.enabled if stages_config else True
            enable_phase3 = stages_config.stage3.enabled if stages_config else True
            enable_phase4 = stages_config.stage4.enabled if stages_config else True

            # 执行工作流
            final_state = await scheduler.run(
                task_id=task_id,
                user_id=user_id,
                stock_code=request.stock_code,
                trade_date=request.trade_date,
                model_config=model_config,
                agent_config=agent_config,
                max_debate_rounds=stages_config.stage2.debate.rounds if stages_config else 2,
                enable_phase1=enable_phase1,
                enable_phase2=enable_phase2,
                enable_phase3=enable_phase3,
                enable_phase4=enable_phase4,
            )

            logger.info(f"任务 {task_id} 工作流执行完成，状态: {final_state.status}")

        except Exception as e:
            logger.error(f"任务 {task_id} 工作流执行失败: {e}", exc_info=True)
            raise

        logger.info(f"分析任务执行成功: task_id={task_id}")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"分析任务执行失败: task_id={task_id}, error={e}\n{error_trace}")

        # 标记任务失败
        await task_manager.fail_task(
            task_id=task_id,
            error_message=str(e),
            error_details={"type": type(e).__name__, "traceback": error_trace}
        )

    finally:
        # 释放并发资源（两个模型都需要释放）
        try:
            from modules.trading_agents.manager.concurrency_controller import get_concurrency_controller
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

        # 减少用户的并发任务计数
        try:
            from core.settings.services.user_service import get_user_settings_service
            settings_service = get_user_settings_service()
            await settings_service.decrement_concurrent_tasks(user_id)
            logger.info(f"已减少用户 {user_id} 的并发任务计数")
        except Exception as e:
            logger.error(f"减少并发任务计数失败: task_id={task_id}, user_id={user_id}, error={e}")

        # 释放 MCP 连接
        try:
            from modules.mcp.pool.pool import get_mcp_connection_pool
            pool = get_mcp_connection_pool()
            await pool.release_task_connections(task_id)
            logger.info(f"已释放任务 {task_id} 的 MCP 连接")
        except Exception as e:
            logger.error(f"释放 MCP 连接失败: task_id={task_id}, error={e}")
