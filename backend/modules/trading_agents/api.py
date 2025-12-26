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

from core.auth.dependencies import get_current_user, get_current_active_user
from core.user.models import UserModel
from core.db.mongodb import mongodb
from modules.trading_agents.core.task_manager import get_task_manager, TaskManager
from modules.trading_agents.websocket import get_ws_manager, WebSocketManager
from modules.trading_agents.schemas import (
    AnalysisTaskCreate,
    BatchTaskCreate,
    AnalysisTaskResponse,
    BatchTaskResponse,
    TaskStatusEnum,
    MessageResponse,
    AIModelConfigCreate,
    AIModelConfigUpdate,
    AIModelConfigResponse,
    AIModelTestRequest,
    ConnectionTestResponse,
    MCPServerConfigCreate,
    MCPServerConfigUpdate,
    MCPServerConfigResponse,
    UserAgentConfigCreate,
    UserAgentConfigUpdate,
    UserAgentConfigResponse,
)
from core.background_tasks import create_analysis_task_background
from modules.trading_agents.services.model_service import get_model_service
from modules.trading_agents.services.mcp_service import get_mcp_service
from modules.trading_agents.services.agent_config_service import get_agent_config_service
from modules.trading_agents.services.report_service import get_report_service, ReportService
from core.auth.rbac import Role, Permission

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/trading-agents", tags=["TradingAgents"])


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

@router.post("/tasks", response_model=AnalysisTaskResponse)
async def create_analysis_task(
    request: AnalysisTaskCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    创建单股分析任务

    使用后台任务创建任务，避免阻塞 HTTP 响应。
    数据库操作和 WebSocket 广播都在后台异步执行。

    Args:
        request: 分析任务请求
        current_user: 当前用户

    Returns:
        创建的任务信息
    """
    # 获取用户配置（TODO: 实现用户配置加载）
    config = {}

    # 使用 asyncio.create_task 在后台创建任务
    task_create_task = asyncio.create_task(
        create_analysis_task_background(
            user_id=str(current_user.id),
            request=request,
            config=config
        )
    )

    # 立即返回任务 ID（任务在后台创建）
    task_id = await asyncio.wait_for(task_create_task, timeout=5.0)

    # 获取任务信息（在后台任务执行后，数据应该已经插入）
    task_manager = get_task_manager()
    task_info = await task_manager.get_task_status(task_id)

    return AnalysisTaskResponse(**task_info)


@router.post("/tasks/batch", response_model=BatchTaskResponse)
async def create_batch_analysis_task(
    request: BatchTaskCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    创建批量分析任务

    Args:
        request: 批量任务请求
        current_user: 当前用户

    Returns:
        创建的批量任务信息
    """
    task_manager = get_task_manager()

    # TODO: 获取用户配置
    config = {}

    # 创建批量任务
    batch_id = await task_manager.create_batch_task(
        user_id=str(current_user.id),
        request=request,
        config=config,
    )

    return BatchTaskResponse(
        id=batch_id,
        user_id=str(current_user.id),
        stock_codes=request.stock_codes,
        total_count=len(request.stock_codes),
        completed_count=0,
        failed_count=0,
        status=TaskStatusEnum.PENDING,
        created_at=None,  # TODO: 从数据库获取
    )


@router.get("/tasks")
async def list_tasks(
    status: Optional[TaskStatusEnum] = None,
    stock_code: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    列出用户的分析任务

    Args:
        status: 状态过滤
        stock_code: 股票代码过滤
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
        limit=limit,
        offset=offset,
    )

    return {"tasks": tasks}


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
    取消任务

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

        await task_manager.cancel_task(task_id)

        return MessageResponse(
            message="任务已取消",
            success=True
        )

    except Exception as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="任务不存在")
        raise


