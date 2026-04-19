"""
MCP API 路由

提供 MCP 服务器管理的 API 端点。
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth.dependencies import get_current_active_user
from core.auth.rbac import Role
from core.mcp.config.loader import reload_mcp_config
from core.mcp.config.settings_models import MCPSystemSettingsCreate, MCPSystemSettingsResponse
from core.mcp.config.settings_service import (
    get_system_settings,
    reset_to_defaults,
    update_system_settings,
)
from core.mcp.pool.pool import get_mcp_connection_pool
from core.mcp.schemas import (
    ConnectionTestResponse,
    MCPServerConfigCreate,
    MCPServerConfigResponse,
    MCPServerConfigUpdate,
)
from core.mcp.service.mcp_service import get_mcp_service
from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/mcp", tags=["MCP"])


# =============================================================================
# MCP 服务器管理端点
# =============================================================================


@router.post("/servers", response_model=MCPServerConfigResponse)
async def create_mcp_server(
    request: MCPServerConfigCreate,
    current_user: UserModel = Depends(get_current_active_user),
) -> MCPServerConfigResponse:
    """
    创建 MCP 服务器配置

    Args:
        request: 服务器配置请求
        current_user: 当前用户

    Returns:
        创建的服务器配置

    Note:
        - is_system=True: 只有管理员可以创建公共服务
        - is_system=False: 任何用户都可以创建个人服务
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_mcp_service()
    return await service.create_server(str(current_user.id), request, is_admin)


@router.get("/servers")
async def list_mcp_servers(
    current_user: UserModel = Depends(get_current_active_user),
) -> dict:
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


