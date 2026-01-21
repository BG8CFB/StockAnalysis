# -*- coding: utf-8 -*-
"""
后台任务管理

负责创建和执行分析任务的后台任务逻辑。

此模块提供简化的接口，实际执行逻辑在 task_manager 中。
"""
import logging
from typing import Dict, Any

from modules.trading_agents.schemas import AnalysisTaskCreate

logger = logging.getLogger(__name__)


async def create_analysis_task_background(
    user_id: str,
    request: AnalysisTaskCreate,
    config: Dict[str, Any]
) -> str:
    """
    后台任务：创建并执行分析任务

    此函数会在后台异步执行，避免阻塞 HTTP 响应。
    实际执行逻辑委托给 task_manager。
    """
    logger.info(f"[BackgroundTasks] ============ create_analysis_task_background CALLED ============")
    logger.info(f"[BackgroundTasks] user_id={user_id}, stock_code={request.stock_code}")

    # 延迟导入避免循环依赖
    from modules.trading_agents.manager.task_manager import get_task_manager

    task_manager = get_task_manager()
    logger.info(f"[BackgroundTasks] task_manager obtained: {task_manager}")

    # 委托给 task_manager 执行
    logger.info(f"[BackgroundTasks] calling task_manager.create_task_background...")
    task_id = await task_manager.create_task_background(
        user_id=user_id,
        request=request,
        config=config
    )
    logger.info(f"[BackgroundTasks] task_id returned: {task_id}")

    return task_id
