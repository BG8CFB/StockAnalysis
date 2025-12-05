# 第三阶段实施计划：智能分析与选股 (Phase 3: AI Analysis & Screener)

## 1. 阶段目标
本阶段是系统的**核心价值**交付期。我们将引入 LLM (OpenAI/DeepSeek) 赋予系统"大脑"，并构建高性能的选股引擎。
核心任务是实现 **AI 分析实验室** 和 **智能选股器**。

## 2. 模块化设计 (Module Specification)

### 2.1 新增模块：`modules/analysis` (AI 核心)
*   **职责**: 调度 AI Agent 进行深度研报生成。
*   **核心技术**: LangChain (或原生 OpenAI SDK), 异步任务队列 (Task Queue)。
*   **数据流**: 调用 `modules/market` 获取数据 -> 送入 LLM -> 生成 Markdown 报告。

### 2.2 新增模块：`modules/screener` (流量入口)
*   **职责**: 提供基于财务、技术指标的即时选股能力。
*   **核心技术**: MongoDB Aggregation Pipeline (聚合查询), 宽表预计算。

## 3. 详细执行步骤 (Task Breakdown)

### 步骤 1: 智能分析引擎 (Backend - Analysis Engine)
*   [ ] **Agent 框架搭建**: 
    *   定义 `UniversalAgent` 类，支持加载 `StockAnalysis.yaml` 配置文件。
    *   实现 "Context-Aware Tools"：让 Agent 能自动调用 `modules/market` 的数据接口。
*   [ ] **异步任务系统**: 
    *   引入 `BackgroundTasks` 或 `Celery` 处理耗时的分析任务（30s - 2min）。
    *   实现任务状态管理 (`PENDING` -> `PROCESSING` -> `COMPLETED`)。
*   [ ] **流式输出 (Streaming)**: 
    *   实现 SSE (Server-Sent Events) 接口，将 Agent 的思考过程 (`Thinking...`) 实时推送到前端。

### 步骤 2: 智能选股引擎 (Backend - Screener Engine)
*   [ ] **宽表同步服务 (Wide-Table Sync)**:
    *   开发定时任务，每日从 Tushare/AkShare 拉取基础指标 (PE, PB, ROE)。
    *   将行情数据与财务数据合并，存入 `stock_basic_info` 宽表。
*   [ ] **筛选器实现**:
    *   编写 `DatabaseScreeningService`，将前端 JSON 条件自动转换为 MongoDB 查询语句。
    *   **测试**: 验证复杂组合条件（如 `行业=银行 AND PE<5`）的准确性。

### 步骤 3: 前端 AI 实验室开发 (Frontend - AI Lab)
*   [ ] **分析请求页**: 支持用户选择"分析师角色"（如基本面专家、技术面专家）。
*   [ ] **实时报告页**: 
    *   使用 Markdown 渲染组件展示最终报告。
    *   使用 WebSocket/SSE 组件展示实时推理步骤日志。

### 步骤 4: 前端选股器开发 (Frontend - Screener)
*   [ ] **策略构建器**: 动态表单组件，支持添加/删除筛选条件。
*   [ ] **结果表格**: 展示筛选结果，支持一键跳转到"AI分析"。

## 4. 验收标准
1.  用户输入 `NVDA`，AI 能生成一份包含最新新闻和财报数据的中文分析报告。
2.  选股器能在一秒内筛选出 "PE < 10 且 股息率 > 5%" 的所有 A 股。
3.  分析过程中的"正在搜索新闻..."等状态能实时在前端显示。
