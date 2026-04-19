"""
工具管理 API

提供可用工具列表、MCP 工具管理和可用性摘要接口。
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from core.user.dependencies import get_current_admin_user
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


class ToggleRequest(BaseModel):
    """工具开关请求"""
    enabled: bool


def _get_tool_registry():
    """获取工具注册表（延迟导入）"""
    try:
        from core.mcp.service.mcp_service import get_mcp_service
        return get_mcp_service()
    except Exception:
        return None


def _get_default_tools() -> list:
    """获取内置默认工具列表"""
    return [
        {"name": "stock_data", "description": "获取股票行情数据", "source": "local"},
        {"name": "financial_data", "description": "获取财务指标数据", "source": "local"},
        {"name": "news_data", "description": "获取新闻数据", "source": "local"},
        {"name": "technical_analysis", "description": "技术分析工具", "source": "local"},
        {"name": "market_overview", "description": "市场概览工具", "source": "local"},
    ]


# 内存存储 MCP 工具的启用/禁用状态
_mcp_tool_states: Dict[str, bool] = {}


@router.get("/available")
async def list_available_tools(
    include_mcp: bool = Query(True),
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取可用工具列表"""
    tools = _get_default_tools()

    if include_mcp:
        try:
            service = _get_tool_registry()
            if service:
                # 获取所有 MCP 服务器的工具
                servers = await service.list_servers("system_admin", is_admin=True)
                for server in (servers.get("system", []) + servers.get("user", [])):
                    if server.enabled:
                        server_tools = await service.get_server_tools(
                            str(server.id), "system_admin", is_admin=True,
                        )
                        for tool in server_tools:
                            tools.append({
                                "name": tool.get("name", ""),
                                "description": tool.get("description", ""),
                                "source": f"mcp:{server.name}",
                            })
        except Exception as e:
            logger.warning(f"获取 MCP 工具列表失败: {e}")

    return {
        "code": 0,
        "message": "success",
        "data": {"data": tools, "count": len(tools)},
    }


@router.get("/mcp")
async def list_mcp_tools(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """列出 MCP 工具"""
    mcp_tools = []
    try:
        service = _get_tool_registry()
        if service:
            servers = await service.list_servers("system_admin", is_admin=True)
            for server in (servers.get("system", []) + servers.get("user", [])):
                if server.enabled:
                    try:
                        server_tools = await service.get_server_tools(
                            str(server.id), "system_admin", is_admin=True,
                        )
                        for tool in server_tools:
                            tool_name = tool.get("name", "")
                            is_enabled = _mcp_tool_states.get(tool_name, True)
                            mcp_tools.append({
                                "name": tool_name,
                                "description": tool.get("description", ""),
                                "source": f"mcp:{server.name}",
                                "category": server.name,
                                "available": True,
                                "tushare_only": False,
                                "enabled": is_enabled,
                            })
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"列出 MCP 工具失败: {e}")

    total = len(mcp_tools)
    available = sum(1 for t in mcp_tools if t["available"])
    enabled = sum(1 for t in mcp_tools if t["enabled"])

    return {
        "code": 0,
        "message": "success",
        "data": {
            "data": mcp_tools,
            "count": total,
            "summary": {
                "total": total,
                "available": available,
                "unavailable": total - available,
                "enabled": enabled,
                "disabled": total - enabled,
                "tushare_only": 0,
                "tushare_available": False,
            },
        },
    }


@router.patch("/mcp/{name}/toggle")
async def toggle_mcp_tool(
    name: str,
    request: ToggleRequest,
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """启用/禁用 MCP 工具"""
    _mcp_tool_states[name] = request.enabled
    status_text = "启用" if request.enabled else "禁用"
    logger.info(f"管理员 {current_admin.username} {status_text}了 MCP 工具: {name}")

    return {
        "code": 0,
        "message": "success",
        "data": {
            "data": {
                "name": name,
                "enabled": request.enabled,
                "message": f"工具 {name} 已{status_text}",
            }
        },
    }


@router.get("/mcp/availability-summary")
async def get_mcp_availability_summary(
    current_admin: UserModel = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """获取 MCP 工具可用性摘要"""
    try:
        service = _get_tool_registry()
        by_category: Dict[str, Any] = {}
        all_tools: list = []
        disabled_tools: list = []

        if service:
            servers = await service.list_servers("system_admin", is_admin=True)
            for server in (servers.get("system", []) + servers.get("user", [])):
                cat_name = server.name
                cat_total = 0
                cat_available = 0
                cat_enabled = 0

                try:
                    server_tools = await service.get_server_tools(
                        str(server.id), "system_admin", is_admin=True,
                    )
                    for tool in server_tools:
                        tool_name = tool.get("name", "")
                        is_enabled = _mcp_tool_states.get(tool_name, True)
                        all_tools.append({
                            "name": tool_name,
                            "available": True,
                            "enabled": is_enabled,
                        })
                        cat_total += 1
                        cat_available += 1
                        if is_enabled:
                            cat_enabled += 1
                        else:
                            disabled_tools.append(tool_name)
                except Exception:
                    pass

                if cat_total > 0:
                    by_category[cat_name] = {
                        "total": cat_total,
                        "available": cat_available,
                        "enabled": cat_enabled,
                    }

        total = len(all_tools)
        available = sum(1 for t in all_tools if t["available"])
        enabled = sum(1 for t in all_tools if t["enabled"])

        return {
            "code": 0,
            "message": "success",
            "data": {
                "data": {
                    "total": total,
                    "available": available,
                    "unavailable": total - available,
                    "enabled": enabled,
                    "disabled": total - enabled,
                    "tushare_available": False,
                    "by_category": by_category,
                    "disabled_tools": disabled_tools,
                }
            },
        }
    except Exception as e:
        return {
            "code": 0,
            "message": "success",
            "data": {
                "data": {
                    "total": 0, "available": 0, "unavailable": 0,
                    "enabled": 0, "disabled": 0, "tushare_available": False,
                    "by_category": {}, "disabled_tools": [],
                }
            },
        }
