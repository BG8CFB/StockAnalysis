"""
TradingAgents 模块 API 路由

定义所有 TradingAgents 相关的 API 端点。
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from core.auth.dependencies import get_current_user, get_current_active_user
from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel
from core.db.mongodb import mongodb
from modules.trading_agents.core.task_manager import get_task_manager, TaskManager
from modules.trading_agents.core.concurrency_controller import get_concurrency_controller
from modules.trading_agents.websocket import get_ws_manager, WebSocketManager
from modules.trading_agents.schemas import (
    AnalysisTaskCreate,
    BatchTaskCreate,
    AnalysisTaskResponse,
    BatchTaskResponse,
    TaskStatusEnum,
    MessageResponse,

    UserAgentConfigCreate,
    UserAgentConfigUpdate,
    UserAgentConfigResponse,
    TradingAgentsSettings,
    TradingAgentsSettingsResponse,
    ReportSummaryResponse,
    # 统一任务模型（重构）
    UnifiedTaskCreate,
    UnifiedTaskResponse,
)
from core.ai.model.schemas import ConnectionTestResponse
from core.background_tasks import create_analysis_task_background
# AI 模型服务已迁移到核心模块，API路由也已迁移
# from core.ai.model import get_model_service
from modules.trading_agents.services.agent_config_service import get_agent_config_service
from modules.trading_agents.services.report_service import get_report_service, ReportService
from core.auth.rbac import Role, Permission

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/trading-agents", tags=["TradingAgents"])


# =============================================================================
# 辅助函数
# =============================================================================

def filter_sensitive_prompts(config: UserAgentConfigResponse) -> UserAgentConfigResponse:
    """
    过滤智能体配置中的敏感提示词

    用于普通用户获取精简配置，不暴露系统提示词。

    Args:
        config: 完整的智能体配置

    Returns:
        精简后的智能体配置（不含 role_definition）
    """
    from modules.trading_agents.schemas import (
        Phase1ConfigSlim, Phase2ConfigSlim, Phase3ConfigSlim,
        Phase4ConfigSlim, AgentConfigSlim
    )

    def filter_agent(agent):
        """过滤单个智能体的提示词"""
        return AgentConfigSlim(
            slug=agent.slug,
            name=agent.name,
            when_to_use=agent.when_to_use,
            enabled_mcp_servers=agent.enabled_mcp_servers,
            enabled_local_tools=agent.enabled_local_tools,
            enabled=agent.enabled,
        )

    def filter_phase(phase, slim_class):
        """过滤阶段配置的提示词"""
        return slim_class(
            enabled=phase.enabled,
            max_rounds=phase.max_rounds,
            agents=[filter_agent(a) for a in phase.agents],
            max_concurrency=getattr(phase, 'max_concurrency', None)
        )

    # 创建新的配置对象（去掉 role_definition）
    filtered_config = config.model_copy(
        update={
            "phase1": filter_phase(config.phase1, Phase1ConfigSlim),
            "phase2": filter_phase(config.phase2, Phase2ConfigSlim) if config.phase2 else None,
            "phase3": filter_phase(config.phase3, Phase3ConfigSlim) if config.phase3 else None,
            "phase4": filter_phase(config.phase4, Phase4ConfigSlim) if config.phase4 else None,
        }
    )

    return filtered_config


# =============================================================================
# WebSocket 端点
# =============================================================================

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(...),
):
    """
    WebSocket 连接端点

    用于实时接收任务进度和事件。

    Args:
        websocket: WebSocket 连接
        task_id: 任务 ID
        token: 访问令牌（通过查询参数传递）
    """
    # 验证 token 获取用户 ID
    try:
        from core.auth.security import jwt_manager
        payload = jwt_manager.verify_token(token, "access")
        if not payload:
            raise ValueError("Invalid token")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing user_id in token")
    except Exception as e:
        logger.warning(f"WebSocket 令牌验证失败: {e}")
        await websocket.close(code=4001, reason="无效的访问令牌")
        return

    ws_manager = get_ws_manager()

    try:
        await ws_manager.connect(websocket, task_id, user_id)

        # 保持连接，接收客户端消息（如心跳）
        while True:
            data = await websocket.receive_json()
            # 处理客户端消息（如心跳保活）
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: task_id={task_id}, user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: task_id={task_id}, error={e}")
    finally:
        await ws_manager.disconnect(websocket)


# =============================================================================
# 任务管理端点
# =============================================================================

@router.post("/tasks", response_model=UnifiedTaskResponse)
async def create_tasks(
    request: UnifiedTaskCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    统一任务创建接口（支持单股和批量分析）

    根据传入的股票代码数量自动判断：
    - 1 个股票代码：创建单个任务，返回 task_id
    - 多个股票代码：创建批量任务，返回 batch_id

    Args:
        request: 统一任务请求（包含 1-50 个股票代码）
        current_user: 当前用户

    Returns:
        统一任务响应（包含 task_id 或 batch_id）
    """
    from core.settings.services.user_service import get_user_settings_service
    from modules.trading_agents.core.task_manager import get_task_manager

    settings_service = get_user_settings_service()
    task_manager = get_task_manager()
    stock_codes = request.stock_codes
    stock_count = len(stock_codes)

    # 🔒 配额检查（所有任务）
    for _ in range(stock_count):
        allowed, error_msg = await settings_service.check_task_quota(str(current_user.id))
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"配额不足: {error_msg}"
            )

    # 获取用户配置
    config = {}

    # 根据股票数量判断是单股还是批量
    is_single = stock_count == 1

    try:
        if is_single:
            # 单股分析：创建单个任务
            task_create_task = asyncio.create_task(
                create_analysis_task_background(
                    user_id=str(current_user.id),
                    request=AnalysisTaskCreate(
                        stock_code=stock_codes[0],
                        market=request.market,
                        trade_date=request.trade_date,
                        stages=request.stages,
                        # 传递用户选择的模型参数（空值时后台会使用默认模型）
                        data_collection_model=request.data_collection_model,
                        debate_model=request.debate_model,
                    ),
                    config=config
                )
            )
            task_id = await asyncio.wait_for(task_create_task, timeout=5.0)
            await settings_service.increment_task_usage(str(current_user.id))

            return UnifiedTaskResponse.for_single_task(task_id, stock_codes[0])

        else:
            # 批量分析：创建批量任务
            batch_id = await task_manager.create_batch_task(
                user_id=str(current_user.id),
                request=BatchTaskCreate(
                    stock_codes=stock_codes,
                    market=request.market,
                    trade_date=request.trade_date,
                    stages=request.stages,
                    # 传递用户选择的模型参数（空值时后台会使用默认模型）
                    data_collection_model=request.data_collection_model,
                    debate_model=request.debate_model,
                ),
                config=config,
            )

            # 增加所有任务的使用计数
            for _ in range(stock_count):
                await settings_service.increment_task_usage(str(current_user.id))

            return UnifiedTaskResponse.for_batch_task(batch_id, stock_codes)

    except Exception as e:
        # 任务创建失败，回滚配额计数
        for _ in range(stock_count):
            await settings_service.decrement_task_usage(str(current_user.id))
        raise HTTPException(status_code=500, detail=f"任务创建失败: {str(e)}")


