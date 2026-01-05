"""
LangGraph 工作流执行器

使用 LangGraph 执行分析任务

集成点：
- 在 execute_analysis_workflow_langgraph 中使用 LangGraph
- 与现有的 execute_analysis_workflow 函数并存
"""

import logging
from typing import Dict, Any

from modules.trading_agents.schemas import AnalysisTaskCreate
from modules.trading_agents.workflow.adapter import get_langgraph_adapter

logger = logging.getLogger(__name__)


# =============================================================================
# LangGraph 工作流执行
# =============================================================================

async def execute_analysis_workflow_langgraph(
    task_id: str,
    user_id: str,
    request: AnalysisTaskCreate,
    config: Dict[str, Any],
) -> None:
    """
    使用 LangGraph 执行分析工作流

    这是新的入口函数，使用 LangGraph 替代旧的工作流引擎

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        request: 分析任务请求
        config: 智能体配置

    Raises:
        Exception: 任务执行失败
    """
    logger.info(f"[LangGraph] 开始执行任务: task_id={task_id}, user_id={user_id}, stock={request.stock_code}")

    try:
        # 获取 LangGraph 适配器
        adapter = get_langgraph_adapter()

        # 执行任务
        result = await adapter.execute_task(
            task_id=task_id,
            user_id=user_id,
            request=request,
            config=config
        )

        logger.info(f"[LangGraph] 任务执行完成: task_id={task_id}, status={result.get('status')}")

        # 更新数据库状态
        await _update_task_completion(task_id, result)

    except Exception as e:
        logger.error(f"[LangGraph] 任务执行失败: task_id={task_id}, 错误: {e}")
        await _update_task_failure(task_id, str(e))
        raise


# =============================================================================
# 数据库更新辅助函数
# =============================================================================

async def _update_task_completion(task_id: str, result: Dict[str, Any]) -> None:
    """
    更新任务完成状态到数据库

    Args:
        task_id: 任务 ID
        result: 任务结果
    """
    from bson import ObjectId
    from core.db.mongodb import mongodb
    from datetime import datetime

    update_data = {
        "status": result.get("status", "completed"),
        "final_recommendation": result.get("final_recommendation"),
        "reports": {
            "final_report": result.get("final_report"),
        },
        "token_usage": result.get("token_usage", {}),
        "completed_at": datetime.utcnow(),
    }

    await mongodb.database.analysis_tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )

    logger.info(f"[LangGraph] 已更新任务完成状态: task_id={task_id}")


async def _update_task_failure(task_id: str, error_message: str) -> None:
    """
    更新任务失败状态到数据库

    Args:
        task_id: 任务 ID
        error_message: 错误信息
    """
    from bson import ObjectId
    from core.db.mongodb import mongodb
    from datetime import datetime

    update_data = {
        "status": "failed",
        "error_message": error_message,
        "completed_at": datetime.utcnow(),
    }

    await mongodb.database.analysis_tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )

    logger.info(f"[LangGraph] 已更新任务失败状态: task_id={task_id}")
