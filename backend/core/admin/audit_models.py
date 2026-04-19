"""
审计日志模型

扩展审计日志的范围，包含所有敏感操作。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class AuditLogCreate(BaseModel):
    """创建审计日志请求"""

    user_id: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogResponse(BaseModel):
    """审计日志响应"""

    id: str
    user_id: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime

    @classmethod
    def from_db(cls, data: Dict[str, Any]) -> "AuditLogResponse":
        """从数据库数据创建响应对象"""
        return cls(
            id=str(data.pop("_id")),
            user_id=str(data.pop("user_id")),
            action=data.pop("action"),
            resource_type=data.pop("resource_type"),
            resource_id=data.pop("resource_id") if "resource_id" in data else None,
            details=data.pop("details"),
            ip_address=data.pop("ip_address") if "ip_address" in data else None,
            created_at=data.pop("created_at"),
        )


# 审计操作类型枚举
AUDIT_ACTIONS = {
    # 用户管理（已存在）
    "user_create": "创建用户",
    "user_delete": "删除用户",
    "user_approve": "审核通过用户",
    "user_reject": "审核拒绝用户",
    "user_disable": "禁用用户",
    "user_enable": "启用用户",
    "user_login": "用户登录",
    "user_logout": "用户登出",
    "password_reset": "密码重置",
    "role_change": "角色变更",
    # AI 模型配置（新增）
    "ai_model_create": "创建 AI 模型",
    "ai_model_update": "更新 AI 模型",
    "ai_model_delete": "删除 AI 模型",
    "ai_model_access": "访问 AI 模型配置",
    "ai_model_test": "测试 AI 模型连接",
    # MCP 服务器配置（新增）
    "mcp_server_create": "创建 MCP 服务器",
    "mcp_server_update": "更新 MCP 服务器",
    "mcp_server_delete": "删除 MCP 服务器",
    "mcp_server_test": "测试 MCP 服务器连接",
    # 智能体配置（新增）
    "agent_config_update": "更新智能体配置",
    "agent_config_import": "导入智能体配置",
    "agent_config_export": "导出智能体配置",
    # 用户配置（新增）
    "settings_import": "导入用户配置",
    "settings_export": "导出用户配置",
    "settings_update": "更新用户配置",
    # 任务管理（新增）
    "batch_task_create": "创建批量任务",
    "task_quota_exceeded": "任务配额超限",
    "task_cancel": "取消任务",
    "task_retry": "重试任务",
    # 系统配置（新增）
    "system_config_update": "更新系统配置",
    "encryption_key_change": "更改加密密钥",
}
