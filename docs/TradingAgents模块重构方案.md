# TradingAgents 模块重构方案 v4

> 创建时间: 2026-01-12
> 完成时间: 2026-01-12
> 基于: AI 框架重构方案 v4.0（LangChain 统一架构）
> 状态: 已完成
> 核心原则: **按业务逻辑组织目录，使用 LangChain 统一服务**

---

## 一、核心设计原则

1. **完全放弃 LangGraph**，使用 LangChain + asyncio 调度
2. **目录结构即业务流程** - 一目了然
3. **调度器编排四阶段** - 不用复杂的图定义
4. **使用 AIService** - 通过 `get_ai_service().chat_completion()` 统一调用
5. **LangChain 统一** - 所有模型通过 LangChain ChatOpenAI 调用

---

## 二、目录结构设计

```
modules/trading_agents/
│
├── api/                          # 对外服务
│   ├── tasks.py                  # 任务创建、查询、取消 API
│   └── reports.py                # 报告查询 API
│
├── scheduler/                    # 核心调度器
│   └── workflow_scheduler.py     # 按顺序调度 Phase 1→2→3→4
│
├── phases/                       # 四阶段（每个阶段独立）
│   │
│   ├── phase1/                   # 第一阶段：分析师团队
│   │   ├── runner.py             # 运行器（并发执行动态分析师）
│   │   └── agents/               # 智能体配置（动态数量）
│   │       ├── technical.yaml
│   │       ├── fundamental.yaml
│   │       └── ...               # 用户可自定义
│   │
│   ├── phase2/                   # 第二阶段：研究与辩论
│   │   ├── runner.py             # 运行器（固定流程）
│   │   └── agents/               # 固定 4 个智能体
│   │       ├── bull.yaml         # 看涨
│   │       ├── bear.yaml         # 看跌
│   │       ├── manager.yaml      # 研究经理
│   │       └── planner.yaml      # 交易计划
│   │
│   ├── phase3/                   # 第三阶段：风险评估
│   │   ├── runner.py             # 运行器（固定流程）
│   │   └── agents/               # 固定 4 个智能体
│   │       ├── aggressive.yaml
│   │       ├── conservative.yaml
│   │       ├── neutral.yaml
│   │       └── cro.yaml
│   │
│   └── phase4/                   # 第四阶段：总结报告
│       ├── runner.py             # 运行器
│       └── agents/
│           └── summarizer.yaml
│
├── pusher/                       # WebSocket 推送
│   ├── manager.py
│   └── events.py
│
├── manager/                      # 任务管理
│   ├── task_manager.py
│   ├── batch_manager.py
│   ├── concurrency_controller.py
│   └── task_restorer.py
│
├── config/                       # 配置管理
│   ├── loader.py                 # YAML 配置加载器
│   └── prompts/defaults/         # 默认提示词
│
├── services/                     # 业务服务
│   ├── agent_config_service.py
│   ├── report_service.py
│   └── report_archival.py
│
├── schemas.py                    # 数据模型
├── exceptions.py                 # 异常定义
│
└── infra/                        # 基础设施
    ├── database.py
    └── alerts.py
```

---

## 三、与 AIService 的集成

### 3.1 核心调用方式

```python
from core.ai import get_ai_service, AIMessage

# 获取 AI 服务
ai_service = get_ai_service()

# 调用聊天补全
response = await ai_service.chat_completion(
    user_id=user_id,
    model_id=model_id,
    messages=[
        AIMessage(role="system", content="你是xxx"),
        AIMessage(role="user", content="分析股票"),
    ],
    tools=[...],
)

# 访问结果
response.content              # 最终答案
response.reasoning_content    # 思考过程（GLM-4.7）
response.usage                # Token 使用统计
```

### 3.2 框架自动选择逻辑

所有模型统一使用 **LangChain ChatOpenAI**，通过 `base_url` 区分：

