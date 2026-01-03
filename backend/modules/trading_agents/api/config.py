"""
智能体配置管理 API 路由
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth.dependencies import get_current_active_user
from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel
from core.auth.rbac import Role

from modules.trading_agents.services.agent_config_service import get_agent_config_service
from modules.trading_agents.schemas import (
    UserAgentConfigResponse,
    UserAgentConfigUpdate,
    MessageResponse,
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/trading-agents/agent-config", tags=["TradingAgents - 智能体配置"])


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
# 用户智能体配置端点
# =============================================================================

@router.get("", response_model=UserAgentConfigResponse)
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


@router.put("", response_model=UserAgentConfigResponse)
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


@router.post("/reset", response_model=UserAgentConfigResponse)
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


@router.post("/export")
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


@router.post("/import", response_model=UserAgentConfigResponse)
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
# 公共智能体配置端点（管理员专用）
# =============================================================================

@router.get("/public", response_model=UserAgentConfigResponse)
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


@router.put("/public", response_model=UserAgentConfigResponse)
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
