"""
MCP 服务器配置管理服务

提供 MCP 服务器的 CRUD 操作和连接测试功能。
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

from core.db.mongodb import mongodb
from modules.trading_agents.schemas import (
    MCPServerConfigCreate,
    MCPServerConfigUpdate,
    MCPServerConfigResponse,
    MCPServerStatusEnum,
    TransportModeEnum,
    AuthTypeEnum,
    ConnectionTestResponse,
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
        request: MCPServerConfigCreate
    ) -> MCPServerConfigResponse:
        """
        创建 MCP 服务器配置

        Args:
            user_id: 用户 ID
            request: 创建请求

        Returns:
            创建的服务器配置
        """
        collection = await self._get_collection()

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
            # http/sse 模式配置
            "url": request.url,
            "auth_type": request.auth_type.value if request.auth_type else AuthTypeEnum.NONE.value,
            "auth_token": request.auth_token,
            # 通用配置
            "auto_approve": request.auto_approve or [],
            "enabled": request.enabled,
            "is_system": request.is_system,
            "owner_id": None if request.is_system else user_id,
            # 状态
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

        # 查询所有启用的服务器
        query = {"enabled": True}

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

        # TODO: 检查是否有进行中的任务使用该服务器

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
        import time
        start_time = time.time()

        # 获取服务器配置
        server = await self.get_server(server_id, user_id, is_admin)
        if not server:
            return ConnectionTestResponse(
                success=False,
                message="服务器配置不存在",
            )

        try:
            # TODO: 实现实际的 MCP 连接测试
            # 根据 transport 类型选择不同的测试方式
            if server.transport == TransportModeEnum.STDIO:
                # 测试 stdio 模式
                pass
            elif server.transport == TransportModeEnum.HTTP:
                # 测试 HTTP 模式
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        server.url,
                        headers=self._get_auth_headers(server),
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            latency_ms = int((time.time() - start_time) * 1000)

                            # 更新状态
                            await self._update_server_status(
                                server_id, MCPServerStatusEnum.AVAILABLE
                            )

                            return ConnectionTestResponse(
                                success=True,
                                message="连接测试成功",
                                latency_ms=latency_ms,
                            )
            elif server.transport == TransportModeEnum.SSE:
                # 测试 SSE 模式
                pass

            latency_ms = int((time.time() - start_time) * 1000)

            # 更新状态
            await self._update_server_status(
                server_id, MCPServerStatusEnum.AVAILABLE
            )

            logger.info(f"MCP 服务器连接测试成功: server_id={server_id}")

            return ConnectionTestResponse(
                success=True,
                message="连接测试成功",
                latency_ms=latency_ms,
            )

        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)

            # 更新状态
            await self._update_server_status(
                server_id, MCPServerStatusEnum.UNAVAILABLE
            )

            logger.error(f"MCP 服务器连接测试超时: server_id={server_id}")

            return ConnectionTestResponse(
                success=False,
                message=f"连接测试超时（超过 10 秒）",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # 更新状态
            await self._update_server_status(
                server_id, MCPServerStatusEnum.UNAVAILABLE
            )

            logger.error(f"MCP 服务器连接测试失败: server_id={server_id}, error={e}")

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
        # 获取服务器配置
        server = await self.get_server(server_id, user_id, is_admin)
        if not server:
            return []

        # TODO: 实现实际的工具列表获取
        # 这需要连接到 MCP 服务器并调用 tools/list 方法

        return [
            {
                "name": "example_tool",
                "description": "示例工具",
                "inputSchema": {},
            }
        ]

    # ========================================================================
    # 辅助方法
    # ========================================================================

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

    def _get_auth_headers(self, server: MCPServerConfigResponse) -> Dict[str, str]:
        """获取认证头"""
        if server.auth_type == AuthTypeEnum.BEARER and server.auth_token:
            return {"Authorization": f"Bearer {server.auth_token}"}
        elif server.auth_type == AuthTypeEnum.BASIC and server.auth_token:
            # auth_token 格式: "username:password"
            import base64
            encoded = base64.b64encode(server.auth_token.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {}


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