@router.post("/tasks/{task_id}/stop", response_model=MessageResponse)
async def stop_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    停止任务（中止执行）

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

        # 请求停止任务
        await task_manager.stop_task(task_id)

        return MessageResponse(
            message="任务停止请求已发送",
            success=True
        )

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
                                yield f"data: {json.dumps({'type': 'report_chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
                            yield f"data: {json.dumps({'type': 'report_complete'}, ensure_ascii=False)}\n\n"
                            break
                        else:
                            # 没有报告，结束流
                            yield f"data: {json.dumps({'type': 'no_report'}, ensure_ascii=False)}\n\n"
                            break

                    # 如果任务失败或取消
                    elif current_state.get("status") in ["failed", "cancelled", "stopped"]:
                        yield f"data: {json.dumps({'type': 'task_ended', 'status': current_state.get('status')}, ensure_ascii=False)}\n\n"
                        break

                    # 如果任务仍在进行，发送心跳
                    else:
                        yield f"data: {json.dumps({'type': 'heartbeat', 'status': current_state.get('status', 'pending')}, ensure_ascii=False)}\n\n"
                        # 根据任务状态动态调整轮询间隔
                        if current_state.get("status") == "running":
                            await asyncio.sleep(0.5)  # 进行中时轮询更快
                        else:
                            await asyncio.sleep(2)  # 其他状态轮询较慢

                except Exception as e:
                    logger.error(f"SSE 流式输出错误: task_id={task_id}, error={e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
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


@router.delete("/tasks/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    删除任务

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

        # 检查任务状态，运行中的任务不能删除
        if task_info["status"] == TaskStatusEnum.RUNNING.value:
            raise HTTPException(status_code=400, detail="运行中的任务不能删除，请先取消任务")

        # 删除任务
        from bson import ObjectId
        await mongodb.database.analysis_tasks.delete_one({"_id": ObjectId(task_id)})

        # 同时删除关联的报告
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

        # 创建新任务请求
        new_request = AnalysisTaskCreate(
            stock_code=original_task["stock_code"],
            trade_date=original_task["trade_date"],
            phase2_enabled=original_task.get("phase2_enabled", True),
            phase3_enabled=original_task.get("phase3_enabled", True),
            phase4_enabled=original_task.get("phase4_enabled", True),
            max_debate_rounds=original_task.get("max_debate_rounds"),
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


# =============================================================================
# AI 模型管理端点
# =============================================================================

@router.post("/models", response_model=AIModelConfigResponse)
async def create_model(
    request: AIModelConfigCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    创建 AI 模型配置

    Args:
        request: 模型配置请求
        current_user: 当前用户

    Returns:
        创建的模型配置
    """
    # 系统级配置需要管理员权限
    if request.is_system:
        # TODO: 添加管理员权限检查
        pass

    service = get_model_service()
    return await service.create_model(str(current_user.id), request)


@router.get("/models")
async def list_models(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    列出 AI 模型配置

    Args:
        current_user: 当前用户

    Returns:
        模型配置列表 {"system": [...], "user": [...]}
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    return await service.list_models(str(current_user.id), is_admin)


@router.get("/models/{model_id}", response_model=AIModelConfigResponse)
async def get_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取单个 AI 模型配置

    Args:
        model_id: 模型 ID
        current_user: 当前用户

    Returns:
        模型配置
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    model = await service.get_model(model_id, str(current_user.id), is_admin)

    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    return model


@router.put("/models/{model_id}", response_model=AIModelConfigResponse)
async def update_model(
    model_id: str,
    request: AIModelConfigUpdate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    更新 AI 模型配置

    Args:
        model_id: 模型 ID
        request: 更新请求
        current_user: 当前用户

    Returns:
        更新后的模型配置
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    model = await service.update_model(model_id, str(current_user.id), request, is_admin)

    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在或无权修改")

    return model


@router.delete("/models/{model_id}", response_model=MessageResponse)
async def delete_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    删除 AI 模型配置

    Args:
        model_id: 模型 ID
        current_user: 当前用户

    Returns:
        操作结果
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()
    success = await service.delete_model(model_id, str(current_user.id), is_admin)

    if not success:
        raise HTTPException(status_code=404, detail="模型配置不存在或无权删除")

    return MessageResponse(message="模型配置已删除", success=True)


@router.post("/models/{model_id}/test", response_model=ConnectionTestResponse)
async def test_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    测试 AI 模型连接

    Args:
        model_id: 模型 ID
        current_user: 当前用户

    Returns:
        测试结果
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_model_service()

    # 获取模型配置
    model = await service.get_model(model_id, str(current_user.id), is_admin)
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    # 构建测试请求
    test_request = AIModelTestRequest(
        api_base_url=model.api_base_url,
        api_key=model.api_key,
        model_id=model.model_id,
        timeout_seconds=10,
    )

    return await service.test_model_connection(test_request)


@router.post("/models/test", response_model=ConnectionTestResponse)
async def test_model_connection(
    request: AIModelTestRequest,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    测试 AI 模型连接（通用接口）

    Args:
        request: 测试请求
        current_user: 当前用户

    Returns:
        测试结果
    """
    service = get_model_service()
    return await service.test_model_connection(request)


# =============================================================================
# MCP 服务器管理端点
# =============================================================================

@router.post("/mcp-servers", response_model=MCPServerConfigResponse)
async def create_mcp_server(
    request: MCPServerConfigCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    创建 MCP 服务器配置

    Args:
        request: 服务器配置请求
        current_user: 当前用户

    Returns:
        创建的服务器配置
    """
    service = get_mcp_service()
    return await service.create_server(str(current_user.id), request)


@router.get("/mcp-servers")
async def list_mcp_servers(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    列出 MCP 服务器配置

    Args:
        current_user: 当前用户

    Returns:
        服务器配置列表 {"system": [...], "user": [...]}
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_mcp_service()
    return await service.list_servers(str(current_user.id), is_admin)


@router.get("/mcp-servers/{server_id}", response_model=MCPServerConfigResponse)
async def get_mcp_server(
    server_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取单个 MCP 服务器配置

    Args:
        server_id: 服务器 ID
        current_user: 当前用户

    Returns:
        服务器配置
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_mcp_service()
    server = await service.get_server(server_id, str(current_user.id), is_admin)

    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务器配置不存在")

    return server


@router.put("/mcp-servers/{server_id}", response_model=MCPServerConfigResponse)
async def update_mcp_server(
    server_id: str,
    request: MCPServerConfigUpdate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    更新 MCP 服务器配置

    Args:
        server_id: 服务器 ID
        request: 更新请求
        current_user: 当前用户

    Returns:
        更新后的服务器配置
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_mcp_service()
    server = await service.update_server(server_id, str(current_user.id), request, is_admin)

    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务器配置不存在或无权修改")

    return server


@router.delete("/mcp-servers/{server_id}", response_model=MessageResponse)
async def delete_mcp_server(
    server_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    删除 MCP 服务器配置

    Args:
        server_id: 服务器 ID
        current_user: 当前用户

    Returns:
        操作结果
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_mcp_service()
    success = await service.delete_server(server_id, str(current_user.id), is_admin)

    if not success:
        raise HTTPException(status_code=404, detail="MCP 服务器配置不存在或无权删除")

    return MessageResponse(message="MCP 服务器配置已删除", success=True)


@router.post("/mcp-servers/{server_id}/test", response_model=ConnectionTestResponse)
async def test_mcp_server(
    server_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    测试 MCP 服务器连接

    Args:
        server_id: 服务器 ID
        current_user: 当前用户

    Returns:
        测试结果
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_mcp_service()
    return await service.test_server_connection(server_id, str(current_user.id), is_admin)


@router.get("/mcp-servers/{server_id}/tools")
async def get_mcp_server_tools(
    server_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取 MCP 服务器的工具列表

    Args:
        server_id: 服务器 ID
        current_user: 当前用户

    Returns:
        工具列表
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_mcp_service()
    return {"tools": await service.get_server_tools(server_id, str(current_user.id), is_admin)}


# =============================================================================
# 智能体配置管理端点
# =============================================================================

@router.get("/agent-config", response_model=UserAgentConfigResponse)
async def get_agent_config(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    获取用户智能体配置

    Args:
        current_user: 当前用户

    Returns:
        用户智能体配置
    """
    service = get_agent_config_service()
    config = await service.get_user_config(str(current_user.id), create_if_missing=True)

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

    Args:
        current_user: 当前用户

    Returns:
        重置后的配置
    """
    service = get_agent_config_service()
    return await service.reset_to_default(str(current_user.id))


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


@router.get("/reports/summary")
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
