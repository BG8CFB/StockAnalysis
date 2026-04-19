"""
智能体执行辅助函数

提供通用的智能体开始/完成处理逻辑，包括：
- 更新 state.current_agent
- 保存到数据库
- 发送 WebSocket 事件
- 保存报告到数据库

**版本**: v1.0
**最后更新**: 2026-02-16
"""

import logging
from typing import Any, Optional

from modules.trading_agents.models.state import WorkflowState
from modules.trading_agents.workflow.events import (
    create_agent_completed_event,
    create_agent_started_event,
    create_report_generated_event,
)

logger = logging.getLogger(__name__)


async def handle_agent_started(
    state: WorkflowState,
    agent_slug: str,
    agent_name: str,
    websocket_manager: Any,
) -> None:
    """
    处理智能体开始执行

    Args:
        state: 工作流状态
        agent_slug: 智能体 slug
        agent_name: 智能体名称
        websocket_manager: WebSocket 管理器
    """
    # 更新当前执行的智能体
    state.current_agent = agent_slug

    # 保存当前智能体到数据库（用于页面刷新后恢复状态）
    try:
        from modules.trading_agents.manager.task_manager import get_task_manager

        task_manager = get_task_manager()
        await task_manager.update_task_progress(
            task_id=state.task_id,
            progress=state.progress,
            current_phase=(
                int(state.current_phase)
                if isinstance(state.current_phase, (int, str))
                and str(state.current_phase).isdigit()
                else None
            ),
            current_agent=agent_slug,
        )
    except Exception as e:
        logger.error(f"更新当前智能体失败: {agent_slug}, error={e}")

    # 发送智能体开始事件
    agent_started_event = create_agent_started_event(
        task_id=state.task_id, agent_slug=agent_slug, agent_name=agent_name
    )
    await websocket_manager.broadcast_event(state.task_id, agent_started_event)
    logger.info(f"智能体开始: {agent_slug} ({agent_name})")


async def handle_agent_completed(
    state: WorkflowState,
    agent_slug: str,
    agent_name: str,
    output: Optional[str],
    websocket_manager: Any,
    save_report: bool = True,
) -> None:
    """
    处理智能体完成执行

    Args:
        state: 工作流状态
        agent_slug: 智能体 slug
        agent_name: 智能体名称
        output: 智能体输出（报告）
        websocket_manager: WebSocket 管理器
        save_report: 是否保存报告到数据库（默认 True）
    """
    if not output:
        logger.warning(f"智能体输出为空: {agent_slug}")
        return

    # 保存报告到数据库（立即持久化，避免页面刷新后丢失）
    if save_report:
        try:
            from modules.trading_agents.manager.task_manager import get_task_manager

            task_manager = get_task_manager()
            await task_manager.add_task_report(
                task_id=state.task_id, agent_slug=agent_slug, report=output
            )
            logger.info(f"报告已保存到数据库: {agent_slug}")
        except Exception as e:
            logger.error(f"保存报告失败: {agent_slug}, error={e}")

    # 发送报告生成事件
    report_event = create_report_generated_event(
        task_id=state.task_id, agent_slug=agent_slug, agent_name=agent_name, content=output
    )
    await websocket_manager.broadcast_event(state.task_id, report_event)

    # 更新进度：智能体完成
    state.completed_agent_executions += 1
    state.progress = state.calculate_progress()

    # 发送智能体完成事件
    agent_completed_event = create_agent_completed_event(
        task_id=state.task_id,
        agent_slug=agent_slug,
        agent_name=agent_name,
        token_usage={},  # 暂无 token 用量
        progress=state.progress,
        completed_agents=state.completed_agent_executions,
        total_agents=state.total_agent_executions,
    )
    await websocket_manager.broadcast_event(state.task_id, agent_completed_event)
    logger.info(f"智能体完成: {agent_slug}, 进度: {state.progress:.1f}%")
