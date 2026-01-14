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
| [MCP工具](./tools/MCP工具.md) | MCP 工具集成方案、财经工具配置 |

---

## 快速开始

### 模块概述

TradingAgents 是基于 **LangChain** 和 **Python 原生 async/await** 的多阶段 AI 股票分析系统，模拟专业投资分析团队的工作模式，通过结构化的四阶段工作流对投资标的进行深度分析。

### 核心特性

- **四阶段工作流**：并行分析 → 观点辩论 → 风险评估 → 综合报告
- **动态智能体配置**：第一阶段智能体完全可配置
- **双模型架构**：数据收集模型 + 辩论模型
- **三层并发控制**：模型级 + 任务级 + 批量级
- **实时进度推送**：WebSocket 事件推送
- **MCP 工具集成**：统一的工具调用协议
- **简单调度**：单一调度文件，Python 原生控制流

### 技术栈

| 组件 | 技术选型 |
|------|----------|
| 工作流实现 | Python async/await + asyncio |
| AI 集成 | LangChain (ChatOpenAI, ChatPromptTemplate) |
| 工具协议 | MCP (Model Context Protocol) |
| 并行执行 | asyncio.gather(), asyncio.Semaphore |
| 数据存储 | MongoDB + Redis |
| 实时通信 | WebSocket |

---

## 架构概览

### 调度流程

```
用户任务请求
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│              workflow_scheduler.py (单一调度文件)            │
│                                                             │
│  async def run_trading_analysis(symbol, config):            │
│      state = AnalysisState(symbol)                           │
│      model = ChatOpenAI(model=config["model"])              │
│                                                             │
│      # Phase 1: 并行分析师团队                               │
│      phase1 = await asyncio.gather(*[                       │
│          run_analyst(state, model, cfg)                     │
│          for cfg in config["phase1_analysts"]                │
│      ])                                                      │
│                                                             │
│      # Phase 2: 串行观点辩论                                 │
│      phase2 = await run_phase2_debate(state, model)          │
│                                                             │
│      # Phase 3: 并行风险评估                                 │
│      phase3 = await asyncio.gather(*[                       │
│          run_risk_assessor(state, model, cfg)               │
│          for cfg in config["phase3_assessors"]               │
│      ])                                                      │
│                                                             │
│      # Phase 4: 综合报告                                     │
│      final = await run_phase4_report(state, model)           │
│                                                             │
│      return state                                            │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
  返回最终报告
```

### LangChain 组件使用

```python
# 模型初始化
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7
)

# 提示词模板
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是专业股票分析师"),
    ("human", "请分析股票：{symbol}")
])

# 工具绑定
if tools:
    model_with_tools = model.bind_tools(tools)

# 调用模型
chain = prompt | model_with_tools
result = await chain.ainvoke({"symbol": "AAPL"})
```

---

## 目录结构变化

### v2.0 (LangGraph) → v3.0 (LangChain)

| 变化类型 | v2.0 | v3.0 |
|----------|------|------|
| 调度器 | `scheduler/workflow_scheduler.py` + StateGraph | `scheduler/workflow_scheduler.py` (单一文件) |
| 阶段层 | `phases/phase{N}/runner.py` | `phases/phase{N}.py` (函数) |
| 状态管理 | LangGraph State (TypedDict) | Pydantic BaseModel |
| 并行控制 | LangGraph 内置 | asyncio.gather() |
| 依赖 | langgraph | langchain-openai, langchain-core |

### 简化后的目录结构

```
backend/modules/trading_agents/
├── scheduler/
│   └── workflow_scheduler.py   # 单一调度文件 ⭐
├── phases/
│   ├── phase1.py               # Phase 1 函数
│   ├── phase2.py               # Phase 2 函数
│   ├── phase3.py               # Phase 3 函数
│   └── phase4.py               # Phase 4 函数
├── manager/
│   ├── task_manager.py         # 任务管理器
│   └── concurrency_controller.py  # 并发控制器
└── services/
    └── agent_config_service.py  # 智能体配置服务
```

---

## 相关文档

- [项目记忆文档 - TradingAgents 章节](../../CLAUDE.md#tradingagents-模块)
- [MCP 模块完整文档](../MCP/MCP模块完整文档.md)
- [市场数据模块文档](../market_data/README.md)
- [API 文档](../API文档.md)

---

**最后更新**: 2026-01-14
**维护者**: StockAnalysis 开发团队
