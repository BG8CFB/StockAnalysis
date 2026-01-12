"""
任务恢复增强功能

支持从检查点继续执行任务，智能体删除时标记任务为失败。
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.schemas import TaskStatusEnum

logger = logging.getLogger(__name__)


async def restore_running_tasks_with_checkpoint(
    mongodb_db
) -> tuple[int, int]:
    """
    恢复运行中的任务（增强版）

    系统重启后，检查每个运行中的任务：
    1. 验证配置中的智能体是否存在
    2. 如果智能体被删除，标记任务为失败
    3. 否则，重置为 PENDING 状态，保留已完成报告

    Args:
        mongodb_db: MongoDB 数据库实例

    Returns:
        (恢复的任务数量, 失败的任务数量)
    """
    # 查找所有运行中的任务
    running_tasks = await mongodb_db.get_collection("analysis_tasks").find({
        "status": TaskStatusEnum.RUNNING.value
    }).to_list(None)

    if not running_tasks:
        logger.info("没有需要恢复的运行中任务")
        return 0, 0

    logger.info(f"发现 {len(running_tasks)} 个需要恢复的运行中任务")

    restored_count = 0
    failed_count = 0

    for task_doc in running_tasks:
        task_id = str(task_doc["_id"])
        user_id = task_doc["user_id"]
        stock_code = task_doc.get("stock_code", "未知")
        config_snapshot = task_doc.get("config_snapshot")
        current_phase = task_doc.get("current_phase", 1)
        current_agent = task_doc.get("current_agent")

        try:
            # 检查是否有配置快照
            if not config_snapshot:
                logger.warning(f"任务缺少配置快照: task_id={task_id}")
                await _mark_task_failed(mongodb_db, task_id, "任务恢复失败：缺少配置快照")
                failed_count += 1
                continue

            # 验证配置中的智能体是否存在
            agent_exists = await _validate_agent_exists(
                config_snapshot,
                current_phase,
                current_agent
            )

            if not agent_exists:
                logger.warning(
                    f"任务配置的智能体已被删除: task_id={task_id}, "
                    f"phase={current_phase}, agent={current_agent}"
                )
                await _mark_task_failed(
                    mongodb_db,
                    task_id,
                    "任务恢复失败：配置的智能体已被删除"
                )
                failed_count += 1
                continue

            # 将任务状态重置为 PENDING，保留已完成报告
            await mongodb_db.get_collection("analysis_tasks").update_one(
                {"_id": task_doc["_id"]},
                {
                    "$set": {
                        "status": TaskStatusEnum.PENDING.value,
                        "interrupt_signal": False,
                        "progress": 0.0,  # 重置进度
                        "current_phase": 0,  # 重新开始
                        "current_agent": None,
                    }
                }
            )

            # 清除开始时间
            await mongodb_db.get_collection("analysis_tasks").update_one(
                {"_id": task_doc["_id"]},
                {"$unset": ["started_at"]}
            )

            restored_count += 1

            logger.info(
                f"任务已恢复为待执行状态: task_id={task_id}, "
                f"user_id={user_id}, stock={stock_code}, "
                f"已保留 {len(task_doc.get('reports', {}))} 个报告"
            )

        except Exception as e:
            logger.error(
                f"恢复任务失败: task_id={task_id}, error={e}",
                exc_info=True
            )
            failed_count += 1

    logger.info(f"任务恢复完成，共恢复 {restored_count} 个，失败 {failed_count} 个")
    return restored_count, failed_count


async def _validate_agent_exists(
    config_snapshot: dict,
    phase: int,
    agent_slug: Optional[str]
) -> bool:
    """
    验证智能体是否存在

    Args:
        config_snapshot: 配置快照
        phase: 当前阶段
        agent_slug: 当前智能体标识

    Returns:
        智能体是否存在
    """
    if not agent_slug:
        return True  # 没有指定智能体，跳过检查

    phase_key = f"phase{phase}"
    phase_config = config_snapshot.get(phase_key)

    if not phase_config:
        return True  # 阶段不存在，可能被禁用

    agents = phase_config.get("agents", [])
    for agent in agents:
        if agent.get("slug") == agent_slug:
            return True

    return False


async def _mark_task_failed(
    mongodb_db,
    task_id: str,
    reason: str
) -> None:
    """
    标记任务为失败

    Args:
        mongodb_db: MongoDB 数据库实例
        task_id: 任务 ID
        reason: 失败原因
    """
    await mongodb_db.get_collection("analysis_tasks").update_one(
        {"_id": ObjectId(task_id)},
        {
            "$set": {
                "status": TaskStatusEnum.FAILED.value,
                "error_message": reason,
                "completed_at": datetime.utcnow(),
            }
        }
    )