| 模型 | `platform` | `base_url` |
|------|-----------|-----------|
| 智谱 GLM | `zhipu` | `https://open.bigmodel.cn/api/paas/v4` |
| 智谱编程 | `zhipu_coding` | `https://open.bigmodel.cn/api/coding/paas/v4` |
| DeepSeek | `deepseek` | `https://api.deepseek.com` |
| 千问 | `qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| OpenAI | `openai` | 默认 |
| Claude | `anthropic` | 使用 ChatAnthropic |

**关键点**:
- 所有模型通过 LangChain 统一调用
- GLM-4.7 思考能力通过 `model_kwargs={"thinking": {...}}` 支持
- trading_agents **不需要知道**底层模型差异

---

## 四、各模块职责说明

### 4.1 scheduler/workflow_scheduler.py

**职责**: 按业务流程顺序调度四个阶段

**核心逻辑**:
```
Phase 1 (并发) → Phase 2 (串行) → Phase 3 (串行) → Phase 4 (串行)
```

**不使用**:
- ❌ LangGraph StateGraph
- ❌ 图定义、边、条件路由

**使用**:
- ✅ `asyncio.gather()` 并发执行 Phase 1 分析师
- ✅ `await` 串行执行 Phase 2/3/4

---

### 4.2 phases/phase1/ (动态分析师)

**特点**:
- 智能体数量**不确定** - 从 `agents/*.yaml` 动态加载
- 支持**并发执行** - `asyncio.gather()`
- 用户可**自定义** - 添加新的 YAML 文件

**runner.py 职责**:
1. 扫描 `agents/` 目录，加载所有 `.yaml` 配置
2. 过滤出 `enabled: true` 的智能体
3. 并发执行所有启用的分析师
4. 汇总报告返回

**agents/*.yaml 配置项**:
| 字段 | 说明 |
|------|------|
| `slug` | 唯一标识 |
| `name` | 显示名称 |
| `enabled` | 是否启用 |
| `model_ref` | 引用的模型（data_collection_model） |
| `role_definition` | 提示词 |
| `enabled_tools` | 启用的工具列表 |
| `enabled_mcp_servers` | 启用的 MCP 服务器 |

---

### 4.3 phases/phase2/ (研究与辩论)

**特点**:
- 智能体**固定 4 个** - 看涨、看跌、研究经理、交易计划
- 流程**固定** - 初始观点 → 辩论轮次 → 裁决 → 交易计划
- 提示词从 YAML 加载

**runner.py 执行流程**:
```
1. 看涨初始观点 + 看跌初始观点（并行）
2. 循环辩论（可配置轮次）
   └─ 每轮：看涨反驳 + 看跌反驳（并行）
3. 研究经理裁决
4. 交易计划制定
```

---

### 4.4 phases/phase3/ (风险评估)

**特点**:
- 智能体**固定 4 个** - 激进派、保守派、中性派、首席风控官
- 流程**固定** - 三派评估（可并行）→ CRO 总结

**runner.py 执行流程**:
```
1. 激进 + 保守 + 中性（可并行）
2. 首席风控官综合三方意见
```

---

### 4.5 phases/phase4/ (总结报告)

**特点**:
- 智能体**固定 1 个** - 最终总结
- 汇总所有阶段信息
- 生成投资建议（买入/卖出/持有）

---

## 五、配置文件示例

### 5.1 Phase 1 分析师配置（动态数量）

```yaml
# phases/phase1/agents/technical.yaml
slug: technical_analyst
name: 技术分析师
enabled: true

# 模型引用（指向用户配置的模型）
model_ref: data_collection_model

# 角色定义（提示词）
role_definition: |
  你是一位专业的技术分析师。
  你的任务是分析股票的技术面，包括：
  - 趋势分析
  - 支撑压力位
  - 技术指标
  - 成交量分析

  请基于市场数据，生成专业的技术分析报告。

# 工具配置
enabled_tools:
  - get_stock_quotes
  - get_technical_indicators

# MCP 服务器
enabled_mcp_servers:
  - market_data
```

### 5.2 Phase 2 固定智能体配置

```yaml
# phases/phase2/agents/bull.yaml
slug: bull_analyst
name: 看涨分析师
enabled: true  # 固定智能体，不建议禁用

model_ref: debate_model

role_definition: |
  你是一位经验丰富的看涨研究员。
  你的任务是基于第一阶段分析师团队的报告，构建看涨投资逻辑。

  请：
  1. 仔细阅读第一阶段所有分析师的报告
  2. 提炼其中的看涨论据和投资机会
  3. 构建完整的看涨投资逻辑
  4. 给出明确的看涨建议

enabled_tools: []
enabled_mcp_servers: []
```

---

## 六、文件删除/新建/迁移清单

### 6.1 删除的文件（11 个）

| 文件 | 删除原因 |
|------|----------|
| `workflow/nodes.py` | 2295行，逻辑分散到 phases/*/runner.py |
| `workflow/graph.py` | 不使用 LangGraph，用 scheduler 调度 |
| `workflow/executor.py` | 逻辑分散到 phases/*/runner.py |
| `workflow/adapter.py` | 不再需要适配器 |
| `workflow/integration.py` | 不再需要集成入口 |
| `workflow/state.py` | 状态定义移到 scheduler/ |
| `tools/registry.py` | 直接使用 MCP 模块 |
| `tools/mcp_tool_filter.py` | 直接使用 MCP 模块 |
| `tools/local_tools.py` | 移到配置文件 |
| `tools/loop_detector.py` | 简化逻辑 |
| `tools/registry_timeout.py` | 简化逻辑 |
| `models/state.py` | 旧版状态模型 |

### 6.2 新建的文件/目录

| 路径 | 说明 |
|------|------|
| `scheduler/workflow_scheduler.py` | 工作流调度器 |
| `scheduler/state.py` | 工作流状态定义（从 workflow/state.py 迁移） |
| `phases/phase1/runner.py` | Phase 1 运行器 |
| `phases/phase1/agents/*.yaml` | Phase 1 智能体配置（动态） |
| `phases/phase2/runner.py` | Phase 2 运行器 |
| `phases/phase2/agents/*.yaml` | Phase 2 智能体配置（固定 4 个） |
| `phases/phase3/runner.py` | Phase 3 运行器 |
| `phases/phase3/agents/*.yaml` | Phase 3 智能体配置（固定 4 个） |
| `phases/phase4/runner.py` | Phase 4 运行器 |
| `phases/phase4/agents/*.yaml` | Phase 4 智能体配置（固定 1 个） |
| `pusher/manager.py` | WebSocket 管理器（从 websocket/ 迁移） |
| `pusher/events.py` | 事件定义（从 websocket/ 迁移） |
| `manager/` | 任务管理相关（从 core/ 迁移） |
| `config/loader.py` | 配置加载器 |
| `config/prompts/defaults/` | 默认提示词 |

### 6.3 重命名/重组

| 原路径 | 新路径 |
|--------|--------|
| `websocket/` | `pusher/` |
| `core/task_manager.py` | `manager/task_manager.py` |
| `core/batch_manager.py` | `manager/batch_manager.py` |
| `core/concurrency_controller.py` | `manager/concurrency_controller.py` |
| `core/task_manager_restore.py` | `manager/task_restorer.py` |

---

## 七、执行步骤

### 阶段 1: 创建目录结构

```
scheduler/
phases/phase1/agents/
phases/phase2/agents/
phases/phase3/agents/
phases/phase4/agents/
pusher/
manager/
config/prompts/defaults/
```

### 阶段 2: 实现核心功能

1. `scheduler/workflow_scheduler.py` - 调度器
2. `scheduler/state.py` - 状态定义
3. `phases/phase1/runner.py` - 并发执行动态分析师
4. `phases/phase2/runner.py` - 固定流程
5. `phases/phase3/runner.py` - 固定流程
6. `phases/phase4/runner.py` - 固定流程

### 阶段 3: 配置管理

1. 创建智能体 YAML 配置文件
2. `config/loader.py` - 配置加载器
3. 迁移提示词模板

### 阶段 4: 迁移与清理

1. 迁移 `websocket/` → `pusher/`
2. 迁移 `core/*` → `manager/*`
3. 删除 11 个旧文件

### 阶段 5: 测试验证

1. 单元测试
2. 集成测试
3. 前端联调

---

## 八、关键设计决策

| 决策 | 理由 |
|------|------|
| **不用 LangGraph** | 业务流程用调度器更清晰，不需要复杂的图定义 |
| **目录即业务流程** | 一目了然，新人快速理解 |
| **Phase 1 动态** | 支持用户自定义分析师数量和类型 |
| **Phase 2/3/4 固定** | 业务逻辑固定，只需调整提示词 |
| **使用 AIService** | 通过 `get_ai_service().chat_completion()` 统一调用 |
| **LangChain 统一** | 所有模型通过 ChatOpenAI + base_url 统一 |

---

## 九、与 AIService 的集成关系

```
┌─────────────────────────────────────────────────────────────┐
│                  TradingAgents 业务层                        │
│                                                             │
│  scheduler/workflow_scheduler.py                            │
│  phases/*/runner.py                                         │
│  └─ 调用: get_ai_service().chat_completion()                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI 服务层 (core/ai/)                       │
│                                                             │
│  AIService.chat_completion()                                │
│  └─ LangChainAdapter.create_chat_model()                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangChain 框架                             │
│                                                             │
│  ChatOpenAI (智谱/Claude/DeepSeek/千问 统一)                  │
│  └─ model_kwargs={"thinking": {...}}  (GLM-4.7 思考能力)      │
└─────────────────────────────────────────────────────────────┘
```

**集成优势**:
- trading_agents 只需调用 `get_ai_service().chat_completion()`
- 所有模型通过 LangChain 统一调用
- GLM-4.7 思考能力通过 `model_kwargs` 传递
- 未来添加新模型无需修改 trading_agents

---

---

## 十、完成总结

### 10.1 已完成的工作

**代码重构**:
- ✅ 创建 `scheduler/` 目录，实现 WorkflowScheduler 调度器
- ✅ 创建 `phases/phase1-4/` 目录，实现四阶段运行器
- ✅ 创建 13 个 YAML 智能体配置文件
- ✅ 将 `websocket/` 重命名为 `pusher/`
- ✅ 将 `core/` 任务管理迁移到 `manager/`
- ✅ 更新 `config/loader.py` 支持新的目录结构
- ✅ 更新所有导入路径，移除对旧模块的依赖

**文件清理**:
- ✅ 删除 `workflow/` 目录（不再使用 LangGraph）
- ✅ 删除 `tools/mcp_tool_filter.py`（直接使用 MCP 模块）
- ✅ 清理所有旧的导入引用

**API 更新**:
- ✅ 更新 `core/background_tasks.py` 使用新调度器
- ✅ 更新 `manager/task_manager.py` 使用新的 pusher API
- ✅ 更新所有模块的导入路径

**导入修复**:
- ✅ 修复 `manager/__init__.py` 中的导入（使用正确的类名和函数名）
- ✅ 修复 `pusher/__init__.py` 中的导入
- ✅ 修复 `config/__init__.py` 中的导入
- ✅ 修复所有其他文件中的旧导入

### 10.2 目录结构（实际）

```
modules/trading_agents/
├── scheduler/
│   ├── __init__.py
│   ├── state.py                 # WorkflowState 状态定义
│   └── workflow_scheduler.py    # WorkflowScheduler 调度器
├── phases/
│   ├── __init__.py
│   ├── phase1/
│   │   ├── runner.py            # run_phase1()
│   │   └── agents/
│   │       ├── technical.yaml   # 技术分析师
│   │       ├── sentiment.yaml   # 市场情绪分析师
│   │       ├── fundamentals.yaml # 基本面分析师
│   │       └── news.yaml        # 新闻分析师
│   ├── phase2/
│   │   ├── runner.py            # run_phase2()
│   │   └── agents/
│   │       ├── bull.yaml        # 看涨分析师
│   │       ├── bear.yaml        # 看跌分析师
│   │       ├── manager.yaml     # 研究经理
│   │       └── planner.yaml     # 交易计划
│   ├── phase3/
│   │   ├── runner.py            # run_phase3()
│   │   └── agents/
│   │       ├── aggressive.yaml  # 激进派
│   │       ├── conservative.yaml # 保守派
│   │       ├── neutral.yaml     # 中性派
│   │       └── cro.yaml         # 首席风控官
│   └── phase4/
│       ├── runner.py            # run_phase4()
│       └── agents/
│           └── summarizer.yaml  # 总结分析师
├── pusher/
│   ├── __init__.py
│   ├── manager.py               # WebSocketManager
│   └── events.py                # 事件定义
├── manager/
│   ├── __init__.py
│   ├── task_manager.py          # TaskManager
│   ├── task_manager_restore.py  # 恢复功能
│   ├── batch_manager.py         # BatchTaskManager
│   ├── concurrency_controller.py # ConcurrencyController
│   ├── task_queue.py            # TaskQueueManager
│   ├── task_expiry.py           # TaskExpiryHandler
│   └── concurrency.py           # ConcurrencyManager
├── config/
│   ├── __init__.py
│   └── loader.py                # ConfigLoader
└── tools/
    └── __init__.py              # （已清空，工具通过 MCP 提供）
```

### 10.3 验证结果

**导入测试通过**:
```bash
from modules.trading_agents.scheduler.state import WorkflowState
from modules.trading_agents.scheduler.workflow_scheduler import create_workflow_scheduler
from modules.trading_agents.phases import run_phase1, run_phase2, run_phase3, run_phase4
from modules.trading_agents.pusher import get_ws_manager
from modules.trading_agents.manager import get_task_manager
from modules.mcp.pool.pool import get_mcp_connection_pool
# ✅ All imports successful!
```

**旧导入清理完成**:
- ✅ 无 `from modules.trading_agents.core.` 引用
- ✅ 无 `from modules.trading_agents.websocket.` 引用
- ✅ 无 `from modules.trading_agents.workflow.` 引用
- ✅ 无 `from modules.trading_agents.tools.mcp_tool_filter` 引用

---

**文档结束**
