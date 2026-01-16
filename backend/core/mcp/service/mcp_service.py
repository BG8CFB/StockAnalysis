"""
MCP 服务器配置管理服务

提供 MCP 服务器的 CRUD 操作和连接测试功能。
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from core.db.mongodb import mongodb
from core.mcp.adapter.adapter import (
    build_auth_headers,
    map_transport_mode,
)
from core.mcp.schemas import (
    AuthTypeEnum,
    ConnectionTestResponse,
    MCPServerConfigCreate,
    MCPServerConfigResponse,
    MCPServerConfigUpdate,
    MCPServerStatusEnum,
)

logger = logging.getLogger(__name__)


class MCPService:
    """
    MCP 服务器配置管理服务

    提供服务器的创建、更新、删除、查询和测试功能。
    """

    COLLECTION_NAME = "mcp_servers"

    def __init__(self):
        """初始化服务"""
        self._db = None

    async def _get_collection(self):
        """获取数据库集合"""
        return mongodb.get_collection(self.COLLECTION_NAME)

    # ========================================================================
    # CRUD 操作
    # ========================================================================

    async def create_server(
        self,
        user_id: str,
        request: MCPServerConfigCreate,
        is_admin: bool = False
    ) -> MCPServerConfigResponse:
        """
        创建 MCP 服务器配置

        Args:
            user_id: 用户 ID
            request: 创建请求
            is_admin: 是否为管理员（用于权限检查）

        Returns:
            创建的服务器配置
        """
        collection = await self._get_collection()

        # 权限检查：只有管理员可以创建系统级服务
        if request.is_system and not is_admin:
            raise PermissionError("只有管理员可以创建公共服务（系统级MCP）")

        # 验证环境变量格式
        if request.env:
            try:
                json.dumps(request.env)
            except (TypeError, ValueError) as e:
                raise ValueError(f"环境变量格式无效: {e}")

        # 创建文档
        doc = {
            "name": request.name,
            "transport": request.transport.value,
            # stdio 模式配置
            "command": request.command,
            "args": request.args or [],
            "env": request.env or {},
            # http/sse/websocket 模式配置
            "url": request.url,
            "headers": request.headers or {},
            # 认证配置（兼容旧版本）
            "auth_type": request.auth_type.value if request.auth_type else AuthTypeEnum.NONE.value,
            "auth_token": request.auth_token,
            # 通用配置
            "auto_approve": request.auto_approve or [],
            "enabled": request.enabled,
            "is_system": request.is_system,
            "owner_id": None if request.is_system else user_id,
            # 状态 - 创建后立即进行连接检测
            "status": MCPServerStatusEnum.UNKNOWN.value,
            "last_check_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # 插入数据库
        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(
            f"创建 MCP 服务器配置: name={request.name}, "
            f"transport={request.transport}, user={user_id}, "
            f"is_system={request.is_system}"
        )

        # 创建后立即进行状态检测（异步后台任务）
        server_id = str(result.inserted_id)
        asyncio.create_task(self._check_server_status_after_create(server_id))

        return MCPServerConfigResponse.from_db(doc)

    async def get_server(
        self,
        server_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> Optional[MCPServerConfigResponse]:
        """
        获取单个服务器配置

        Args:
            server_id: 服务器 ID
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            服务器配置或 None
        """
        collection = await self._get_collection()

        try:
            object_id = ObjectId(server_id)
        except Exception:
            return None

        doc = await collection.find_one({"_id": object_id})

        if not doc:
            return None

        # 权限检查
        if not is_admin and doc.get("is_system"):
            # 系统级配置所有用户可读
            pass
        elif not is_admin and doc.get("owner_id") != user_id:
            return None

        return MCPServerConfigResponse.from_db(doc)

    async def list_servers(
        self,
        user_id: str,
        is_admin: bool = False
    ) -> Dict[str, List[MCPServerConfigResponse]]:
        """
        列出服务器配置

        Args:
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            {"system": [...], "user": [...]}
        """
        collection = await self._get_collection()

        # 查询所有服务器（包括禁用的），由前端来决定如何显示
        query = {}

        if is_admin:
            # 管理员查看所有服务器
            cursor = collection.find(query).sort("created_at", -1)
            all_servers = [MCPServerConfigResponse.from_db(doc) async for doc in cursor]
            return {
                "system": [s for s in all_servers if s.is_system],
                "user": [s for s in all_servers if not s.is_system],
            }
        else:
            # 普通用户查看系统级服务器（只读）和自己的服务器
            system_servers = []
            user_servers = []

            # 系统级服务器
            system_cursor = collection.find({
                **query,
                "is_system": True,
            }).sort("created_at", -1)
            system_servers = [MCPServerConfigResponse.from_db(doc) async for doc in system_cursor]

            # 用户自己的服务器
            user_cursor = collection.find({
                **query,
                "is_system": False,
                "owner_id": user_id,
            }).sort("created_at", -1)
            user_servers = [MCPServerConfigResponse.from_db(doc) async for doc in user_cursor]

            return {
                "system": system_servers,
                "user": user_servers,
            }

    async def update_server(
        self,
        server_id: str,
        user_id: str,
        request: MCPServerConfigUpdate,
        is_admin: bool = False
    ) -> Optional[MCPServerConfigResponse]:
        """
        更新服务器配置

        Args:
            server_id: 服务器 ID
            user_id: 用户 ID
            request: 更新请求
            is_admin: 是否为管理员

        Returns:
            更新后的服务器配置或 None
        """
        collection = await self._get_collection()

        try:
            object_id = ObjectId(server_id)
        except Exception:
            return None

        # 获取原配置
        doc = await collection.find_one({"_id": object_id})
        if not doc:
            return None

        # 权限检查（系统级配置只有管理员可以修改）
        if doc.get("is_system") and not is_admin:
            return None

        if not doc.get("is_system") and doc.get("owner_id") != user_id:
            return None

        # 验证环境变量格式
        if request.env is not None:
            try:
                json.dumps(request.env)
            except (TypeError, ValueError) as e:
                raise ValueError(f"环境变量格式无效: {e}")

        # 构建更新数据
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.transport is not None:
            update_data["transport"] = request.transport.value
        if request.command is not None:
            update_data["command"] = request.command
        if request.args is not None:
            update_data["args"] = request.args
        if request.env is not None:
            update_data["env"] = request.env
        if request.url is not None:
            update_data["url"] = request.url
        if request.headers is not None:
            update_data["headers"] = request.headers
        if request.auth_type is not None:
            update_data["auth_type"] = request.auth_type.value
        if request.auth_token is not None:
            update_data["auth_token"] = request.auth_token
        if request.auto_approve is not None:
            update_data["auto_approve"] = request.auto_approve
        if request.enabled is not None:
            update_data["enabled"] = request.enabled

        update_data["updated_at"] = datetime.utcnow()

        # 执行更新
        await collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )

        # 获取更新后的配置
        updated_doc = await collection.find_one({"_id": object_id})

        logger.info(f"更新 MCP 服务器配置: server_id={server_id}, user={user_id}")

        return MCPServerConfigResponse.from_db(updated_doc)

    async def delete_server(
        self,
        server_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> bool:
        """
        删除服务器配置

        Args:
            server_id: 服务器 ID
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            是否删除成功
        """
        collection = await self._get_collection()

        try:
            object_id = ObjectId(server_id)
        except Exception:
            return False

        # 获取配置
        doc = await collection.find_one({"_id": object_id})
        if not doc:
            return False

        # 权限检查（系统级配置只有管理员可以删除）
        if doc.get("is_system") and not is_admin:
            return False

        if not doc.get("is_system") and doc.get("owner_id") != user_id:
            return False

        # 删除配置
        result = await collection.delete_one({"_id": object_id})

        logger.info(f"删除 MCP 服务器配置: server_id={server_id}, user={user_id}")

        return result.deleted_count > 0

    # ========================================================================
    # 连接测试
    # ========================================================================

    async def test_server_connection(
        self,
        server_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> ConnectionTestResponse:
        """
        测试 MCP 服务器连接

        Args:
            server_id: 服务器 ID
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            测试结果
        """
        from core.mcp.adapter.adapter import get_mcp_tools

        start_time = time.time()

        # 获取服务器配置
        server = await self.get_server(server_id, user_id, is_admin)
        if not server:
            return ConnectionTestResponse(
                success=False,
                message="服务器配置不存在",
            )

        # 构建连接配置
        try:
            connection_config = self._build_connection_config(server)
            logger.debug(f"开始测试 MCP 连接: server_id={server_id}, name={server.name}")

            # 测试连接
            tools = await get_mcp_tools(server.name, connection_config)

            # 在连接测试完成后计算延迟
            latency_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"连接测试完成: server_id={server_id}, latency={latency_ms}ms, tools={len(tools)}")

            # 更新状态为可用
            await self._update_server_status(
                server_id, MCPServerStatusEnum.AVAILABLE
            )

            logger.info(
                f"MCP 服务器连接测试成功: server_id={server_id}, "
                f"tools={len(tools)}, latency={latency_ms}ms"
            )

            return ConnectionTestResponse(
                success=True,
                message=f"连接成功，检测到 {len(tools)} 个工具",
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"连接测试失败: server_id={server_id}, latency={latency_ms}ms, error={str(e)}")

            # 更新状态
            await self._update_server_status(
                server_id, MCPServerStatusEnum.UNAVAILABLE
            )

            logger.error(
                f"MCP 服务器连接测试失败: server_id={server_id}, error={e}"
            )

            return ConnectionTestResponse(
                success=False,
                message=f"连接测试失败: {str(e)}",
                latency_ms=latency_ms,
            )

    async def get_server_tools(
        self,
        server_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取 MCP 服务器的工具列表

        Args:
            server_id: 服务器 ID
            user_id: 用户 ID
            is_admin: 是否为管理员

        Returns:
            工具列表
        """
        from core.mcp.adapter.adapter import get_mcp_tools

        # 获取服务器配置
        server = await self.get_server(server_id, user_id, is_admin)
        if not server:
            return []

        try:
            # 构建连接配置
            connection_config = self._build_connection_config(server)

            # 获取工具
            tools = await get_mcp_tools(server.name, connection_config)

            # 转换为字典格式
            tool_list = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description or "",
                }
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    if hasattr(tool.args_schema, 'model_json_schema'):
                        tool_dict["inputSchema"] = tool.args_schema.model_json_schema()
                    elif hasattr(tool.args_schema, 'schema'):
                        tool_dict["inputSchema"] = tool.args_schema.schema()

                tool_list.append(tool_dict)

            logger.info(
                f"获取 MCP 工具列表成功: server={server.name}, "
                f"count={len(tool_list)}"
            )

            return tool_list

        except Exception as e:
            logger.error(
                f"获取 MCP 工具列表失败: server={server.name}, error={e}",
                exc_info=True
            )
            return []

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _build_connection_config(self, server: MCPServerConfigResponse) -> Dict[str, Any]:
        """
        构建 MCP 连接配置

        Args:
            server: 服务器配置

        Returns:
            连接配置字典
        """
        # 获取认证头
        headers = build_auth_headers(
            headers=server.headers,
            auth_type=server.auth_type.value,
            auth_token=server.auth_token,
        )

        transport = map_transport_mode(server.transport.value)

        # 根据传输模式构建配置
        if transport == "stdio":
            from core.mcp.adapter.adapter import build_stdio_connection
            return build_stdio_connection(
                command=server.command,
                args=server.args,
                env=server.env,
            )
        elif transport == "sse":
            from core.mcp.adapter.adapter import build_sse_connection
            return build_sse_connection(
                url=server.url,
                headers=headers,
            )
        elif transport == "streamable_http":
            from core.mcp.adapter.adapter import build_streamable_http_connection
            return build_streamable_http_connection(
                url=server.url,
                headers=headers,
            )
        elif transport == "websocket":
            from core.mcp.adapter.adapter import build_websocket_connection
            return build_websocket_connection(
                url=server.url,
            )
        else:
            raise ValueError(f"不支持的传输模式: {transport}")

    async def _check_server_status_after_create(self, server_id: str) -> None:
        """
        创建后自动检测服务器状态（后台任务）

        这个方法会在创建服务器后异步调用，自动检测服务器是否可用。
        """
        try:
            # 使用系统用户进行测试
            result = await self.test_server_connection(
                server_id=server_id,
                user_id="system",
                is_admin=True
            )
            logger.info(f"自动状态检测完成: server_id={server_id}, success={result.success}")
        except Exception as e:
            logger.error(f"自动状态检测失败: server_id={server_id}, error={e}")
            # 检测失败时，状态保持为UNKNOWN

    async def _update_server_status(
        self,
        server_id: str,
        status: MCPServerStatusEnum
    ) -> None:
        """更新服务器状态"""
        collection = await self._get_collection()

        try:
            object_id = ObjectId(server_id)
        except Exception:
            return

        await collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": status.value,
                    "last_check_at": datetime.utcnow(),
                }
            }
        )


# =============================================================================
# 全局服务实例
# =============================================================================

_mcp_service: Optional[MCPService] = None


def get_mcp_service() -> MCPService:
    """获取全局 MCP 服务实例"""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = MCPService()
    return _mcp_service
