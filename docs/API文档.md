# API 接口文档

本文档详细描述了 StockAnalysis 项目的所有 API 接口，包括请求格式、返回格式和权限要求。

> **维护规则**: 当项目中新增、删除或修改 API 接口时，必须同步更新本文档，确保文档与实际代码一致。

---

## 目录

- [1. 系统与认证](#1-系统与认证)
- [2. 管理员接口](#2-管理员接口-adminsuper_admin)
- [3. AI 模型管理](#3-ai-模型管理)
- [4. TradingAgents 模块 API](#4-tradingagents-模块-api)
- [5. MCP 模块](#5-mcp-模块)
- [6. WebSocket 接口](#6-websocket-接口)
- [7. 市场数据模块 API](#7-市场数据模块-api)

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
  "system": [
    {
      "id": "model_id",
      "name": "GPT-4",
      "platform_type": "preset",
      "platform_name": "openai",
      "api_base_url": "https://api.openai.com/v1",
      "model_id": "gpt-4",
      "masked_api_key": "sk-****xxxx",
      "max_concurrency": 40,
      "task_concurrency": 2,
      "batch_concurrency": 1,
      "timeout_seconds": 60,
      "temperature": 0.5,
      "enabled": true,
      "thinking_enabled": false,
      "thinking_mode": null,
      "custom_input_price": null,
      "custom_output_price": null,
      "custom_thinking_price": null,
      "is_system": true,
      "owner_id": null,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "user": [
    {
      "id": "model_id_2",
      "name": "GLM-4 Plus",
      "platform_type": "preset",
      "platform_name": "zhipu",
      "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
      "model_id": "glm-4-plus",
      "masked_api_key": "****xxxx.****",
      "max_concurrency": 40,
      "task_concurrency": 2,
      "batch_concurrency": 1,
      "timeout_seconds": 60,
      "temperature": 0.5,
      "enabled": true,
      "thinking_enabled": true,
      "thinking_mode": "preserved",
      "custom_input_price": 5.0,
      "custom_output_price": 15.0,
      "custom_thinking_price": 15.0,
      "is_system": false,
      "owner_id": "user_id",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**字段说明**：
- `system`: 系统模型列表（所有用户可见）
- `user`: 当前用户的个人模型列表
- `masked_api_key`: 脱敏后的 API Key
- `custom_input_price/custom_output_price/custom_thinking_price`: 自定义价格（null 表示使用内置价格）

### 3.2 创建模型

**请求**：
```
POST /api/ai/models
```

**请求体**：
```json
{
  "name": "Claude 3.5",
  "platform_type": "preset",
  "platform_name": "anthropic",
  "api_base_url": "https://api.anthropic.com/v1",
  "api_key": "sk-ant-...",
  "model_id": "claude-3-5-sonnet-20241022",
  "max_concurrency": 40,
  "task_concurrency": 2,
  "batch_concurrency": 1,
  "timeout_seconds": 60,
  "temperature": 0.5,
  "enabled": true,
  "thinking_enabled": true,
  "thinking_mode": "preserved",
  "custom_input_price": 3.0,
  "custom_output_price": 15.0,
  "custom_thinking_price": 15.0,
  "is_system": false
}
```

**字段说明**：
- `name`: 模型显示名称
- `platform_type`: 平台类型（preset=预设平台，custom=自定义）
- `platform_name`: 预设平台名称（platform_type=preset 时必填）
  - 可选值：openai, anthropic, azure_openai, baidu, alibaba, tencent, deepseek, moonshot, zhipu, zhipu_coding
- `api_base_url`: API 基础 URL
- `api_key`: API Key
- `model_id`: 模型 ID（如 gpt-4, glm-4-plus 等）
- `max_concurrency`: 最大并发数（1-200）
- `task_concurrency`: 单任务并发数（1-10）
- `batch_concurrency`: 批量任务并发数（1-50）
- `timeout_seconds`: 超时时间（秒，10-600）
- `temperature`: 温度参数（0.0-2.0）
- `enabled`: 是否启用
- `thinking_enabled`: 是否启用思考模式
- `thinking_mode`: 思考模式类型（preserved/clear_on_new/auto）
- `custom_input_price`: 自定义输入价格（元/百万tokens，留空使用内置价格）
- `custom_output_price`: 自定义输出价格（元/百万tokens，留空使用内置价格）
- `custom_thinking_price`: 自定义思考价格（元/百万tokens，留空使用内置价格）
- `is_system`: 是否为系统模型（仅管理员可创建系统模型）

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
  "platform_type": "preset",
  "platform_name": "openai",
  "api_base_url": "https://api.openai.com/v1",
  "model_id": "gpt-4",
  "masked_api_key": "sk-****xxxx",
  "max_concurrency": 40,
  "task_concurrency": 2,
  "batch_concurrency": 1,
  "timeout_seconds": 60,
  "temperature": 0.5,
  "enabled": true,
  "thinking_enabled": false,
  "thinking_mode": null,
  "custom_input_price": null,
  "custom_output_price": null,
  "custom_thinking_price": null,
  "is_system": false,
  "owner_id": "user_id",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
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
  "api_key": "new_api_key",
  "enabled": true,
  "thinking_enabled": true,
  "thinking_mode": "auto",
  "custom_input_price": 2.5,
  "custom_output_price": 10.0,
  "custom_thinking_price": null
}
```

**说明**：所有字段均为可选，仅更新提供的字段

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

## 4. TradingAgents 模块 API

> 📖 **详细文档**：
> - [TradingAgents API 接口文档](./TradingAgents/API接口文档.md) - TradingAgents 模块 API 完整文档，包含前后端映射、调用示例等详细说明

TradingAgents 模块包含以下主要功能区域的接口：

- **任务管理**：创建、查询、停止、删除分析任务（单股/批量）
- **报告管理**：查询任务生成的分析报告
- **智能体配置**：管理分析师团队、辩论团队等智能体的配置
- **分析设置**：管理分析流程的全局设置（如轮次、超时等）
- **管理员接口**：系统级模型管理、全局任务管理等

请参考 [TradingAgents API 接口文档](./TradingAgents/API接口文档.md) 获取完整的接口定义。

---

## 5. MCP 模块

### 5.1 列出 MCP 服务器

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

### 5.2 创建 MCP 服务器

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

### 5.3 获取 MCP 服务器详情

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

### 5.4 更新 MCP 服务器

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

### 5.5 删除 MCP 服务器

**请求**：
```
DELETE /api/mcp/servers/{id}
```

### 5.6 测试 MCP 服务器连接

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

### 5.7 获取 MCP 服务器工具列表

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

### 5.8 获取 MCP 设置

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

### 5.9 更新 MCP 设置

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

### 5.10 重置为默认设置

**请求**：
```
POST /api/mcp/settings/reset
```

### 5.11 获取默认配置

**请求**：
```
GET /api/mcp/config/default
```

---

## 6. WebSocket 接口

### 6.1 实时任务进度推送

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

## 7. 市场数据模块 API

> 📖 **详细文档**：
> - [Market Data API 接口文档](./market_data/API接口文档.md) - 数据同步、健康检查、状态监控、数据源配置等完整 API 文档

市场数据模块（`backend/core/market_data/`）提供以下主要功能：

- **数据同步**：同步股票列表、行情、财务数据等
- **健康检查**：检查数据源健康状态
- **状态监控**：获取状态汇总、历史事件、错误统计
- **数据源配置**：数据源配置管理

请参考 [Market Data API 接口文档](./market_data/API接口文档.md) 获取完整的接口定义。

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
