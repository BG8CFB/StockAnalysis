# TradingAgents 模块文档

## 文档目录

### 🏗️ 架构设计 (architecture/)

架构层面的设计文档，包括整体架构、公用机制、技术细节。

| 文档 | 描述 |
|------|------|
| [架构设计](./architecture/架构设计.md) | 整体架构、核心组件、技术选型 |
| [四阶段工作流](./architecture/四阶段工作流.md) | 四阶段工作流详细设计、执行流程 |
| [并发控制机制](./architecture/并发控制机制.md) | 三层并发控制、队列管理、资源调度 |

### 📦 功能模块 (features/)

独立功能模块的业务逻辑文档。

| 文档 | 描述 |
|------|------|
| [智能体配置](./features/智能体配置.md) | 智能体配置管理、配置层级、读取优先级 |
| [分析设置](./features/分析设置.md) | 用户分析参数设置、模型配置、超时配置 |

### 🔧 接口与数据

| 文档 | 描述 |
|------|------|
| [API 接口文档](./API接口文档.md) | 统一 API 文档（接口定义 + 前后端映射 + 调用示例） |
| [数据库设计](./数据库设计.md) | MongoDB 集合设计、字段定义、索引策略 |
| [前端页面设计](./前端页面设计.md) | 前端页面功能、布局、交互设计 |

### 🤖 智能体配置 (agents/)

各阶段智能体的 YAML 配置文件。

| 文档 | 描述 |
|------|------|
| [Phase 1: 信息收集与基础分析](./agents/phase1-信息收集与基础分析.yaml) | 分析师团队配置 |
| [Phase 2: 多空博弈与投资决策](./agents/phase2-多空博弈与投资决策.yaml) | 观点辩论配置 |
| [Phase 3: 交易执行策划](./agents/phase3-交易执行策划.yaml) | 风险评估配置 |
| [Phase 4: 策略风格与风险评估](./agents/phase4-策略风格与风险评估.yaml) | 综合报告配置 |

### 🔌 工具集成 (tools/)

| 文档 | 描述 |
|------|------|
| [MCP 工具使用](./tools/MCP工具.md) | TradingAgents 如何使用 MCP 工具 |

**架构说明**：MCP 模块 (`modules/mcp/`) 是独立的基础设施模块，提供连接池和工具调用能力。TradingAgents 作为使用者，通过连接池调用已配置的 MCP 工具，不负责 MCP 服务器的管理。

---

## 快速开始

### 模块概述

TradingAgents 是基于 **LangChain 1.0** 的多阶段 AI 股票分析系统，使用 `create_agent()` 接口构建智能体，模拟专业投资分析团队的工作模式，通过四阶段流程对投资标的进行深度分析。

### 核心特性

- **LangChain create_agent**：使用 LangChain 1.0 标准接口创建智能体
- **四阶段流程**：并行分析 → 观点辩论 → 交易执行 → 风险评估
- **动态智能体配置**：通过 YAML 文件配置各阶段智能体
- **双模型架构**：数据收集模型 + 辩论模型
- **三层并发控制**：模型级 + 任务级 + 批量级
- **实时进度推送**：WebSocket 事件推送
- **工具集成**：通过 MCP 模块调用外部工具
- **简单调度**：单一调度文件，Python 函数式调用

### 模块依赖关系

**TradingAgents 作为业务模块，依赖以下基础设施模块**：

| 依赖模块 | 路径 | 提供能力 |
|---------|------|---------|
| **核心 AI 模块** | `backend/core/ai/` | 模型管理、LLM 调用、Token 计数、定价、并发控制 |
| **MCP 模块** | `backend/modules/mcp/` | 工具协议、连接池、服务器管理、工具调用 |
| **市场数据模块** | `backend/core/market_data/` | A股/美股/港股数据获取 |

### 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| 工作流实现 | Python async/await + LangChain create_agent | 函数式调用 + 智能体编排 |
| AI 调用 | 核心 AI 模块 (`core/ai`) | 使用核心模块的 AI 服务 |
| 工具调用 | MCP 模块 | 工具连接池和调用 |
| 模型配置 | LangChain ChatModel | 提示词、工具绑定 |
| 并行执行 | asyncio.gather() | 异步并发控制 |
| 数据存储 | MongoDB + Redis | 任务数据、缓存 |
| 实时通信 | WebSocket | 进度推送 |

---

## 架构概览

### 调度流程

TradingAgents 采用简单的函数式调度架构，通过单一调度文件协调各阶段执行。

用户发起分析请求后，调度器依次执行：

1. **Phase 1（信息收集与基础分析）**：并行执行 6 个分析师智能体
   - 财经新闻分析师、社交媒体分析师、中国市场分析师
   - 市场技术分析师、基本面分析师、短线资金分析师

2. **Phase 2（多空博弈与投资决策）**：串行执行观点辩论
   - 看涨分析师、看跌分析师、投资组合经理

3. **Phase 3（交易执行策划）**：执行交易计划制定
   - 专业交易员

4. **Phase 4（策略风格与风险评估）**：并行执行策略分析
   - 激进策略分析师、中性策略分析师、保守策略分析师、风险管理委员会主席

### 智能体结构

各阶段智能体通过 YAML 配置文件定义，包含：
- **角色定义**（roleDefinition）：智能体的系统提示词
- **强制执行标准**：必须遵守的分析规则
- **核心分析维度**：评估的关键指标
- **输出格式**：标准化的 Markdown 报告

---

## 目录结构

### 模块组织

```
backend/modules/trading_agents/
├── scheduler/
│   └── workflow_scheduler.py   # 单一调度文件
├── phases/
│   ├── __init__.py
│   ├── phase1/                 # Phase 1: 信息收集与基础分析
│   │   ├── template.py         # 智能体模板
│   │   └── factory.py          # 动态创建智能体
│   ├── phase2/                 # Phase 2: 多空博弈与投资决策
│   │   ├── bull_researcher.py
│   │   ├── bear_researcher.py
│   │   └── research_manager.py
│   ├── phase3/                 # Phase 3: 交易执行策划
│   │   └── trader.py
│   └── phase4/                 # Phase 4: 策略风格与风险评估
│       ├── aggressive_debator.py
│       ├── neutral_debator.py
│       ├── conservative_debator.py
│       └── risk_manager.py
├── manager/
│   ├── task_manager.py         # 任务管理器
│   └── concurrency_controller.py  # 并发控制器
└── services/
    └── agent_config_service.py  # 智能体配置服务
```

### 版本演进

| 变化类型 | v2.0 | v3.0 |
|----------|------|------|
| 调度方式 | StateGraph 工作流图 | 函数式调用 + create_agent |
| 阶段实现 | runner.py + nodes | 独立智能体文件 |
| 状态管理 | LangGraph State | Python 对象传递 |
| 智能体创建 | 图节点定义 | create_agent() 接口 |

---

## 相关文档

### 依赖的基础设施模块

- [核心 AI 模块](../../backend/core/ai/README.md) - 模型管理、LLM 调用、Token 计数、定价
- [MCP 模块](../MCP/MCP模块设计方案.md) - 工具协议、连接池、服务器管理
- [市场数据模块](../market_data/README.md) - A股/美股/港股数据

### 项目文档

- [项目记忆文档 - TradingAgents 章节](../../CLAUDE.md#tradingagents-模块)

---

**最后更新**: 2026-01-14
**维护者**: StockAnalysis 开发团队
