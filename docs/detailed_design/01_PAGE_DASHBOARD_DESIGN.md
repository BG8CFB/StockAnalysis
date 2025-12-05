# 01_PAGE_DASHBOARD_DESIGN.md

# 前端页面设计：仪表盘 (Dashboard)

## 1. 概述

仪表盘是 TradingAgents-CN 系统的首页和指挥中心。它不仅是一个数据展示面板，更是连接市场行情、用户资产、分析任务和系统状态的聚合枢纽。

**核心类与服务**：
*   **入口服务**: `DashboardService` (逻辑层聚合，暂未实现独立文件，目前逻辑分散在各个 Router 中，建议后续重构)
*   **数据源**: `StockDataService` (行情), `PaperTradingService` (资产), `AnalysisService` (任务)

---

## 2. 页面功能模块详解

### 2.1 市场概览面板 (Market Overview)
*   **功能描述**：展示核心指数的实时行情。
*   **支持的指数**:
    *   **A股**: 上证指数 (`000001.SH`), 深证成指 (`399001.SZ`), 创业板指 (`399006.SZ`)。
    *   **港股**: 恒生指数 (`^HSI`)。
    *   **美股**: 纳斯达克 (`^IXIC`), 标普500 (`^GSPC`)。
*   **数据流**:
    *   前端并发调用 `GET /api/stocks/{index_code}/quote`。
    *   对于 `^HSI` (港股指数)，后端通过 `YFinance` 获取实时点位。

### 2.2 资产概览面板 (Asset Summary)
*   **功能描述**：展示用户模拟交易账户的整体资产状况。
*   **展示要素**：
    *   **总资产**: 动态聚合 `CNY + HKD(折算) + USD(折算)`。
    *   **多币种明细**: 
        *   🇨🇳 CNY 现金余额
        *   🇭🇰 HKD 现金余额
        *   🇺🇸 USD 现金余额
    *   **持仓分布**: 当前持仓股票数量及市值占比。
*   **数据流**:
    *   调用 `GET /api/paper/account` 获取多币种账户详情。

### 2.3 智能分析任务监控 (Analysis Task Monitor)
*   **功能描述**：实时追踪当前正在运行的 AI 分析任务。
*   **展示要素**：
    *   任务列表：显示最近 5 个任务。
    *   状态徽章：`PENDING` (排队中), `PROCESSING` (分析中), `COMPLETED` (完成), `FAILED` (失败)。
    *   进度条：0-100% 动态进度。
*   **交互逻辑**：
    *   点击任务可跳转至 `AI分析实验室` 查看详情。

---

## 3. 核心逻辑设计 (Backend Logic)

### 3.1 数据聚合层 (Aggregation Layer)
仪表盘的数据并非来自单一表，而是由后端聚合多个模块的数据：

1.  **并行获取**：
    *   Thread 1 -> `StockDataService.get_indices_snapshot()`
    *   Thread 2 -> `PaperTradingService.get_account_summary(user_id)`
    *   Thread 3 -> `AnalysisService.get_recent_tasks(user_id)`
2.  **汇率换算**:
    *   调用 `CurrencyService` 获取实时汇率 (USD/CNY, HKD/CNY)，将外币资产折算为 CNY 显示总资产。

### 3.2 实时性设计
*   **轮询 (Polling)**：
    *   前端每 5-10 秒调用一次 `GET /api/dashboard/summary`。
*   **SSE (Server-Sent Events)**:
    *   系统支持 SSE 推送 (`app/routers/sse.py`)，可订阅 `market_ticks` 事件实现毫秒级更新。

---

## 4. 📂 代码导航 (Code Navigation)

对于初级工程师，本模块涉及以下关键文件：

*   **接口定义 (Controller)**:
    *   `app/routers/stocks.py`: 获取市场指数行情。
    *   `app/routers/paper.py`: 获取用户资产信息。
    *   `app/routers/analysis.py`: 获取最近任务状态。
    *   *注：目前没有独立的 `dashboard.py`，数据由前端分别调用上述接口组装。*

*   **数据模型 (Model)**:
    *   `app/models/stock_models.py`: 定义行情数据结构。
    *   `app/models/user.py`: 定义用户关联信息。

---

## 5. 🚀 初级开发指南 (Developer Guide)

**任务：我想给仪表盘增加一个“系统公告”栏，该怎么做？**

1.  **Step 1: 定义数据模型**
    *   在 `app/models/` 下新建 `announcement.py` (或复用现有文件)。
    *   定义 `class Announcement(BaseModel): title: str, content: str, ...`。

2.  **Step 2: 创建数据库集合**
    *   MongoDB 不需要提前建表，直接在 Service 层写入即可自动创建。

3.  **Step 3: 编写接口**
    *   在 `app/routers/system_config.py` 中添加 `GET /api/system/announcements`。
    *   实现逻辑：`db.announcements.find().sort("date", -1).limit(1)`。

4.  **Step 4: 前端调用**
    *   前端调用该接口，将返回的 JSON 显示在仪表盘顶部。

---

## 6. 数据存储设计 (Database Schema)

### 6.1 用户资产表 (`paper_accounts`)
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "cash": {
    "CNY": 50000.0,
    "HKD": 100000.0,
    "USD": 5000.0
  },
  "realized_pnl": {
    "CNY": 1200.0,
    "HKD": -50.0,
    "USD": 0.0
  },
  "updated_at": ISODate("...")
}
```

### 6.2 任务状态表 (`analysis_tasks`)
```javascript
{
  "_id": ObjectId("..."),
  "task_id": "uuid-...",
  "user_id": ObjectId("..."),
  "market": "CN",
  "stock_code": "600519",
  "status": "PROCESSING", // PENDING, PROCESSING, COMPLETED, FAILED
  "progress": 45,         // 0-100
  "current_step": "analyzing_financials",
  "created_at": ISODate("...")
}
```

---

## 7. 接口设计 (API Specification)

### 7.1 获取仪表盘聚合数据
*   **URL**: `/api/dashboard/summary`
*   **Method**: `GET`
*   **Response**:
    ```json
    {
      "market_indices": [
        { "symbol": "000001.SH", "name": "上证指数", "price": 3050.12, "change_pct": 0.52 },
        { "symbol": "^IXIC", "name": "纳斯达克", "price": 14000.50, "change_pct": -0.20 }
      ],
      "assets": {
        "total_value_cny": 105000.00,
        "cash_breakdown": { "CNY": 50000, "USD": 2000, "HKD": 10000 }
      },
      "active_tasks": [
        { "task_id": "uuid-123", "stock": "TSLA", "status": "PROCESSING", "progress": 45 }
      ]
    }
    ```
