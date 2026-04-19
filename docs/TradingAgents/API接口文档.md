# TradingAgents API 接口文档

**版本**: v3.0 (LangChain create_agent 重构版)
**最后更新**: 2026-01-15
**状态**: 最新

---

## 目录

- [一、API 概述](#一api-概述)
- [二、与核心基础设施的集成](#二与核心基础设施的集成)
- [三、任务管理接口](#三任务管理接口)
- [四、智能体配置接口](#四智能体配置接口)
- [五、设置接口](#五设置接口)
- [六、管理员接口](#六管理员接口)
- [七、WebSocket 与 SSE](#七websocket-与-sse)
- [八、数据模型](#八数据模型)
- [九、错误码](#九错误码)
- [十、API 调用流程](#十api-调用流程)

---

## 一、API 概述

### 1.1 基础信息

| 属性 | 值 |
|------|-----|
| **Base URL** | `/api` |
| **内容类型** | `application/json` |
| **认证方式** | Bearer Token (JWT) |

### 1.2 接口分类

| 分类 | 路径前缀 | 权限要求 |
|------|----------|----------|
| 任务管理 | `/trading-agents/tasks` | 所有认证用户 |
| 智能体配置 | `/trading-agents/agent-config` | 所有认证用户 |
| 设置管理 | `/settings/trading-agents` | 所有认证用户 |
| 管理员接口 | `/admin/trading-agents` | ADMIN/SUPER_ADMIN |

**架构说明**：

TradingAgents 模块作为业务模块，依赖并复用以下两个核心基础设施模块：

| 模块 | 路径 | 调用方式 | 提供的能力 |
|------|------|----------|------------|
| **核心 AI 模块** | `backend/core/ai/` | 通过 `AIService` 统一服务调用 | LLM 调用、并发控制、Token 计数与定价、使用统计 |
| **MCP 模块** | `backend/core/mcp/` | 通过 `MCPConnectionPool` 连接池调用 | 工具连接获取、工具调用、连接复用、并发控制 |

**核心原则**：TradingAgents 不重复实现 AI 调用和工具调用的基础能力，全部复用核心模块提供的统一接口。

详细的集成说明请参考 [二、与核心基础设施的集成](#二与核心基础设施的集成)。

### 1.3 前端页面与 API 映射关系

```
前端页面                    后端 API                  前端文件位置
─────────────────────────────────────────────────────────────────
单股分析页面          →   POST /trading-agents/tasks       SingleAnalysisView.vue
                         (创建单个任务)

批量分析页面          →   POST /trading-agents/tasks       BatchAnalysisView.vue
                         (创建批量任务)

分析详情页面          →   GET  /trading-agents/tasks/{id}  AnalysisDetailView.vue
                     →   GET  /trading-agents/tasks/{id}/stream
                     →   WS   /trading-agents/ws/{user_id}

任务中心              →   GET  /trading-agents/tasks       TaskCenterView.vue
                     →   GET  /trading-agents/tasks/status-counts
                     →   POST /trading-agents/tasks/{id}/cancel
                     →   DELETE /trading-agents/tasks/{id}

智能体配置管理        →   GET  /trading-agents/agent-config          AgentConfigView.vue
                     →   PUT  /trading-agents/agent-config
                     →   POST /trading-agents/agent-config/reset

分析设置             →   GET  /settings/trading-agents     AnalysisSettingsView.vue
                     →   PUT  /settings/trading-agents

所有任务管理          →   GET /admin/trading-agents/tasks  AllTasksView.vue
```

**注意**：AI 模型管理 (`/ai/models`) 和 MCP 服务器管理 (`/mcp/servers`) 属于各自的基础设施模块，不在此文档范围。

### 1.4 通用响应格式

**成功响应**：
```json
{
  "success": true,
  "data": {...}
}
```

**错误响应**：
```json
{
  "detail": "错误描述信息"
}
```

---

## 二、与核心基础设施的集成

### 2.1 架构依赖关系

TradingAgents 作为业务模块，**不重复实现**以下基础能力，全部复用核心模块提供的服务：

| 能力域 | 核心模块 | 复用方式 | TradingAgents 获得的能力 |
|--------|----------|----------|--------------------------|
| **AI 调用** | `core/ai/` | 通过 `AIService` 统一服务 | LLM 调用、并发控制、Token 统计、成本计算 |
| **工具调用** | `core/mcp/` | 通过 `MCPConnectionPool` 连接池 | MCP 工具调用、连接复用、并发控制 |

### 2.2 AI 调用集成

TradingAgents 通过核心 AI 模块的 `AIService` 进行所有 LLM 调用。

**核心 AI 模块文件位置**：`backend/core/ai/service.py`

**调用方式**：

TradingAgents 智能体直接调用 `AIService.chat_completion()` 方法，传入以下参数：

| 参数 | 说明 | 用途 |
|------|------|------|
| `user_id` | 用户 ID | 用户隔离、配额控制 |
| `messages` | 消息列表 | 对话上下文 |
| `model_id` | 模型 ID | 指定使用的模型 |
| `tools` | 工具列表 | MCP 工具绑定 |
| `task_id` | 任务 ID | Token 使用统计关联 |
| `phase` | 阶段标识 | Phase 1-4 标记 |
| `agent_slug` | 智能体标识 | 具体智能体标记 |

**核心模块自动处理**：

1. **并发控制**：通过 `ConcurrencyManager` 自动管理模型并发槽位
2. **模型创建**：通过 `LangChainAdapter` 创建 ChatModel 实例（支持智谱/Claude/OpenAI/DeepSeek 等）
3. **Token 统计**：自动记录输入/输出 Token 数量
4. **成本计算**：通过 `PricingService` 自动计算调用成本
5. **使用记录**：通过 `UsageService` 自动记录到数据库

### 2.3 MCP 工具集成

TradingAgents 通过 MCP 模块的 `MCPConnectionPool` 调用外部工具。

**MCP 模块文件位置**：`backend/core/mcp/pool/pool.py`

**调用方式**：

TradingAgents 智能体通过以下步骤调用 MCP 工具：

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | `acquire_connection()` | 获取或创建 MCP 长连接（支持任务级复用） |
| 2 | `call_tool()` | 调用具体工具，传入工具名称和参数 |
| 3 | `release_connection()` | 释放连接（启动 10 秒延迟关闭） |

**核心模块自动处理**：

1. **连接复用**：同一任务内的多次调用复用同一连接
2. **并发控制**：通过用户级信号量（个人 100 并发，公共 10 并发）
3. **服务器管理**：支持动态注册/注销/禁用 MCP 服务器
4. **自动清理**：连接关闭后自动清理，信号量空闲后自动释放
5. **任务标记**：支持任务完成/失败/取消的标记方法

### 2.4 接口归属说明

为了避免职责混淆，以下接口归属各自的基础设施模块，不在 TradingAgents 文档范围：

| 功能 | 模块 | 路径 | 文档位置 |
|------|------|------|----------|
| AI 模型管理 | 核心 AI 模块 | `/ai/models` | `backend/core/ai/README.md` |
| MCP 服务器管理 | MCP 模块 | `/mcp/servers` | `docs/MCP/MCP模块设计方案.md` |
| 市场数据获取 | 市场数据模块 | `/market-data/*` | `docs/market_data/README.md` |

### 2.5 复用设计的好处

| 好处 | 说明 |
|------|------|
| **避免重复造轮子** | AI 调用、工具调用的基础能力只需实现一次 |
| **统一维护** | 核心能力升级时，所有业务模块自动受益 |
| **数据一致性** | Token 统计、成本计算使用同一套逻辑 |
| **并发控制统一** | 全局统一的并发限制，避免资源冲突 |
| **配置统一** | 模型配置、MCP 配置统一管理，用户只需配置一次 |

---

## 三、任务管理接口

### 3.1 创建任务

**接口**：`POST /api/trading-agents/tasks`

**描述**：统一任务创建接口，支持单股和批量分析

**前端调用**：
- **页面**: 单股分析页面 (`SingleAnalysisView.vue`)、批量分析页面 (`BatchAnalysisView.vue`)
- **方法**: `createTasks(params)`
- **API 文件**: `frontend/src/modules/trading_agents/api.ts`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `stock_codes` | string[] | 是 | 股票代码列表（1-50 个） |
| `market` | string | 否 | 市场类型（默认：a_share） |
| `trade_date` | string | 否 | 交易日期（ISO 8601） |
| `stages` | object | 否 | 阶段配置 |
| `data_collection_model` | string | 否 | 数据收集模型 ID |
| `debate_model` | string | 否 | 辩论模型 ID |

**前端调用示例**：

```typescript
// frontend/src/modules/trading_agents/api.ts
createTasks({
  stock_codes: ["600000"],
  market: "a_share",
  trade_date: "2026-01-14",
  data_collection_model: "claude-sonnet-4-20250514",
  debate_model: "claude-haiku-4-20250514",
  stages: {
    stage1: { enabled: true, selected_agents: ["technical", "fundamental"] },
    stage2: { enabled: true, debate: { rounds: 2, concurrency: 1 } },
    stage3: { enabled: true, debate: { rounds: 2, concurrency: 1 } },
    stage4: { enabled: true }
  }
})
```

**响应示例（单股）**：

```json
{
  "type": "single",
  "task_id": "678901234567890123456789",
  "stock_code": "600000",
  "message": "任务创建成功"
}
```

**响应示例（批量）**：

```json
{
  "type": "batch",
  "batch_id": "678901234567890123456789",
  "stock_codes": ["600000", "600001"],
  "total_count": 2,
  "message": "批量任务创建成功"
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:53`

---

### 3.2 查询任务列表

**接口**：`GET /api/trading-agents/tasks`

**描述**：列出用户的分析任务，支持多条件筛选

**前端调用**：
- **页面**: 任务中心 (`TaskCenterView.vue`)、分析详情页 (`AnalysisDetailView.vue`)
- **方法**: `listTasks(params)`

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 否 | 状态过滤（pending/running/completed/failed/cancelled） |
| `stock_code` | string | 否 | 股票代码过滤（模糊匹配） |
| `recommendation` | string | 否 | 推荐结果过滤 |
| `risk_level` | string | 否 | 风险等级过滤 |
| `start_date` | string | 否 | 开始日期（ISO 8601） |
| `end_date` | string | 否 | 结束日期（ISO 8601） |
| `limit` | int | 否 | 返回数量限制（1-100，默认：50） |
| `offset` | int | 否 | 偏移量（默认：0） |

**前端调用示例**：

```typescript
// frontend/src/modules/trading_agents/api.ts
listTasks({
  status: 'completed',
  stock_code: '600000',
  recommendation: '买入',
  risk_level: '中',
  start_date: '2026-01-01',
  end_date: '2026-01-14',
  limit: 50,
  offset: 0
})
```

**响应示例**：

```json
{
  "tasks": [
    {
      "id": "678901234567890123456789",
      "stock_code": "600000",
      "stock_name": "浦发银行",
      "status": "completed",
      "recommendation": "BUY",
      "risk_level": "MEDIUM",
      "created_at": "2026-01-14T10:00:00Z",
      "completed_at": "2026-01-14T10:05:30Z"
    }
  ],
  "total": 1
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:224`

---

### 3.3 获取任务详情

**接口**：`GET /api/trading-agents/tasks/{task_id}`

**描述**：获取单个任务的详细信息

**前端调用**：
- **页面**: 分析详情页 (`AnalysisDetailView.vue`)
- **方法**: `getTask(taskId)`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 是 | 任务 ID |

**响应示例**：

```json
{
  "id": "678901234567890123456789",
  "user_id": "user123",
  "stock_code": "600000",
  "stock_name": "浦发银行",
  "status": "completed",
  "trade_date": "2026-01-14",
  "created_at": "2026-01-14T10:00:00Z",
  "started_at": "2026-01-14T10:00:05Z",
  "completed_at": "2026-01-14T10:05:30Z",
  "stages": {
    "phase1": {"enabled": true},
    "phase2": {"enabled": true},
    "phase3": {"enabled": true},
    "phase4": {"enabled": true}
  },
  "reports": {
    "final_report": "# 分析报告\n\n...",
    "analyst_reports": [...],
    "debate_turns": [...],
    "risk_assessments": [...]
  },
  "final_recommendation": "BUY",
  "risk_level": "MEDIUM",
  "buy_price": 10.50,
  "sell_price": 12.00,
  "token_usage": {
    "total_tokens": 15000,
    "prompt_tokens": 10000,
    "completion_tokens": 5000
  }
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:281`

---

### 3.4 获取任务队列位置

**接口**：`GET /api/trading-agents/tasks/{task_id}/queue-position`

**描述**：查询任务在等待队列中的位置

**前端调用**：
- **页面**: 分析详情页 (`AnalysisDetailView.vue`)
- **方法**: `getQueuePosition(taskId)`

**响应示例**：

```json
{
  "position": 5,
  "waiting_count": 10
}
```

**字段说明**：
- `position`: 队列位置（0 表示可以执行，>0 表示前面有 N 个任务）
- `waiting_count`: 总等待任务数

**后端实现**: `backend/modules/trading_agents/api/tasks.py:412`

---

### 3.5 取消/停止任务

**接口**：`POST /api/trading-agents/tasks/{task_id}/cancel`

**描述**：取消或停止任务（自动判断状态）

**前端调用**：
- **页面**: 分析详情页 (`AnalysisDetailView.vue`)、任务中心 (`TaskCenterView.vue`)
- **方法**: `cancelTask(taskId)`

**响应示例**：

```json
{
  "success": true,
  "message": "任务已停止"
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:466`

---

### 3.6 重试失败任务

**接口**：`POST /api/trading-agents/tasks/{task_id}/retry`

**描述**：重试失败、已取消或已停止的任务

**前端调用**：
- **页面**: 分析详情页 (`AnalysisDetailView.vue`)、任务中心 (`TaskCenterView.vue`)
- **方法**: `retryTask(taskId)`

**响应**：返回新创建的任务信息（格式同 3.3）

**后端实现**: `backend/modules/trading_agents/api/tasks.py:510`

---

### 3.7 删除任务

**接口**：`DELETE /api/trading-agents/tasks/{task_id}`

**前端调用**：
- **页面**: 任务中心 (`TaskCenterView.vue`)
- **方法**: `deleteTask(taskId, deleteReports)`

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `delete_reports` | boolean | 否 | 是否同时删除关联报告（默认：false） |

**响应示例**：

```json
{
  "success": true,
  "message": "任务已删除"
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:774`

---

### 3.8 批量删除任务

**接口**：`POST /api/trading-agents/tasks/batch-delete`

**前端调用**：
- **页面**: 任务中心 (`TaskCenterView.vue`)
- **方法**: `batchDeleteTasks(taskIds, deleteReports)`

**请求参数**：

```json
{
  "task_ids": ["id1", "id2", "id3"],
  "delete_reports": false
}
```

**响应示例**：

```json
{
  "success_count": 2,
  "failed_count": 1,
  "failed_tasks": [
    {"task_id": "id3", "reason": "运行中的任务不能删除"}
  ],
  "message": "成功删除 2 个任务，失败 1 个"
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:682`

---

### 3.9 清空指定状态任务

**接口**：`DELETE /api/trading-agents/tasks/clear`

**前端调用**：
- **页面**: 任务中心 (`TaskCenterView.vue`)
- **方法**: `clearTasksByStatus(statuses, deleteReports)`

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `statuses` | string | 是 | 状态列表（逗号分隔） |
| `delete_reports` | boolean | 否 | 是否同时删除关联报告 |

**示例**：`/api/trading-agents/tasks/clear?statuses=failed,cancelled,stopped&delete_reports=false`

**后端实现**: `backend/modules/trading_agents/api/tasks.py:589`

---

### 3.10 获取任务状态统计

**接口**：`GET /api/trading-agents/tasks/status-counts`

**描述**：获取用户任务状态统计（用于状态标签栏徽章）

**前端调用**：
- **页面**: 任务中心 (`TaskCenterView.vue`)
- **方法**: `getStatusCounts()`

**响应示例**：

```json
{
  "all": 100,
  "running": 15,
  "completed": 80,
  "failed": 3,
  "cancelled": 2,
  "_detail": {
    "pending": 5,
    "running": 10,
    "completed": 80,
    "failed": 3,
    "cancelled": 1,
    "stopped": 1
  }
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:167`

---

### 3.11 SSE 流式输出

**接口**：`GET /api/trading-agents/tasks/{task_id}/stream`

**描述**：SSE 流式输出任务报告

**前端调用**：
- **页面**: 分析详情页 (`AnalysisDetailView.vue`)
- **方法**: `useSSE()` Hook
- **文件**: `frontend/src/modules/trading_agents/composables/useSSE.ts`

**响应类型**：`text/event-stream`

**前端连接示例**：

```typescript
// frontend/src/modules/trading_agents/composables/useSSE.ts
const { connect, onMessage, onError } = useSSE()

connect(`/api/trading-agents/tasks/${taskId}/stream?token=${token}`)

onMessage((event) => {
  const data = JSON.parse(event.data)

  switch (data.type) {
    case 'report_chunk':
      appendReport(data.content)
      break
    case 'report_complete':
      finalizeReport()
      break
    case 'heartbeat':
      // 心跳，忽略
      break
  }
})
```

**事件类型**：

| 类型 | 描述 |
|------|------|
| `heartbeat` | 心跳事件（任务仍在进行） |
| `report_chunk` | 报告分块 |
| `report_complete` | 报告输出完成 |
| `task_ended` | 任务结束（失败/取消/过期） |
| `error` | 错误事件 |

**后端实现**: `backend/modules/trading_agents/api/tasks.py:325`

---

## 四、智能体配置接口

### 4.1 获取全局配置

**接口**：`GET /api/trading-agents/agent-config`

**描述**：获取全局智能体配置（所有用户共享同一配置）

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue`)、单股分析页 (`SingleAnalysisView.vue`)
- **方法**: `getAgentConfig(params)`

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `include_prompts` | boolean | 否 | 是否包含提示词（仅管理员可用） |

**前端调用示例**：

```typescript
// frontend/src/modules/trading_agents/api.ts
getAgentConfig({ include_prompts: false })
// 普通用户：include_prompts 强制为 false
// 管理员：可指定 true 获取完整提示词
```

**响应示例（普通用户）**：

```json
{
  "id": "...",
  "user_id": "user123",
  "is_customized": false,
  "phase1": {
    "enabled": true,
    "max_rounds": 3,
    "max_concurrency": 3,
    "agents": [
      {
        "slug": "technical",
        "name": "技术分析师",
        "when_to_use": "进行技术分析，识别趋势和形态",
        "enabled_mcp_servers": [],
        "enabled_local_tools": ["get_stock_quotes"],
        "enabled": true
      }
    ]
  },
  "phase2": {
    "enabled": true,
    "max_rounds": 2,
    "agents": [...]
  },
  "phase3": {
    "enabled": true,
    "agents": [...]
  },
  "phase4": {
    "enabled": true,
    "agents": [...]
  }
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:889`

---

### 4.2 更新全局配置

**接口**：`PUT /api/trading-agents/agent-config`

**描述**：更新全局智能体配置（仅管理员可操作）

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue`)
- **方法**: `updateConfig(config)`

**前端调用示例**：

```typescript
// frontend/src/modules/trading_agents/api.ts
updateConfig({
  phase1: {
    enabled: true,
    max_rounds: 3,
    max_concurrency: 3,
    agents: [
      {
        slug: "technical",
        name: "技术分析师",
        role_definition: "你是...", // 仅管理员可编辑
        when_to_use: "进行技术分析",
        enabled_mcp_servers: ["finance"],
        enabled_local_tools: ["get_stock_quotes"],
        enabled: true
      }
    ]
  }
})
```

**响应**：返回更新后的配置

**后端实现**: `backend/modules/trading_agents/api/tasks.py:925`

---

### 4.3 重置为默认配置

**接口**：`POST /api/trading-agents/agent-config/reset`

**描述**：重置全局配置为默认配置（模板）

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue`)
- **方法**: `resetConfig()`

**响应**：返回重置后的配置

**后端实现**: `backend/modules/trading_agents/api/tasks.py:949`

---

### 4.4 导出配置

**接口**：`POST /api/trading-agents/agent-config/export`

**描述**：导出全局配置为 JSON

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue`)
- **方法**: `exportConfig()`

**响应示例**：

```json
{
  "config": {
    "phase1": {...},
    "phase2": {...},
    "phase3": {...},
    "phase4": {...}
  }
}
```

**后端实现**: `backend/modules/trading_agents/api/tasks.py:968`

---

### 4.5 导入配置

**接口**：`POST /api/trading-agents/agent-config/import`

**描述**：从 JSON 导入配置

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue`)
- **方法**: `importConfig(configData)`

**请求参数**：配置数据（参考 3.4 响应格式）

**响应**：返回导入后的配置

**后端实现**: `backend/modules/trading_agents/api/tasks.py:990`

---

### 4.6 获取公共配置（管理员）

**接口**：`GET /api/trading-agents/agent-config/public`

**权限**：仅 ADMIN/SUPER_ADMIN

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue` - 管理员模式)
- **方法**: `getPublicConfig(params)`

**查询参数**：`include_prompts`（是否包含提示词）

**后端实现**: `backend/modules/trading_agents/api/tasks.py:1018`

---

### 4.7 更新公共配置（管理员）

**接口**：`PUT /api/trading-agents/agent-config/public`

**权限**：仅 ADMIN/SUPER_ADMIN

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue` - 管理员模式)
- **方法**: `updatePublicConfig(config)`

**后端实现**: `backend/modules/trading_agents/api/tasks.py:1051`

---

### 4.8 导出公共配置（管理员）

**接口**：`GET /api/trading-agents/admin/public-config/export`

**权限**：仅 ADMIN/SUPER_ADMIN

**描述**：导出公共配置为 YAML 文件

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue` - 管理员编辑公共配置模式)
- **方法**: `exportPublicConfig()`

**响应**：YAML 文件下载

**逻辑**：
- 读取 `agents_public.yaml` 文件
- 返回文件下载流

---

### 4.9 导入公共配置（管理员）

**接口**：`POST /api/trading-agents/admin/public-config/import`

**权限**：仅 ADMIN/SUPER_ADMIN

**描述**：导入 YAML 文件覆盖公共配置

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue` - 管理员编辑公共配置模式)
- **方法**: `importPublicConfig(file)`

**请求**：`multipart/form-data` 上传 YAML 文件

**逻辑**：
- 验证 YAML 格式
- 验证配置结构
- 直接覆盖 `agents_public.yaml`

---

### 4.10 恢复全局配置为默认（管理员）

**接口**：`POST /api/trading-agents/admin/public-config/reset`

**权限**：仅 ADMIN/SUPER_ADMIN

**描述**：用默认配置覆盖全局配置

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue` - 管理员编辑模式)
- **方法**: `resetGlobalConfig()`

**逻辑**：
- 用 `agents_default.yaml` 覆盖全局配置
- 等同于"恢复出厂设置"

---

### 4.11 获取配置来源状态

**接口**：`GET /api/trading-agents/agent-config/status`

**描述**：获取全局配置来源状态

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue`)
- **方法**: `getConfigStatus()`

**响应示例**：

```json
{
  "source": "global",             // global/public/default
  "is_customized": true,          // 是否使用全局自定义配置
  "has_customization": true,      // 是否有自定义配置
  "can_edit_prompts": false       // 是否可编辑提示词（仅管理员）
}
```

**状态说明**：
- `global`: 使用数据库全局配置
- `public`: 使用公共配置 YAML 文件
- `default`: 使用默认配置 YAML 文件（兜底）

---

### 4.12 导出全局配置

**接口**：`GET /api/trading-agents/agent-config/export`

**描述**：导出全局配置为 YAML 文件

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue`)
- **方法**: `exportGlobalConfig()`

**响应**：YAML 文件下载

**逻辑**：
- 从数据库读取全局配置
- 转换为 YAML 格式
- 返回文件下载

---

### 4.13 导入全局配置

**接口**：`POST /api/trading-agents/agent-config/import`

**描述**：导入 YAML 文件作为全局配置

**前端调用**：
- **页面**: 智能体配置管理 (`AgentConfigView.vue`)
- **方法**: `importGlobalConfig(file)`

**请求**：`multipart/form-data` 上传 YAML 文件

**逻辑**：
- 验证 YAML 格式
- 验证配置结构
- 创建/更新数据库记录

---

## 五、设置接口

### 5.1 获取分析设置

**接口**：`GET /api/settings/trading-agents`

**描述**：获取用户的 TradingAgents 分析设置

**前端调用**：
- **页面**: 分析设置 (`AnalysisSettingsView.vue`)
- **方法**: `getSettings()`

**响应示例**：

```json
{
  "id": "...",
  "user_id": "user123",
  "settings": {
    "data_collection_model_id": "claude-sonnet-4-20250514",
    "debate_model_id": "claude-haiku-4-20250514",
    "default_debate_rounds": 2,
    "max_debate_rounds": 3,
    "phase_timeout_minutes": 30,
    "agent_timeout_minutes": 10,
    "tool_timeout_seconds": 60,
    "task_expiry_hours": 24,
    "archive_days": 30,
    "enable_loop_detection": true,
    "enable_progress_events": true
  },
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z"
}
```

**后端实现**: `backend/modules/trading_agents/api/settings.py`

---

### 5.2 更新分析设置

**接口**：`PUT /api/settings/trading-agents`

**前端调用**：
- **页面**: 分析设置 (`AnalysisSettingsView.vue`)
- **方法**: `updateSettings(settings)`

**后端实现**: `backend/modules/trading_agents/api/settings.py`

---

## 六、管理员接口

### 6.1 获取所有任务

**接口**：`GET /api/admin/trading-agents/tasks`

**权限**：仅 ADMIN/SUPER_ADMIN

**前端调用**：
- **页面**: 所有任务管理 (`AllTasksView.vue`)
- **方法**: `listAllTasks(params)`

**查询参数**：支持按 `user_id`、`status`、`stock_code` 等筛选

**后端实现**: `backend/modules/trading_agents/api/admin_tasks.py`

---

### 6.2 获取告警列表

**接口**：`GET /api/admin/alerts`

**权限**：仅 ADMIN/SUPER_ADMIN

**前端调用**：
- **页面**: 告警管理 (`AlertsView.vue`)
- **方法**: `getAlerts()`

**后端实现**: `backend/core/admin/api/alerts.py`

---

### 6.3 处理告警

**接口**：`POST /api/admin/alerts/{id}/handle`

**权限**：仅 ADMIN/SUPER_ADMIN

**前端调用**：
- **页面**: 告警管理 (`AlertsView.vue`)
- **方法**: `handleAlert(id, action)`

**后端实现**: `backend/core/admin/api/alerts.py`

---

### 6.4 忽略告警

**接口**：`POST /api/admin/alerts/{id}/dismiss`

**权限**：仅 ADMIN/SUPER_ADMIN

**前端调用**：
- **页面**: 告警管理 (`AlertsView.vue`)
- **方法**: `dismissAlert(id)`

**后端实现**: `backend/core/admin/api/alerts.py`

---

## 七、WebSocket 与 SSE

### 7.1 WebSocket 实时推送

**连接端点**：`WS /api/trading-agents/ws/{user_id}`

**描述**：建立 WebSocket 连接，接收任务进度实时推送

**前端调用**：
- **Hook**: `useWebSocket()`
- **文件**: `frontend/src/modules/trading_agents/composables/useWebSocket.ts`

**连接方式**：

```typescript
// frontend/src/modules/trading_agents/composables/useWebSocket.ts
const { connect, disconnect, on, off } = useWebSocket()

const wsUrl = `ws://localhost:8000/api/trading-agents/ws/${userId}?token=${jwtToken}`
connect(wsUrl)

// 监听任务进度
on('task_progress', (data) => {
  updateAgentStatus(data)
})

// 监听阶段完成
on('phase_completed', (data) => {
  markPhaseComplete(data.phase)
})

// 监听任务完成
on('task_completed', (data) => {
  showFinalReport(data)
})
```

**连接认证**：通过 Query 参数传递 Token

```
WS /api/trading-agents/ws/{user_id}?token={jwt_token}
```

**事件类型**：

| 事件类型 | 前端处理 | 说明 |
|----------|----------|------|
| `task_created` | 更新任务列表 | 任务创建 |
| `task_started` | 更新状态为运行中 | 任务开始 |
| `task_progress` | 更新进度条和智能体状态 | 进度更新 |
| `phase_started` | 展开阶段卡片 | 阶段开始 |
| `phase_completed` | 标记阶段完成 | 阶段完成 |
| `agent_started` | 高亮智能体卡片 | 智能体开始 |
| `agent_completed` | 标记智能体完成 | 智能体完成 |
| `task_completed` | 显示最终报告 | 任务完成 |
| `task_failed` | 显示错误信息 | 任务失败 |
| `task_cancelled` | 显示取消状态 | 任务取消 |

**事件格式**：

```json
{
  "event": "task_progress",
  "data": {
    "task_id": "678901234567890123456789",
    "stock_code": "600000",
    "phase": 1,
    "stage": "phase1",
    "agent_slug": "technical",
    "agent_name": "技术分析师",
    "progress": 25.0,
    "message": "技术分析中..."
  },
  "timestamp": 1736836800
}
```

**后端实现**: `backend/modules/trading_agents/api/reports.py`

---

### 7.2 SSE 流式报告

详见 [3.11 SSE 流式输出](#311-sse-流式输出)

---

## 八、数据模型

### 8.1 任务状态枚举

| 状态 | 代码 | 描述 |
|------|------|------|
| 待执行 | `PENDING` | 任务已创建，等待执行 |
| 分析中 | `RUNNING` | 任务正在执行 |
| 已完成 | `COMPLETED` | 任务执行成功 |
| 已失败 | `FAILED` | 任务执行失败 |
| 已取消 | `CANCELLED` | 任务被取消（未执行） |
| 已停止 | `STOPPED` | 任务被停止（执行中） |
| 已过期 | `EXPIRED` | 任务超时过期 |

### 8.2 推荐等级枚举

| 等级 | 代码 | 描述 |
|------|------|------|
| 强烈买入 | `STRONG_BUY` | 预期显著上涨 |
| 买入 | `BUY` | 预期上涨 |
| 持有 | `HOLD` | 维持现有仓位 |
| 卖出 | `SELL` | 预期下跌 |
| 强烈卖出 | `STRONG_SELL` | 预期显著下跌 |

### 8.3 风险等级枚举

| 等级 | 代码 | 描述 |
|------|------|------|
| 低风险 | `LOW` | 风险较低 |
| 中风险 | `MEDIUM` | 风险适中 |
| 高风险 | `HIGH` | 风险较高 |

### 8.4 阶段配置模型

```typescript
interface StageConfig {
  enabled: boolean
  // Phase 1 特有
  max_rounds?: number
  max_concurrency?: number
  selected_agents?: string[]  // 用户选择的智能体
  // Phase 2 特有
  debate?: {
    rounds: number
    concurrency: number
  }
}
```

### 8.5 任务创建请求模型

```typescript
interface TaskCreateRequest {
  stock_codes: string[]           // 1-50 个股票代码
  market?: string                 // 市场类型
  trade_date?: string             // 交易日期
  stages?: {
    stage1?: StageConfig
    stage2?: StageConfig
    stage3?: StageConfig
    stage4?: StageConfig
  }
  data_collection_model?: string  // 数据收集模型 ID
  debate_model?: string           // 辩论模型 ID
}
```

---

## 九、错误码

### 9.1 HTTP 状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 配额不足 |
| 500 | 服务器内部错误 |

### 9.2 业务错误码

| 错误信息 | 场景 |
|----------|------|
| 配额不足 | 用户任务配额已用完 |
| 任务不存在 | 任务 ID 无效 |
| 无权操作此任务 | 尝试操作其他用户的任务 |
| 运行中的任务不能删除 | 需先停止任务再删除 |
| 只有失败的任务可以重试 | 状态不符合重试条件 |
| 股票代码数量超出限制 | 批量任务超过 50 个 |
| 提示词仅管理员可编辑 | 普通用户尝试修改提示词 |

---

## 十、API 调用流程

### 10.1 创建分析任务流程

```
用户操作                       前端                          后端
──────────────────────────────────────────────────────────────────────
1. 打开单股分析页面
   → 页面加载
   → getAgentConfig()
   → listModels()
   → 渲染表单

2. 填写表单并提交
   → 表单验证
   → createTasks()
   → POST /api/trading-agents/tasks
   → 创建任务
   → 返回 task_id

3. 跳转到分析详情
   → getTask(task_id)
   → GET /api/trading-agents/tasks/{id}
   → 返回任务详情

4. 建立 WebSocket
   → WebSocket.connect()
   → WS /api/trading-agents/ws/{user_id}
   → 推送实时事件
   → 更新 UI

5. 建立 SSE
   → SSE.connect()
   → GET /api/trading-agents/tasks/{id}/stream
   → 流式输出报告
   → 渲染 Markdown
```

### 10.2 任务管理流程

```
用户操作                       前端                          后端
──────────────────────────────────────────────────────────────────────
1. 打开任务中心
   → getStatusCounts()
   → GET /api/trading-agents/tasks/status-counts
   → 更新徽章数字

2. 加载任务列表
   → listTasks()
   → GET /api/trading-agents/tasks
   → 渲染列表

3. 筛选任务
   → listTasks({status: 'completed'})
   → GET /api/trading-agents/tasks?status=completed
   → 更新列表

4. 删除任务
   → deleteTask(task_id)
   → DELETE /api/trading-agents/tasks/{id}
   → 从列表移除

5. 批量删除
   → batchDeleteTasks([id1, id2])
   → POST /api/trading-agents/tasks/batch-delete
   → 更新列表
```

### 10.3 配置管理流程

```
用户操作                       前端                          后端
──────────────────────────────────────────────────────────────────────
1. 打开智能体配置
   → getAgentConfig()
   → GET /api/trading-agents/agent-config
   → 渲染配置面板

2. 修改配置
   → updateConfig(newConfig)
   → PUT /api/trading-agents/agent-config
   → 保存配置
   → 刷新显示

3. 导出配置
   → exportConfig()
   → POST /api/trading-agents/agent-config/export
   → 下载 JSON 文件

4. 导入配置
   → 上传文件
   → importConfig(configData)
   → POST /api/trading-agents/agent-config/import
   → 应用配置
```

---

## 相关文档

### TradingAgents 内部文档

- [架构设计](./architecture/架构设计.md) - 整体架构、核心组件、技术选型
- [四阶段工作流](./architecture/四阶段工作流.md) - 四阶段工作流详细设计、执行流程
- [并发控制机制](./architecture/并发控制机制.md) - 三层并发控制、队列管理、资源调度
- [智能体配置](./features/智能体配置.md) - 智能体配置管理、配置层级、读取优先级
- [分析设置](./features/分析设置.md) - 用户分析参数设置、模型配置、超时配置
- [MCP 工具使用](./tools/MCP工具.md) - TradingAgents 如何使用 MCP 工具
- [前端页面设计](./前端页面设计.md) - 前端页面功能、布局、交互设计

### 依赖的基础设施模块文档

- [核心 AI 模块](../../backend/core/ai/README.md) - 模型管理、LLM 调用、Token 计数、定价
- [MCP 模块](../MCP/MCP模块设计方案.md) - 工具协议、连接池、服务器管理
- [市场数据模块](../market_data/README.md) - A股/美股/港股数据

---

**最后更新**: 2026-01-14
**维护者**: StockAnalysis 开发团队