@router.get("/tasks/status-counts")
async def get_task_status_counts(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取用户任务状态统计

    为状态标签栏提供数量徽章。

    Args:
        current_user: 当前用户

    Returns:
        各状态任务数量
    """
    task_manager = get_task_manager()
    user_id = str(current_user.id)

    # 并行查询各状态数量
    from asyncio import gather

    async def count_status(status_value):
        return await task_manager.count_tasks(
            user_id=user_id,
            status=status_value,
        ) if status_value else 0

    # 并行获取各状态数量
    counts = await gather(
        count_status(TaskStatusEnum.PENDING),
        count_status(TaskStatusEnum.RUNNING),
        count_status(TaskStatusEnum.COMPLETED),
        count_status(TaskStatusEnum.FAILED),
        count_status(TaskStatusEnum.CANCELLED),
        count_status(TaskStatusEnum.STOPPED),
    )

    pending_count, running_count, completed_count, failed_count, cancelled_count, stopped_count = counts

    # 返回分组统计
    return {
        "all": sum(counts),
        "running": pending_count + running_count,  # 进行中 = 待执行 + 分析中
        "completed": completed_count,
        "failed": failed_count,
        "cancelled": cancelled_count + stopped_count,  # 已取消 = 已取消 + 已停止
        "_detail": {  # 详细统计（可选，用于调试）
            "pending": pending_count,
            "running": running_count,
            "completed": completed_count,
            "failed": failed_count,
            "cancelled": cancelled_count,
            "stopped": stopped_count,
        }
    }


@router.get("/tasks")
async def list_tasks(
    status: Optional[TaskStatusEnum] = None,
    stock_code: Optional[str] = None,
    stock_name: Optional[str] = None,
    recommendation: Optional[str] = None,
    risk_level: Optional[str] = None,
    start_date: Optional[str] = Query(None, description="开始日期 (ISO 8601格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO 8601格式)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    列出用户的分析任务（增强版）

    支持多条件筛选：状态、股票代码、股票名称、推荐结果、风险等级、时间范围。

    Args:
        status: 状态过滤
        stock_code: 股票代码过滤（模糊匹配）
        stock_name: 股票名称过滤（模糊匹配）
        recommendation: 推荐结果过滤
        risk_level: 风险等级过滤
        start_date: 开始日期过滤
        end_date: 结束日期过滤
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        任务列表
    """
    task_manager = get_task_manager()

    tasks = await task_manager.list_tasks(
        user_id=str(current_user.id),
        status=status,
        stock_code=stock_code,
        recommendation=recommendation,
        risk_level=risk_level,
        limit=limit,
        offset=offset,
    )

    return {
        "tasks": tasks,
        "total": await task_manager.count_tasks(
            user_id=str(current_user.id),
            status=status,
            stock_code=stock_code,
            recommendation=recommendation,
            risk_level=risk_level,
        ),
    }


@router.get("/tasks/{task_id}", response_model=AnalysisTaskResponse)
async def get_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取任务详情

    Args:
        task_id: 任务 ID
        current_user: 当前用户

    Returns:
        任务详情
    """
    task_manager = get_task_manager()

    try:
        task_info = await task_manager.get_task_status(task_id)

        # 验证任务所有权
        if task_info["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权访问此任务")

        return AnalysisTaskResponse(**task_info)

    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise


@router.post("/tasks/{task_id}/cancel", response_model=MessageResponse)
async def cancel_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    取消/停止任务（统一接口）

    智能判断任务状态：
    - 运行中的任务（RUNNING）：使用 stop 停止执行
    - 其他状态（PENDING/QUEUED）：使用 cancel 取消

    Args:
        task_id: 任务 ID
        current_user: 当前用户

    Returns:
        操作结果
    """
    task_manager = get_task_manager()

    try:
        # 验证任务所有权
        task_info = await task_manager.get_task_status(task_id)
        if task_info["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权操作此任务")

        # 根据任务状态智能判断
        status = task_info.get("status")
        if status == TaskStatusEnum.RUNNING.value:
            # 运行中的任务使用 stop
            await task_manager.stop_task(task_id)
            return MessageResponse(message="任务已停止", success=True)
        else:
            # 其他状态使用 cancel
            await task_manager.cancel_task(task_id)
            return MessageResponse(message="任务已取消", success=True)

    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise


@router.get("/tasks/{task_id}/stream")
async def stream_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """
    SSE 流式输出任务报告

    Args:
        task_id: 任务 ID
        current_user: 当前用户

    Returns:
        SSE 流式响应
    """
    task_manager = get_task_manager()

    try:
        # 验证任务所有权
        task_info = await task_manager.get_task_status(task_id)
        if task_info["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权访问此任务")

        async def event_stream():
            """
            SSE 事件流生成器

            当任务进入第四阶段时，流式输出最终报告。
            """
            while True:
                try:
                    # 获取最新任务状态
                    current_state = await task_manager.get_task_status(task_id)

                    # 如果任务完成且在第四阶段，流式输出报告
                    if current_state.get("status") == "completed":
                        final_report = current_state.get("final_report")
                        if final_report:
                            # 分块发送报告
                            chunk_size = 100
                            for i in range(0, len(final_report), chunk_size):
                                chunk = final_report[i:i + chunk_size]
                                yield f"data: {json.dumps({'type': 'report_chunk', 'content': chunk}, ensure_ascii=False)}\\n\\n"
                            yield f"data: {json.dumps({'type': 'report_complete'}, ensure_ascii=False)}\\n\\n"
                            break
                        else:
                            # 没有报告，结束流
                            yield f"data: {json.dumps({'type': 'no_report'}, ensure_ascii=False)}\\n\\n"
                            break

                    # 如果任务失败或取消
                    elif current_state.get("status") in ["failed", "cancelled", "stopped", "expired"]:
                        yield f"data: {json.dumps({'type': 'task_ended', 'status': current_state.get('status')}, ensure_ascii=False)}\\n\\n"
                        break

                    # 如果任务仍在进行，发送心跳
                    else:
                        yield f"data: {json.dumps({'type': 'heartbeat', 'status': current_state.get('status')}, ensure_ascii=False)}\\n\\n"
                        # 根据任务状态动态调整轮询间隔
                        if current_state.get("status") == "running":
                            await asyncio.sleep(0.5)  # 进行中时轮询更快
                        else:
                            await asyncio.sleep(2)  # 其他状态轮询较慢

                except Exception as e:
                    logger.error(f"SSE 流式输出错误: task_id={task_id}, error={e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\\n\\n"
                    break

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise


@router.delete("/tasks/clear")
async def clear_tasks_by_status(
    statuses: str = Query(..., description="要清空的状态列表，逗号分隔，例如: failed,cancelled,stopped"),
    delete_reports: bool = Query(False, description="是否同时删除关联报告"),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    批量清空指定状态的所有任务

    仅支持清空失败、已取消、已终止状态的任务。
    用户只能清空自己的任务。

    Args:
        statuses: 状态列表（逗号分隔）
        delete_reports: 是否同时删除关联报告
        current_user: 当前用户

    Returns:
        删除结果
    """
    from bson import ObjectId

    # 解析状态列表
    status_list = [s.strip() for s in statuses.split(",")]

    # 安全检查：仅允许清空失败、取消、终止状态
    allowed_statuses = {
        TaskStatusEnum.FAILED.value,
        TaskStatusEnum.CANCELLED.value,
        TaskStatusEnum.STOPPED.value,
        TaskStatusEnum.EXPIRED.value,
    }
    invalid_statuses = set(status_list) - allowed_statuses
    if invalid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"不允许清空以下状态: {', '.join(invalid_statuses)}. 仅允许清空失败、已取消、已终止状态的任务"
        )

    user_id = str(current_user.id)

    # 构建查询条件
    query = {
        "user_id": user_id,
        "status": {"$in": status_list}
    }

    # 先统计要删除的数量
    count = await mongodb.database.analysis_tasks.count_documents(query)

    if count == 0:
        return MessageResponse(
            message=f"没有找到需要清空的任务",
            success=False
        )

    logger.info(f"用户 {user_id} 清空任务", {
        "statuses": status_list,
        "count": count,
        "delete_reports": delete_reports
    })

    # 执行删除
    delete_result = await mongodb.database.analysis_tasks.delete_many(query)

    # 如果需要删除关联报告
    if delete_reports:
        # 查询已删除任务的 ID
        task_ids = [str(tid) for tid in await mongodb.database.analysis_tasks.distinct("_id", query)]
        if task_ids:
            await mongodb.database.analysis_reports.delete_many({"task_id": {"$in": task_ids}})

    # 记录审计日志
    from core.admin.audit_logger import get_audit_logger
    audit_logger = get_audit_logger()
    await audit_logger.log_action(
        user_id=user_id,
        action="clear_tasks",
        details={
            "statuses": status_list,
            "deleted_count": delete_result.deleted_count,
            "delete_reports": delete_reports
        }
    )

    return MessageResponse(
        message=f"已清空 {delete_result.deleted_count} 个任务",
        success=True
    )


@router.delete("/tasks/batch-delete")
async def batch_delete_tasks(
    task_ids: list[str],
    delete_reports: bool = Query(False, description="是否同时删除关联报告"),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    批量删除指定的任务

    验证每个任务的所有权，仅删除属于当前用户的任务。
    不允许删除运行中的任务。

    Args:
        task_ids: 任务 ID 列表
        delete_reports: 是否同时删除关联报告
        current_user: 当前用户

    Returns:
        删除结果
    """
    from bson import ObjectId

    # 安全检查：限制批量删除数量
    if len(task_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="单次批量删除最多支持 100 个任务"
        )

    user_id = str(current_user.id)
    success_count = 0
    failed_tasks = []

    logger.info(f"用户 {user_id} 批量删除任务", {
        "task_ids_count": len(task_ids),
        "delete_reports": delete_reports
    })

    # 逐个验证和删除任务
    for task_id in task_ids:
        try:
            # 验证 ObjectId 格式
            obj_id = ObjectId(task_id)

            # 查询任务
            task = await mongodb.database.analysis_tasks.find_one({"_id": obj_id})

            if not task:
                failed_tasks.append({"task_id": task_id, "reason": "任务不存在"})
                continue

            # 验证所有权
            if task["user_id"] != user_id:
                failed_tasks.append({"task_id": task_id, "reason": "无权操作此任务"})
                continue

            # 检查任务状态，运行中的任务不能删除
            if task["status"] == TaskStatusEnum.RUNNING.value:
                failed_tasks.append({"task_id": task_id, "reason": "运行中的任务不能删除"})
                continue

            # 删除任务
            await mongodb.database.analysis_tasks.delete_one({"_id": obj_id})

            # 如果需要删除关联报告
            if delete_reports:
                await mongodb.database.analysis_reports.delete_many({"task_id": task_id})

            success_count += 1

        except Exception as e:
            logger.error(f"批量删除任务失败: task_id={task_id}, error={e}")
            failed_tasks.append({"task_id": task_id, "reason": str(e)})

    # 记录审计日志
    from core.admin.audit_logger import get_audit_logger
    audit_logger = get_audit_logger()
    await audit_logger.log_action(
        user_id=user_id,
        action="batch_delete_tasks",
        details={
            "total": len(task_ids),
            "success_count": success_count,
            "failed_count": len(failed_tasks),
            "delete_reports": delete_reports
        }
    )

    return {
        "success_count": success_count,
        "failed_count": len(failed_tasks),
        "failed_tasks": failed_tasks,
        "message": f"成功删除 {success_count} 个任务" + (f"，失败 {len(failed_tasks)} 个" if failed_tasks else "")
    }


@router.delete("/tasks/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: str,
    delete_reports: bool = Query(False, description="是否同时删除关联报告"),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    删除单个任务

    Args:
        task_id: 任务 ID
        delete_reports: 是否同时删除关联报告
        current_user: 当前用户

    Returns:
        操作结果
    """
    task_manager = get_task_manager()

    try:
        # 验证任务所有权
        task_info = await task_manager.get_task_status(task_id)
        if task_info["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权操作此任务")

        # 检查任务状态，运行中的任务不能删除
        if task_info["status"] == TaskStatusEnum.RUNNING.value:
            raise HTTPException(status_code=400, detail="运行中的任务不能删除，请先取消任务")

        # 删除任务
        from bson import ObjectId
        await mongodb.database.analysis_tasks.delete_one({"_id": ObjectId(task_id)})

        # 如果需要删除关联报告
        if delete_reports:
            await mongodb.database.analysis_reports.delete_many({"task_id": task_id})

        return MessageResponse(
            message="任务已删除",
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise


@router.post("/tasks/{task_id}/retry", response_model=AnalysisTaskResponse)
async def retry_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    重试失败的任务

    创建一个新任务，使用相同的分析参数。

    Args:
        task_id: 原任务 ID
        current_user: 当前用户

    Returns:
        新创建的任务信息
    """
    task_manager = get_task_manager()

    try:
        # 获取原任务信息
        task_info = await task_manager.get_task_status(task_id)

        # 验证任务所有权
        if task_info["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权操作此任务")

        # 只有失败或已取消的任务可以重试
        if task_info["status"] not in [TaskStatusEnum.FAILED.value, TaskStatusEnum.CANCELLED.value, TaskStatusEnum.STOPPED.value, TaskStatusEnum.EXPIRED.value]:
            raise HTTPException(status_code=400, detail="只有失败、已取消、已停止或已过期的任务可以重试")

        # 获取原任务的配置
        from bson import ObjectId
        original_task = await mongodb.database.analysis_tasks.find_one({"_id": ObjectId(task_id)})

        if not original_task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 创建新任务请求（从原任务的 stages 字段重建配置）
        original_stages = original_task.get("stages", {})

        new_request = AnalysisTaskCreate(
            stock_code=original_task["stock_code"],
            market=original_task.get("market", "a_share"),  # 添加缺失字段
            trade_date=original_task["trade_date"],
            stages=AnalysisStagesConfig(**original_stages),  # 使用 stages 字段
            data_collection_model=original_task.get("data_collection_model"),  # 保留模型选择
            debate_model=original_task.get("debate_model"),  # 保留模型选择
        )

        # 创建新任务
        config = original_task.get("config_snapshot", {})

        task_create_task = asyncio.create_task(
            create_analysis_task_background(
                user_id=str(current_user.id),
                request=new_request,
                config=config
            )
        )

        new_task_id = await asyncio.wait_for(task_create_task, timeout=5.0)

        # 获取新任务信息
        new_task_info = await task_manager.get_task_status(new_task_id)

        return AnalysisTaskResponse(**new_task_info)

    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise


@router.get("/tasks/{task_id}/queue-position")
async def get_task_queue_position(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取任务在队列中的位置

    Args:
        task_id: 任务 ID
        current_user: 当前用户

    Returns:
        {
            "position": int,  # 队列位置（0 表示可以执行，>0 表示前面有任务）
            "waiting_count": int,  # 总等待任务数
        }
    """
    try:
        # 获取任务信息
        from bson import ObjectId
        task = await mongodb.database.analysis_tasks.find_one({"_id": ObjectId(task_id)})

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 检查权限
        if task["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权访问此任务")

        # 获取模型 ID
        model_id = task.get("model_id")
        if not model_id:
            return {
                "position": 0,
                "waiting_count": 0,
            }

        # 获取队列位置
        controller = get_concurrency_controller()
        queue_info = await controller.get_queue_position(model_id, task_id)

        return queue_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务队列位置失败: task_id={task_id}, error={e}")
        raise


# =============================================================================
# MCP 服务器管理端点已迁移到 modules/mcp/api/routes.py
# =============================================================================

# =============================================================================

# 智能体配置管理端点
# =============================================================================

@router.get("/agent-config", response_model=UserAgentConfigResponse)
async def get_agent_config(
    include_prompts: bool = Query(
        False,
        description="是否包含提示词（仅管理员可用）。普通用户将自动排除提示词以保护业务逻辑。"
    ),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取用户智能体配置

    返回生效配置（个人配置或公共配置）。

    Args:
        include_prompts: 是否包含提示词（role_definition）
            - 普通用户：强制为 False，返回精简配置（不含提示词）
            - 管理员：可指定 True，返回完整配置（含提示词）
        current_user: 当前用户

    Returns:
        用户智能体配置
    """
    # 检查用户权限：非管理员强制排除提示词
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    if not is_admin:
        include_prompts = False

    service = get_agent_config_service()
    config = await service.get_effective_config(str(current_user.id), include_prompts)

    if not config:
        raise HTTPException(status_code=404, detail="智能体配置不存在")

    return config


@router.put("/agent-config", response_model=UserAgentConfigResponse)
async def update_agent_config(
    request: UserAgentConfigUpdate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    更新用户智能体配置

    Args:
        request: 更新请求
        current_user: 当前用户

    Returns:
        更新后的配置
    """
    service = get_agent_config_service()
    config = await service.update_user_config(str(current_user.id), request)

    if not config:
        raise HTTPException(status_code=404, detail="智能体配置不存在")

    return config


@router.post("/agent-config/reset", response_model=UserAgentConfigResponse)
async def reset_agent_config(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    重置为默认智能体配置

    重置为公共配置（模板）

    Args:
        current_user: 当前用户

    Returns:
        重置后的配置
    """
    service = get_agent_config_service()
    return await service.reset_to_public_config(str(current_user.id))


@router.get("/agent-config/public", response_model=UserAgentConfigResponse)
async def get_public_config(
    include_prompts: bool = Query(
        False,
        description="是否包含提示词。仅管理员可获取完整配置。"
    ),
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """
    获取公共智能体配置（模板）

    仅管理员可访问

    Args:
        include_prompts: 是否包含提示词
        current_admin: 当前管理员

    Returns:
        公共智能体配置
    """
    service = get_agent_config_service()
    config = await service.get_public_config()

    if not config:
        raise HTTPException(status_code=404, detail="公共配置不存在")

    # 如果不需要包含提示词，进行过滤
    if not include_prompts:
        config = filter_sensitive_prompts(config)

    return config


@router.put("/agent-config/public", response_model=UserAgentConfigResponse)
async def update_public_config(
    request: UserAgentConfigUpdate,
    current_admin: UserModel = Depends(get_current_admin_user),
):
    """
    更新公共智能体配置（模板）

    仅管理员可访问。更新公共配置后，未自定义的用户会使用新配置。

    Args:
        request: 更新请求
        current_admin: 当前管理员

    Returns:
        更新后的公共配置
    """
    service = get_agent_config_service()
    config = await service.update_public_config(request, str(current_admin.id))

    if not config:
        raise HTTPException(status_code=404, detail="公共配置更新失败")

    return config


@router.post("/agent-config/export")
async def export_agent_config(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    导出智能体配置

    Args:
        current_user: 当前用户

    Returns:
        配置数据
    """
    service = get_agent_config_service()
    config = await service.export_config(str(current_user.id))

    if not config:
        raise HTTPException(status_code=404, detail="智能体配置不存在")

    return {"config": config}


@router.post("/agent-config/import", response_model=UserAgentConfigResponse)
async def import_agent_config(
    config_data: dict,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    导入智能体配置

    Args:
        config_data: 配置数据
        current_user: 当前用户

    Returns:
        导入后的配置
    """
    service = get_agent_config_service()
    config = await service.import_config(str(current_user.id), config_data)

    if not config:
        raise HTTPException(status_code=400, detail="导入配置失败")

    return config


# =============================================================================
# TradingAgents 设置端点
# =============================================================================

@router.get("/settings", response_model=TradingAgentsSettingsResponse)
async def get_settings(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取用户的 TradingAgents 设置

    返回用户的分析规则配置，包括 AI 模型、辩论轮次、超时等设置。

    Args:
        current_user: 当前用户

    Returns:
        用户设置，如果不存在则返回默认设置
    """
    from modules.trading_agents.services.settings_service import get_trading_agents_settings_service

    service = get_trading_agents_settings_service()
    settings = await service.get_user_settings(str(current_user.id))

    if not settings:
        # 返回默认设置
        from modules.trading_agents.schemas import TradingAgentsSettings, TradingAgentsSettingsResponse
        from datetime import datetime

        default_settings = TradingAgentsSettings()
        return TradingAgentsSettingsResponse(
            id="",
            user_id=str(current_user.id),
            settings=default_settings,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    return settings


@router.put("/settings", response_model=TradingAgentsSettingsResponse)
async def update_settings(
    request: TradingAgentsSettings,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    更新用户的 TradingAgents 设置

    更新用户的分析规则配置，包括 AI 模型、辩论轮次、超时等设置。

    Args:
        request: 设置数据
        current_user: 当前用户

    Returns:
        更新后的设置
    """
    from modules.trading_agents.services.settings_service import get_trading_agents_settings_service

    service = get_trading_agents_settings_service()
    updated = await service.update_user_settings(str(current_user.id), request)

    return updated


# =============================================================================
# 报告管理端点
# =============================================================================

@router.get("/reports")
async def list_reports(
    stock_code: Optional[str] = None,
    recommendation: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    列出用户的分析报告

    Args:
        stock_code: 股票代码过滤
        recommendation: 推荐结果过滤 (BUY/SELL/HOLD)
        risk_level: 风险等级过滤
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        报告列表
    """
    service = get_report_service()

    # 转换枚举值
    from modules.trading_agents.schemas import RecommendationEnum, RiskLevelEnum

    rec_enum = RecommendationEnum(recommendation) if recommendation else None
    risk_enum = RiskLevelEnum(risk_level) if risk_level else None

    reports = await service.list_reports(
        user_id=str(current_user.id),
        stock_code=stock_code,
        recommendation=rec_enum,
        risk_level=risk_enum,
        limit=limit,
        offset=offset,
    )

    return {"reports": reports}


@router.get("/reports/summary", response_model=ReportSummaryResponse)
async def get_reports_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取报告统计摘要

    Args:
        days: 统计天数
        current_user: 当前用户

    Returns:
        统计摘要
    """
    service = get_report_service()
    return await service.get_reports_summary(str(current_user.id), days)


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取单个报告详情

    Args:
        report_id: 报告 ID
        current_user: 当前用户

    Returns:
        报告详情
    """
    service = get_report_service()
    report = await service.get_report(report_id, str(current_user.id))

    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return report


@router.delete("/reports/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    删除报告

    Args:
        report_id: 报告 ID
        current_user: 当前用户

    Returns:
        操作结果
    """
    service = get_report_service()
    success = await service.delete_report(report_id, str(current_user.id))

    if not success:
        raise HTTPException(status_code=404, detail="报告不存在或无权删除")

    return MessageResponse(message="报告已删除", success=True)


# =============================================================================
# 健康检查端点
# =============================================================================

@router.get("/health", response_model=dict)
async def health_check():
    """
    健康检查端点

    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "module": "TradingAgents",
    }
