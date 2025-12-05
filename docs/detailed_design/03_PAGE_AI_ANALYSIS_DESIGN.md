# 03_PAGE_AI_ANALYSIS_DESIGN.md

# 前端页面设计：AI 分析实验室 (AI Analysis Lab)

## 1. 概述

AI 分析实验室是系统的核心业务板块，基于 `AnalysisService` 和 `UniversalAgent`。用户在此发起针对特定股票（支持 A股/港股/美股）的深度分析请求。

**核心类与服务**：
*   **核心服务**: `app.services.analysis_service.AnalysisService`
*   **智能体SDK**: `tradingagents.agents.openai_agents_sdk.OpenAIAgent`
*   **异步队列**: `BackgroundTasks` (FastAPI原生) + `asyncio.create_task` (批量并发)

---

## 2. 页面功能模块详解

### 2.1 分析请求发起 (Request Launcher)
*   **智能代码输入**：
    *   支持输入 `AAPL` (美股)、`00700` (港股)、`600519` (A股)。
    *   前端自动调用 `/api/markets/search` 提示候选股票。
*   **智能体选择器**：
    *   `财经新闻分析师`: 侧重市场情绪和新闻事件。
    *   `基本面分析师`: 侧重财务报表（支持 Tushare 港股财务数据）。
    *   `技术面分析师`: 侧重 K 线形态（支持 YFinance 数据）。
*   **分析模式**：
    *   **快速模式**: 仅分析最近 7 天数据。
    *   **深度模式**: 分析最近 30-90 天数据，消耗更多配额。

### 2.2 实时推理流 (Live Inference Stream)
*   **功能描述**：通过 WebSocket 或 SSE (`/api/sse/events`) 展示 AI 的思考步骤。
*   **可视化步骤**:
    1.  `[System]` 识别到股票 `TSLA` (美股)。
    2.  `[Agent]` 正在调用 `get_stock_news(TSLA)`...
    3.  `[Tool]` 成功获取 15 条 Yahoo Finance 新闻。
    4.  `[Agent]` 正在分析新闻情感...
    5.  `[Agent]` 生成最终报告。

---

## 3. 核心逻辑设计 (Backend Logic)

### 3.1 智能体与工具链 (Agents & Tools)

#### A. 智能体配置
智能体行为由 `tradingagents/agents/StockAnalysis.yaml` 定义。
*   **Role**: 定义了 Agent 的人设（如“严谨的财务专家”）。
*   **Prompt**: 定义了分析框架（如“先看营收，再看利润，最后看现金流”）。

#### B. 工具自动适配 (Context-Aware Tools)
智能体调用的工具（如 `get_stock_price`）具有**市场感知能力**：
*   当 Agent 分析 **A股** 时：工具底层调用 `Tushare/AkShare`。
*   当 Agent 分析 **港股** 时：工具底层调用 `YFinance` 获取价格，调用 `Tushare` 获取财报 (`hk_income` 接口)。
*   当 Agent 分析 **美股** 时：工具底层调用 `Finnhub` 获取基本面。

### 3.2 异步任务状态机
由于跨国数据获取较慢，任务流程设计如下：
1.  **提交**: `POST /api/analysis/create` -> 返回 `task_id`。
2.  **状态流转**:
    *   `PENDING`: 任务创建，等待调度。
    *   `PROCESSING`: 正在执行（细分为 `data_preparation`, `analysis`, `report_generation` 步骤）。
    *   `COMPLETED`: 分析完成，结果已入库。
    *   `FAILED`: 发生不可恢复错误。
3.  **执行**: `AnalysisService._execute_analysis_background` 负责实际执行。

---

## 4. 📂 代码导航 (Code Navigation)

*   **智能体定义 (Agent Definitions)**:
    *   `tradingagents/agents/StockAnalysis.yaml`: **核心配置文件**。在这里修改 Agent 的 Prompt 和角色设定。
    *   `tradingagents/agents/universal_agent.py`: 读取 YAML 并初始化 Agent 的代码。

*   **业务逻辑 (Service)**:
    *   `app/services/analysis_service.py`: 整个分析流程的总控代码。负责任务创建、状态更新、结果保存。

*   **接口层 (Router)**:
    *   `app/routers/analysis.py`: 接收前端请求，启动后台任务。

---

## 5. 🚀 初级开发指南 (Developer Guide)

**任务：我想修改“财经新闻分析师”的 Prompt，让他更关注负面新闻。**

1.  **Step 1: 找到配置文件**
    *   打开 `tradingagents/agents/StockAnalysis.yaml`。

2.  **Step 2: 定位角色**
    *   搜索 `slug: financial-news-analyst`。

3.  **Step 3: 修改 roleDefinition**
    *   在 `roleDefinition` 字段中添加：“请特别关注可能导致股价下跌的负面新闻，如诉讼、监管罚款等。”

4.  **Step 4: 重启服务**
    *   修改 YAML 文件通常不需要重启，因为 `universal_agent.py` 每次任务都会重新加载配置（或有缓存机制）。

**任务：我想新增一个“宏观经济分析师”**

1.  在 `StockAnalysis.yaml` 中新增一个 entry：
    ```yaml
    - slug: macro-analyst
      name: 宏观经济分析师
      roleDefinition: 你是一个宏观经济专家...
    ```
2.  前端在调用 `/api/analysis/create` 时，`analysts` 参数传入 `["macro-analyst"]` 即可。

---

## 6. 接口设计 (API Specification)

### 6.1 提交分析
*   **URL**: `/api/analysis/single` (POST)
*   **Request Body**:
    ```json
    {
      "symbol": "AAPL",
      "parameters": {
        "research_depth": "deep", // quick, deep
        "analysts": ["market", "fundamental"]
      }
    }
    ```

### 6.2 获取任务状态
*   **URL**: `/api/analysis/tasks/{task_id}/status`
*   **Method**: `GET`
*   **Response**:
    ```json
    {
      "status": "PROCESSING",
      "progress": 45,
      "current_step": "analyzing_financials",
      "message": "正在分析财务报表..."
    }
    ```

### 6.3 获取分析结果
*   **URL**: `/api/analysis/tasks/{task_id}/result`
*   **Method**: `GET`
*   **Response**:
    ```json
    {
      "summary": "...",
      "full_report": "...",
      "recommendation": "BUY",
      "decision": { "action": "buy", "target_price": 180.0 }
    }
    ```

---

## 7. 数据存储设计 (Database Schema)

### 7.1 任务追踪表 (`analysis_tasks`)
```javascript
{
  "_id": ObjectId("..."),
  "task_id": "uuid-...",
  "user_id": ObjectId("..."),
  "market": "CN",
  "stock_code": "600519",
  "status": "PROCESSING",
  "progress": 30,
  "current_step": "fetching_data",
  "started_at": ISODate("..."),
  "completed_at": null,
  "error": null
}
```

### 7.2 分析结果表 (`analysis_results`)
```javascript
{
  "_id": ObjectId("..."),
  "task_id": "uuid-...",
  "analysis_id": "uuid-...", // 冗余ID
  "stock_symbol": "600519",
  "full_report": "# 贵州茅台分析报告\n\n## 财务分析...", // Markdown
  "summary": "公司基本面稳健...",
  "recommendation": "BUY", // BUY, HOLD, SELL
  "confidence_score": 0.85,
  "risk_level": "low",
  "data_sources": ["Tushare", "AkShare"],
  "created_at": ISODate("...")
}
```
