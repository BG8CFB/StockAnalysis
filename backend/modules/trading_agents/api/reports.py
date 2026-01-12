"""
报告管理 API 路由
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from core.auth.dependencies import get_current_active_user
from core.auth.security import jwt_manager
from core.user.models import UserModel

from modules.trading_agents.services.report_service import get_report_service, ReportService
from modules.trading_agents.services.settings_service import get_trading_agents_settings_service
from modules.trading_agents.pusher import get_ws_manager, WebSocketManager
from modules.trading_agents.schemas import (
    ReportSummaryResponse,
    MessageResponse,
    RecommendationEnum,
    RiskLevelEnum,
    TradingAgentsSettings,
    TradingAgentsSettingsResponse,
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/trading-agents/reports", tags=["TradingAgents - 报告管理"])


# =============================================================================
# 报告查询端点
# =============================================================================

@router.get("")
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


@router.get("/summary", response_model=ReportSummaryResponse)
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


@router.get("/{report_id}")
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


# =============================================================================
# 报告删除端点
# =============================================================================

@router.delete("/{report_id}", response_model=MessageResponse)
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
# TradingAgents 设置管理 API 路由（从 settings.py 合并）
# =============================================================================

# 创建设置路由器
settings_router = APIRouter(prefix="/trading-agents/settings", tags=["TradingAgents - 设置"])


@settings_router.get("", response_model=TradingAgentsSettingsResponse)
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
    service = get_trading_agents_settings_service()
    settings = await service.get_user_settings(str(current_user.id))

    if not settings:
        # 返回默认设置
        default_settings = TradingAgentsSettings()
        return TradingAgentsSettingsResponse(
            id="",
            user_id=str(current_user.id),
            settings=default_settings,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    return settings


@settings_router.put("", response_model=TradingAgentsSettingsResponse)
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
    service = get_trading_agents_settings_service()
    updated = await service.update_user_settings(str(current_user.id), request)

    return updated


# =============================================================================
# WebSocket API 路由（从 websocket.py 合并）
# =============================================================================

# 创建 WebSocket 路由器
websocket_router = APIRouter(prefix="/trading-agents", tags=["TradingAgents - WebSocket"])


@websocket_router.websocket("/ws/{task_id}")
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

    ws_manager: WebSocketManager = get_ws_manager()

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
# 健康检查 API 路由（从 health.py 合并）
# =============================================================================

# 创建健康检查路由器
health_router = APIRouter(prefix="/trading-agents", tags=["TradingAgents - 健康检查"])


@health_router.get("/health", response_model=dict)
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
