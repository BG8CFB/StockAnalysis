# API 接口文档

本文档详细描述了 StockAnalysis 项目的所有 API 接口，包括请求格式、返回格式和权限要求。

> **维护规则**: 当项目中新增、删除或修改 API 接口时，必须同步更新本文档，确保文档与实际代码一致。

---

## 目录

- [1. 系统与认证](#1-系统与认证)
- [2. 管理员接口](#2-管理员接口-adminsuper_admin)
- [3. AI 模型管理](#3-ai-模型管理)
- [4. TradingAgents 任务管理](#4-tradingagents-任务管理)
- [5. TradingAgents 报告管理](#5-tradingagents-报告管理)
- [6. TradingAgents 智能体配置](#6-tradingagents-智能体配置)
- [7. TradingAgents 分析设置](#7-tradingagents-分析设置)
- [8. TradingAgents 管理员接口](#8-tradingagents-管理员接口-adminsuper_admin)
- [9. MCP 模块](#9-mcp-模块)
- [10. WebSocket 接口](#10-websocket-接口)

---

## 通用说明

### 请求头

所有需要认证的请求都需要携带 Token：

```
Authorization: Bearer {access_token}
```

### 通用响应格式

**成功响应**：
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

**错误响应**：
```json
{
  "success": false,
  "error": "错误类型",
  "message": "错误描述",
  "details": { ... }
}
```

---

## 1. 系统与认证

### 1.1 系统状态检查

**请求**：
```
GET /api/system/status
```

**返回**：
```json
{
  "initialized": true,
  "version": "0.1.0",
  "status": "healthy"
}
```

### 1.2 系统初始化（仅首次可用）

**请求**：
```
POST /api/system/initialize
```

**请求体**：
```json
{
  "username": "admin",
  "password": "admin123",
  "email": "admin@example.com"
}
```

**返回**：
```json
{
  "success": true,
  "message": "系统初始化成功"
}
```

### 1.3 生成图形验证码

**请求**：
```
POST /api/users/captcha/generate
```

**返回**：
```json
{
  "success": true,
  "data": {
    "captcha_id": "uuid",
    "image": "base64_image_data"
  }
}
```

### 1.4 检查是否需要验证码

**请求**：
```
GET /api/users/captcha/required
```

**返回**：
```json
{
  "required": true
}
```

### 1.5 用户注册

**请求**：
```
POST /api/users/register
```

**请求体**：
```json
{
  "username": "johndoe",
  "password": "password123",
  "email": "john@example.com",
  "captcha_id": "uuid",
  "captcha_text": "验证码"
}
```

**返回**：
```json
{
  "success": true,
  "message": "注册成功，请等待管理员审核"
}
```

### 1.6 用户登录

**请求**：
```
POST /api/users/login
```

**请求体**：
```json
{
  "username": "johndoe",
  "password": "password123"
}
```

**返回**：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "user_id",
    "username": "johndoe",
    "email": "john@example.com",
    "role": "USER"
  }
}
```

### 1.7 用户登出

**请求**：
```
POST /api/users/logout
```

**返回**：
```json
{
  "success": true,
  "message": "登出成功"
}
```

### 1.8 刷新令牌

**请求**：
```
POST /api/users/refresh-token
```

**请求体**：
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**返回**：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### 1.9 获取当前用户信息

**请求**：
```
GET /api/users/me
```

**返回**：
```json
{
  "id": "user_id",
  "username": "johndoe",
  "email": "john@example.com",
  "role": "USER",
  "status": "ACTIVE"
}
```

### 1.10 更新当前用户信息

**请求**：
```
PUT /api/users/me
```

**请求体**：
```json
{
  "email": "newemail@example.com",
  "password": "newpassword123"
}
```

**返回**：
```json
{
  "success": true,
  "message": "用户信息更新成功"
}
```

---

## 2. 管理员接口 (ADMIN/SUPER_ADMIN)

### 2.1 用户列表

**请求**：
```
GET /api/admin/users?page=1&page_size=20&status=ACTIVE&role=USER
```

**查询参数**：
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20）
- `status`: 用户状态筛选
- `role`: 角色筛选

**返回**：
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "users": [
    {
      "id": "user_id",
      "username": "johndoe",
      "email": "john@example.com",
      "role": "USER",
      "status": "ACTIVE",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 2.2 创建用户

**请求**：
```
POST /api/admin/users
```

**请求体**：
```json
{
  "username": "newuser",
  "password": "password123",
  "email": "newuser@example.com",
  "role": "USER"
}
```

**返回**：
```json
{
  "success": true,
  "message": "用户创建成功"
}
```

### 2.3 更新用户

**请求**：
```
PUT /api/admin/users/{id}
```

**请求体**：
```json
{
  "email": "updated@example.com",
  "role": "ADMIN"
}
```

### 2.4 删除用户

**请求**：
```
DELETE /api/admin/users/{id}
```

### 2.5 审核通过

**请求**：
```
PUT /api/admin/users/{id}/approve
```

### 2.6 审核拒绝

**请求**：
```
PUT /api/admin/users/{id}/reject
```

### 2.7 禁用用户

**请求**：
```
PUT /api/admin/users/{id}/disable
```

### 2.8 启用用户

**请求**：
```
PUT /api/admin/users/{id}/enable
```

### 2.9 修改用户角色（SUPER_ADMIN 专用）

**请求**：
```
PUT /api/admin/users/{id}/role
```

**请求体**：
```json
{
  "role": "ADMIN"
}
```

### 2.10 触发用户密码重置

**请求**：
```
POST /api/admin/users/request-reset
```

**请求体**：
```json
{
  "user_id": "user_id"
}
```

### 2.11 查看审计日志

**请求**：
```
GET /api/admin/audit-logs?page=1&page_size=20
```

**返回**：
```json
{
  "total": 1000,
  "logs": [
    {
      "id": "log_id",
      "user_id": "user_id",
      "username": "johndoe",
      "action": "user_login",
      "details": { ... },
      "ip_address": "192.168.1.1",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

## 3. AI 模型管理

### 3.1 获取模型列表

**请求**：
```
GET /api/ai/models
```

**返回**：
```json
{
  "models": [
    {
      "id": "model_id",
      "name": "GPT-4",
      "provider": "openai",
      "api_base": "https://api.openai.com/v1",
      "model_name": "gpt-4",
      "is_default": true,
      "enabled": true
    }
  ]
}
```

### 3.2 创建模型

**请求**：
```
POST /api/ai/models
```

**请求体**：
```json
{
  "name": "Claude 3.5",
  "provider": "anthropic",
  "api_base": "https://api.anthropic.com/v1",
  "api_key": "sk-ant-...",
  "model_name": "claude-3-5-sonnet-20241022",
  "is_default": false
}
```

### 3.3 获取模型详情

**请求**：
```
GET /api/ai/models/{id}
```

**返回**：
```json
{
  "id": "model_id",
  "name": "GPT-4",
  "provider": "openai",
  "api_base": "https://api.openai.com/v1",
  "model_name": "gpt-4",
  "is_default": true,
  "enabled": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 3.4 更新模型

**请求**：
```
PUT /api/ai/models/{id}
```

**请求体**：
```json
{
  "name": "GPT-4 Turbo",
  "api_key": "new_api_key"
}
```

### 3.5 删除模型

**请求**：
```
DELETE /api/ai/models/{id}
```

### 3.6 测试模型连接

**请求**：
```
POST /api/ai/models/{id}/test
```

**返回**：
```json
{
  "success": true,
  "message": "连接成功",
  "latency_ms": 150
}
```

### 3.7 设置为默认模型

**请求**：
```
PUT /api/ai/models/{id}/default
```

---

## 4. TradingAgents 任务管理

### 4.1 创建分析任务（支持单股和批量）

**请求**：
```
POST /api/trading-agents/tasks
```

**请求体**：
```json
{
  "stock_codes": ["000001", "000002"],
  "market": "a_share",
  "trade_date": "2024-01-01",
  "data_collection_model": "model_id_1",
  "debate_model": "model_id_2",
  "stages": {
    "stage1": {
      "enabled": true,
      "selected_agents": ["technical_analyst", "fundamental_analyst"]
    },
    "stage2": {
      "enabled": true,
      "debate": {
        "rounds": 3
      }
    },
    "stage3": {
      "enabled": true
    },
    "stage4": {
      "enabled": true
    }
  }
}
```

**字段说明**：
- `stock_codes`: 股票代码列表（1-50个）
- `market`: 市场类型（a_share, hong_kong, us）
- `trade_date`: 交易日期
- `data_collection_model`: 数据收集阶段模型ID（可选）
- `debate_model`: 辩论阶段模型ID（可选）
- `stages`: 阶段配置

**返回**：
```json
{
  "task_id": "task_id_1",
  "batch_id": null,
  "stock_codes": ["000001"],
  "total_count": 1,
  "message": "已创建单股分析任务，任务ID: task_id_1"
}
```

或批量任务：
```json
{
  "task_id": null,
  "batch_id": "batch_id_1",
  "stock_codes": ["000001", "000002"],
  "total_count": 2,
  "message": "已创建批量分析任务，批量ID: batch_id_1，共 2 个股票"
}
```

### 4.2 列出任务

**请求**：
```
GET /api/trading-agents/tasks?page=1&page_size=20&status=running
```

**查询参数**：
- `page`: 页码
- `page_size`: 每页数量
- `status`: 状态筛选（pending, running, completed, failed, cancelled）
- `stock_code`: 股票代码筛选

**返回**：
```json
{
  "total": 50,
  "page": 1,
  "page_size": 20,
  "tasks": [
    {
      "id": "task_id",
      "user_id": "user_id",
      "stock_code": "000001",
      "trade_date": "2024-01-01",
      "status": "running",
      "current_phase": 2,
      "current_agent": "debate_manager",
      "progress": 45.5,
      "reports": {
        "phase1": "第一阶段报告..."
      },
      "final_recommendation": null,
      "token_usage": {
        "total": 1000,
        "input": 600,
        "output": 400
      },
      "created_at": "2024-01-01T00:00:00Z",
      "started_at": "2024-01-01T00:01:00Z"
    }
  ]
}
```

### 4.3 获取任务详情

**请求**：
```
GET /api/trading-agents/tasks/{id}
```

**返回**：
```json
{
  "id": "task_id",
  "user_id": "user_id",
  "stock_code": "000001",
  "trade_date": "2024-01-01",
  "status": "completed",
  "current_phase": 4,
  "current_agent": null,
  "progress": 100.0,
  "reports": {
    "phase1": "第一阶段报告内容...",
    "phase2": "第二阶段报告内容...",
    "phase3": "第三阶段报告内容...",
    "final": "最终投资建议..."
  },
  "final_recommendation": "买入",
  "buy_price": 10.5,
  "sell_price": 12.0,
  "token_usage": {
    "total": 5000,
    "input": 3000,
    "output": 2000,
    "by_phase": {
      "phase1": 1500,
      "phase2": 2000,
      "phase3": 1000,
      "phase4": 500
    }
  },
  "created_at": "2024-01-01T00:00:00Z",
  "started_at": "2024-01-01T00:01:00Z",
  "completed_at": "2024-01-01T00:05:00Z"
}
```

### 4.4 取消/停止任务

**请求**：
```
POST /api/trading-agents/tasks/{id}/cancel
```

**返回**：
```json
{
  "success": true,
  "message": "任务已取消"
}
```

### 4.5 SSE 实时报告流

**请求**：
```
GET /api/trading-agents/tasks/{id}/stream
```

**返回**: Server-Sent Events (SSE) 流

### 4.6 删除任务

**请求**：
```
DELETE /api/trading-agents/tasks/{id}
```

### 4.7 重试失败任务

**请求**：
```
POST /api/trading-agents/tasks/{id}/retry
```

### 4.8 获取队列位置

**请求**：
```
GET /api/trading-agents/tasks/{id}/queue-position
```

**返回**：
```json
{
  "position": 3,
  "estimated_wait_minutes": 5
}
```

---

## 5. TradingAgents 报告管理

### 5.1 列出报告

**请求**：
```
GET /api/trading-agents/reports?page=1&page_size=20
```

**返回**：
```json
{
  "total": 100,
  "reports": [
    {
      "id": "report_id",
      "task_id": "task_id",
      "stock_code": "000001",
      "trade_date": "2024-01-01",
      "report_type": "final",
      "recommendation": "买入",
      "buy_price": 10.5,
      "sell_price": 12.0,
      "token_usage": {
        "total": 5000
      },
      "created_at": "2024-01-01T00:05:00Z"
    }
  ]
}
```

### 5.2 获取报告统计摘要

**请求**：
```
GET /api/trading-agents/reports/summary
```

**返回**：
```json
{
  "total_reports": 100,
  "buy_count": 45,
  "sell_count": 30,
  "hold_count": 25,
  "avg_buy_price": 10.5,
  "avg_sell_price": 12.0,
  "recommendation_distribution": {
    "买入": 45,
    "卖出": 30,
    "持有": 25
  },
  "total_token_usage": 500000
}
```

### 5.3 获取报告详情

**请求**：
```
GET /api/trading-agents/reports/{id}
```

**返回**：
```json
{
  "id": "report_id",
  "task_id": "task_id",
  "stock_code": "000001",
  "trade_date": "2024-01-01",
  "report_type": "final",
  "report_content": "完整的报告内容...",
  "recommendation": "买入",
  "buy_price": 10.5,
  "sell_price": 12.0,
  "token_usage": {
    "total": 5000,
    "input": 3000,
    "output": 2000
  },
  "created_at": "2024-01-01T00:05:00Z"
}
```

### 5.4 删除报告

**请求**：
```
DELETE /api/trading-agents/reports/{id}
```

---

## 6. TradingAgents 智能体配置

### 6.1 获取智能体配置

**请求**：
```
GET /api/trading-agents/agent-config
```

**返回**：
```json
{
  "id": "config_id",
  "user_id": "user_id",
  "is_customized": false,
  "phase1": {
    "enabled": true,
    "max_rounds": 1,
    "max_concurrency": 3,
    "agents": [
      {
        "slug": "technical_analyst",
        "name": "技术分析师",
        "role_definition": "你是一位专业的技术分析师...",
        "when_to_use": "用于技术面分析",
        "enabled_mcp_servers": ["finance_mcp"],
        "enabled_local_tools": [],
        "enabled": true
      }
    ]
  },
  "phase2": {
    "enabled": true,
    "max_rounds": 3,
    "agents": [
      {
        "slug": "bull_debater",
        "name": "看多辩手",
        "role_definition": "你是一位看多的辩论者...",
        "when_to_use": "用于多空辩论"
      }
    ]
  },
  "phase3": { ... },
  "phase4": { ... },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 6.2 更新智能体配置

**请求**：
```
PUT /api/trading-agents/agent-config
```

**请求体**：
```json
{
  "phase1": {
    "enabled": true,
    "max_rounds": 1,
    "max_concurrency": 3,
    "agents": [ ... ]
  },
  "phase2": { ... },
  "phase3": { ... },
  "phase4": { ... }
}
```

### 6.3 重置为默认配置

**请求**：
```
POST /api/trading-agents/agent-config/reset
```

### 6.4 导出配置

**请求**：
```
POST /api/trading-agents/agent-config/export
```

**返回**：
```json
{
  "config": { ... },
  "exported_at": "2024-01-01T00:00:00Z"
}
```

### 6.5 导入配置

**请求**：
```
POST /api/trading-agents/agent-config/import
```

**请求体**：
```json
{
  "config": { ... }
}
```

---

## 7. TradingAgents 分析设置

### 7.1 获取分析设置

**请求**：
```
GET /api/trading-agents/settings
```

**返回**：
```json
{
  "id": "settings_id",
  "user_id": "user_id",
  "settings": {
    "data_collection_model_id": "model_id_1",
    "debate_model_id": "model_id_2",
    "default_debate_rounds": 3,
    "max_debate_rounds": 5,
    "phase_timeout_minutes": 30,
    "agent_timeout_minutes": 10,
    "tool_timeout_seconds": 30,
    "task_expiry_hours": 24,
    "archive_days": 30,
    "enable_loop_detection": true,
    "enable_progress_events": true
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 7.2 更新分析设置

**请求**：
```
PUT /api/trading-agents/settings
```

**请求体**：
```json
{
  "data_collection_model_id": "new_model_id",
  "debate_rounds": 5,
  "phase_timeout_minutes": 45
}
```

---

## 8. TradingAgents 管理员接口 (ADMIN/SUPER_ADMIN)

### 8.1 获取公共智能体配置

**请求**：
```
GET /api/trading-agents/agent-config/public
```

### 8.2 更新公共智能体配置

**请求**：
```
PUT /api/trading-agents/agent-config/public
```

### 8.3 获取所有系统模型

**请求**：
```
GET /api/trading-agents/admin/models
```

**返回**：
```json
{
  "models": [
    {
      "id": "model_id",
      "name": "GPT-4",
      "user_id": "user_id",
      "is_default": false
    }
  ]
}
```

### 8.4 创建系统模型

**请求**：
```
POST /api/trading-agents/admin/models
```

**请求体**：
```json
{
  "name": "Claude 3.5",
  "provider": "anthropic",
  "api_base": "https://api.anthropic.com/v1",
  "api_key": "sk-ant-...",
  "model_name": "claude-3-5-sonnet-20241022"
}
```

### 8.5 更新系统模型

**请求**：
```
PUT /api/trading-agents/admin/models/{id}
```

### 8.6 删除系统模型

**请求**：
```
DELETE /api/trading-agents/admin/models/{id}
```

### 8.7 获取所有任务（跨用户）

**请求**：
```
GET /api/trading-agents/admin/all-tasks?page=1&page_size=20
```

### 8.8 删除任意任务

**请求**：
```
DELETE /api/trading-agents/admin/all-tasks/{id}
```

### 8.9 取消/停止任意任务

**请求**：
```
POST /api/trading-agents/admin/all-tasks/{id}/cancel
```

---

## 9. MCP 模块

### 9.1 列出 MCP 服务器

**请求**：
```
GET /api/mcp/servers
```

**返回**：
```json
{
  "servers": [
    {
      "id": "server_id",
      "name": "FinanceMCP",
      "transport": "streamable_http",
      "url": "http://localhost:3000/mcp",
      "status": "available",
      "is_system": true,
      "enabled": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 9.2 创建 MCP 服务器

**请求**：
```
POST /api/mcp/servers
```

**请求体（stdio 模式）**：
```json
{
  "name": "LocalMCP",
  "transport": "stdio",
  "command": "python",
  "args": ["-m", "mcp_server"],
  "env": {
    "API_KEY": "xxx"
  },
  "enabled": true
}
```

**请求体（HTTP 模式）**：
```json
{
  "name": "RemoteMCP",
  "transport": "streamable_http",
  "url": "http://example.com/mcp",
  "headers": {
    "Authorization": "Bearer xxx"
  },
  "enabled": true
}
```

### 9.3 获取 MCP 服务器详情

**请求**：
```
GET /api/mcp/servers/{id}
```

**返回**：
```json
{
  "id": "server_id",
  "name": "FinanceMCP",
  "transport": "streamable_http",
  "url": "http://localhost:3000/mcp",
  "headers": {},
  "status": "available",
  "is_system": true,
  "enabled": true,
  "last_check_at": "2024-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 9.4 更新 MCP 服务器

**请求**：
```
PUT /api/mcp/servers/{id}
```

**请求体**：
```json
{
  "url": "http://new-url.com/mcp",
  "enabled": false
}
```

### 9.5 删除 MCP 服务器

**请求**：
```
DELETE /api/mcp/servers/{id}
```

### 9.6 测试 MCP 服务器连接

**请求**：
```
POST /api/mcp/servers/{id}/test
```

**返回**：
```json
{
  "success": true,
  "message": "连接成功",
  "latency_ms": 50,
  "details": {
    "tools_count": 10
  }
}
```

### 9.7 获取 MCP 服务器工具列表

**请求**：
```
GET /api/mcp/servers/{id}/tools
```

**返回**：
```json
{
  "tools": [
    {
      "name": "get_stock_price",
      "description": "获取股票实时价格",
      "server_id": "server_id",
      "server_name": "FinanceMCP"
    }
  ]
}
```

### 9.8 获取 MCP 设置

**请求**：
```
GET /api/mcp/settings
```

**返回**：
```json
{
  "connection_timeout": 30,
  "max_retries": 3,
  "health_check_interval": 300
}
```

### 9.9 更新 MCP 设置

**请求**：
```
PUT /api/mcp/settings
```

**请求体**：
```json
{
  "connection_timeout": 60,
  "max_retries": 5
}
```

### 9.10 重置为默认设置

**请求**：
```
POST /api/mcp/settings/reset
```

### 9.11 获取默认配置

**请求**：
```
GET /api/mcp/config/default
```

---

## 10. WebSocket 接口

### 10.1 实时任务进度推送

**连接**：
```
WS /api/trading-agents/ws/{task_id}?token={access_token}
```

**事件格式**：
```json
{
  "event_type": "phase_started",
  "task_id": "task_id",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "phase": 1,
    "phase_name": "分析师团队"
  }
}
```

**事件类型**：
- `task_started`: 任务开始
- `phase_started`: 阶段开始
- `phase_completed`: 阶段完成
- `agent_started`: 智能体开始
- `agent_completed`: 智能体完成
- `tool_called`: 工具调用
- `tool_result`: 工具返回
- `report_generated`: 报告生成
- `task_completed`: 任务完成
- `task_failed`: 任务失败
- `task_cancelled`: 任务取消

---

## 附录

### 任务状态枚举

| 状态 | 代码 | 说明 |
|------|------|------|
| 待执行 | `pending` | 任务已创建，等待执行 |
| 执行中 | `running` | 任务正在执行 |
| 已完成 | `completed` | 任务执行完成 |
| 失败 | `failed` | 任务执行失败 |
| 已取消 | `cancelled` | 任务被用户取消 |
| 已停止 | `stopped` | 任务被人工干预停止 |
| 已过期 | `expired` | 任务超过 24 小时未完成 |

### 推荐结果枚举

| 结果 | 说明 |
|------|------|
| 买入 | 建议买入 |
| 卖出 | 建议卖出 |
| 持有 | 建议持有 |

### 风险等级枚举

| 等级 | 说明 |
|------|------|
| 高 | 高风险 |
| 中 | 中等风险 |
| 低 | 低风险 |

### MCP 传输模式

| 模式 | 说明 | 推荐场景 |
|------|------|----------|
| `stdio` | 标准输入输出 | 本地进程 |
| `streamable_http` | Streamable HTTP | 远程服务（推荐） |
| `websocket` | WebSocket | 实时通信 |
| `sse` | Server-Sent Events | 已废弃 |
