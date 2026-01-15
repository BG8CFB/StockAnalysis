"""
MCP 工具过滤器

根据智能体配置过滤和管理可用的 MCP 工具。

**版本**: v1.0
**最后更新**: 2026-01-15
"""

import logging
from typing import List, Dict, Any, Set

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class MCPToolFilter:
    """
    MCP 工具过滤器

    根据智能体配置中的白名单和黑名单，过滤可用的 MCP 工具。
    """

    def __init__(self, agent_config: Dict[str, Any]):
        """
        初始化工具过滤器

        Args:
            agent_config: 智能体配置（包含 mcp_servers 和 local_tools 配置）
        """
        self.config = agent_config
        self.mcp_servers = agent_config.get("mcp_servers", [])
        self.local_tools = agent_config.get("local_tools", [])

    def filter_tools(
        self,
        available_tools: List[BaseTool]
    ) -> List[BaseTool]:
        """
        根据配置过滤工具列表

        Args:
            available_tools: 所有可用的工具列表

        Returns:
            过滤后的工具列表
        """
        if not self.mcp_servers and not self.local_tools:
            logger.debug("[MCP Tool Filter] 没有配置工具限制，返回所有工具")
            return available_tools

        filtered_tools = []
        allowed_tools: Set[str] = set()

        # 收集所有允许的工具名称
        allowed_tools.update(self.mcp_servers)
        allowed_tools.update(self.local_tools)

        # 过滤工具
        for tool in available_tools:
            tool_name = tool.name

            # 检查工具是否在允许列表中
            if self._is_tool_allowed(tool_name, allowed_tools):
                filtered_tools.append(tool)
                logger.debug(f"[MCP Tool Filter] 允许工具: {tool_name}")
            else:
                logger.debug(f"[MCP Tool Filter] 过滤工具: {tool_name}")

        logger.info(
            f"[MCP Tool Filter] 从 {len(available_tools)} 个工具中过滤出 {len(filtered_tools)} 个"
        )
        return filtered_tools

    def _is_tool_allowed(
        self,
        tool_name: str,
        allowed_tools: Set[str]
    ) -> bool:
        """
        检查工具是否被允许使用

        Args:
            tool_name: 工具名称
            allowed_tools: 允许的工具名称集合

        Returns:
            是否允许使用该工具
        """
        # 如果没有配置限制，允许所有工具
        if not allowed_tools:
            return True

        # 检查精确匹配
        if tool_name in allowed_tools:
            return True

        # 检查前缀匹配（例如 "mcp__server1__*" 匹配所有来自 server1 的工具）
        for allowed in allowed_tools:
            if allowed.endswith("*"):
                prefix = allowed[:-1]
                if tool_name.startswith(prefix):
                    return True

        return False

    def get_tool_summary(self, tools: List[BaseTool]) -> Dict[str, Any]:
        """
        获取工具列表摘要信息

        Args:
            tools: 工具列表

        Returns:
            工具摘要信息
        """
        summary = {
            "total": len(tools),
            "by_server": {},
        }

        for tool in tools:
            # 从工具名称中提取服务器名称（假设格式为 mcp__server_name__tool_name）
            parts = tool.name.split("__")
            if len(parts) >= 2 and parts[0] == "mcp":
                server_name = parts[1]
                summary["by_server"][server_name] = (
                    summary["by_server"].get(server_name, 0) + 1
                )

        return summary