@router.get("/servers/{server_id}", response_model=MCPServerConfigResponse)
async def get_mcp_server(
    server_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> MCPServerConfigResponse:
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


@router.put("/servers/{server_id}", response_model=MCPServerConfigResponse)
async def update_mcp_server(
    server_id: str,
    request: MCPServerConfigUpdate,
    current_user: UserModel = Depends(get_current_active_user),
) -> MCPServerConfigResponse:
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


@router.delete("/servers/{server_id}")
async def delete_mcp_server(
    server_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> dict:
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

    return {"message": "MCP 服务器配置已删除", "success": True}


@router.post("/servers/{server_id}/test", response_model=ConnectionTestResponse)
async def test_mcp_server(
    server_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> ConnectionTestResponse:
    """
    测试 MCP 服务器连接

    手动触发连接测试，返回详细的测试结果（包括延迟）。

    Args:
        server_id: 服务器 ID
        current_user: 当前用户

    Returns:
        测试结果（包含延迟信息）
    """
    is_admin = current_user.role in [Role.ADMIN, Role.SUPER_ADMIN]
    service = get_mcp_service()
    return await service.test_server_connection(server_id, str(current_user.id), is_admin)


@router.get("/servers/{server_id}/tools")
async def get_mcp_server_tools(
    server_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> dict:
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
# 连接池管理端点（管理员）
# =============================================================================


@router.get("/pool/stats")
async def get_pool_stats(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> dict:
    """
    获取连接池统计信息

    仅管理员可访问。返回连接池的状态、活跃连接、并发限制等信息。

    Args:
        current_admin: 当前管理员

    Returns:
        连接池统计信息
    """
    pool = get_mcp_connection_pool()
    stats = await pool.get_connection_stats()

    # 添加服务器配置信息
    service = get_mcp_service()
    all_servers = await service.list_servers("system_admin", is_admin=True)

    server_info = {}
    for server in all_servers.get("system", []) + all_servers.get("user", []):
        server_info[server.id] = {
            "name": server.name,
            "is_system": server.is_system,
            "owner_id": server.owner_id,
            "status": server.status.value,
            "enabled": server.enabled,
        }

    return {
        "pool": stats,
        "servers": server_info,
    }


@router.post("/pool/servers/{server_id}/disable")
async def disable_mcp_server(
    server_id: str,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> dict:
    """
    禁用 MCP 服务器（停止接受新任务）

    仅管理员可访问。禁用后：
    - 已有连接继续运行
    - 新任务无法获取连接
    - 任务完成后自然销毁

    Args:
        server_id: 服务器 ID
        current_admin: 当前管理员

    Returns:
        操作结果
    """
    pool = get_mcp_connection_pool()
    await pool.disable_server(server_id)

    # 同时更新数据库中的 enabled 状态
    service = get_mcp_service()
    server = await service.get_server(server_id, str(current_admin.id), is_admin=True)
    if server:
        await service.update_server(
            server_id,
            str(current_admin.id),
            MCPServerConfigUpdate(name=server.name, enabled=False),  # type: ignore[call-arg]
            is_admin=True,
        )

    return {"message": "MCP 服务器已禁用", "success": True}


# =============================================================================
# 系统配置管理端点
# =============================================================================


@router.get("/settings", response_model=MCPSystemSettingsResponse)
async def get_mcp_settings(
    current_user: UserModel = Depends(get_current_active_user),
) -> MCPSystemSettingsResponse:
    """
    获取 MCP 系统配置

    所有用户都可以读取系统配置。
    配置加载优先级：数据库 > YAML 默认配置 > 环境变量

    Args:
        current_user: 当前用户

    Returns:
        系统配置
    """
    db_settings = await get_system_settings()

    if not db_settings:
        # 数据库无配置，返回默认值
        logger.debug("数据库中无 MCP 系统配置，返回默认值")
        return MCPSystemSettingsResponse()

    return MCPSystemSettingsResponse.from_db(db_settings)


@router.put("/settings", response_model=MCPSystemSettingsResponse)
async def update_mcp_settings(
    settings: MCPSystemSettingsCreate,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> MCPSystemSettingsResponse:
    """
    更新 MCP 系统配置

    仅管理员可访问。更新后立即对所有用户生效。

    Args:
        settings: 系统配置
        current_admin: 当前管理员

    Returns:
        更新后的系统配置
    """
    # 将 Pydantic 模型转换为字典
    settings_dict = settings.model_dump()

    # 保存到数据库
    await update_system_settings(settings_dict)

    # 重新加载配置（清除缓存）
    reload_mcp_config()

    logger.info(f"MCP 系统配置已更新并重新加载: operator={current_admin.username}")

    # 返回更新后的配置
    return MCPSystemSettingsResponse.from_db(settings_dict)


@router.post("/settings/reset")
async def reset_mcp_settings(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> dict:
    """
    恢复 MCP 系统配置为默认值

    仅管理员可访问。删除数据库中的配置，恢复为 YAML 默认配置。
    恢复后立即对所有用户生效。

    Args:
        current_admin: 当前管理员

    Returns:
        操作结果
    """
    # 删除数据库中的配置
    await reset_to_defaults()

    # 重新加载配置（清除缓存）
    reload_mcp_config()

    logger.info(f"MCP 系统配置已恢复为默认值: operator={current_admin.username}")

    return {
        "message": "MCP 系统配置已恢复为默认值",
        "success": True,
    }


# =============================================================================
# 健康检查端点
# =============================================================================


@router.get("/health")
async def health_check() -> dict:
    """
    健康检查端点

    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "module": "MCP",
    }


@router.post("/health-check")
async def trigger_health_check(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> dict:
    """
    手动触发 MCP 健康检查

    对所有已启用的 MCP 服务器执行连接测试，更新状态缓存。

    Args:
        current_admin: 当前管理员

    Returns:
        健康检查结果
    """
    service = get_mcp_service()
    is_admin = True
    servers = await service.list_servers(str(current_admin.id), is_admin)
    results = {}
    for server in servers.get("system", []) + servers.get("user", []):
        if server.enabled:
            try:
                test_result = await service.test_server_connection(
                    server.id, str(current_admin.id), is_admin
                )
                results[server.id] = {
                    "name": server.name,
                    "success": test_result.success,
                    "message": test_result.message,
                }
            except Exception as e:
                results[server.id] = {
                    "name": server.name,
                    "success": False,
                    "message": str(e),
                }
    return {"success": True, "results": results, "total": len(results)}


@router.post("/reload")
async def reload_mcp(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> dict:
    """
    重新加载 MCP 配置

    从数据库重新加载所有 MCP 配置，刷新连接池。

    Args:
        current_admin: 当前管理员

    Returns:
        操作结果
    """
    reload_mcp_config()
    logger.info(f"MCP 配置已手动重载: operator={current_admin.username}")
    return {"message": "MCP 配置已重新加载", "success": True}


@router.post("/connectors/update")
async def update_mcp_connectors(
    data: dict[str, Any],
    current_admin: UserModel = Depends(get_current_admin_user),
) -> dict:
    """
    批量更新 MCP 连接器配置

    批量更新多个 MCP 服务器的启用状态等配置。

    Args:
        data: 更新数据（servers 列表）
        current_admin: 当前管理员

    Returns:
        操作结果
    """
    service = get_mcp_service()
    servers_data = data.get("servers", [])
    updated_count = 0
    failed_count = 0

    for server_data in servers_data:
        server_id = server_data.get("id") or server_data.get("server_id")
        if not server_id:
            failed_count += 1
            continue
        try:
            update = MCPServerConfigUpdate(
                enabled=server_data.get("enabled"),
            )
            await service.update_server(server_id, str(current_admin.id), update, is_admin=True)
            updated_count += 1
        except Exception as e:
            logger.warning(f"批量更新 MCP 连接器失败: server_id={server_id}, error={e}")
            failed_count += 1

    return {
        "message": f"已更新 {updated_count} 个连接器",
        "success": True,
        "updated": updated_count,
        "failed": failed_count,
    }
