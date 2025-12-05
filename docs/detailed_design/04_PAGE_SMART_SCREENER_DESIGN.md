# 04_PAGE_SMART_SCREENER_DESIGN.md

# 前端页面设计：智能选股器 (Smart Screener)

## 1. 概述

智能选股器是系统的“流量入口”，允许用户基于基本面、技术面和市场面指标快速圈定目标股票池。系统采用 **"宽表预计算" + "数据库原生筛选"** 的架构，确保在百万级数据量下实现毫秒级响应。

**核心类与服务**：
*   **入口服务**: `app.services.enhanced_screening_service.EnhancedScreeningService` (负责路由策略，决定是用数据库查还是内存算)
*   **底层实现**: `app.services.database_screening_service.DatabaseScreeningService` (MongoDB 聚合查询)
*   **数据同步**: `app.services.basics_sync_service` (负责维护宽表)

---

## 2. 页面功能模块详解

### 2.1 策略构建器 (Strategy Builder)
*   **动态字段加载**:
    *   API: `GET /api/screening/fields`
    *   前端根据返回的 metadata 渲染输入控件（数字范围、下拉选择）。
*   **逻辑组合**:
    *   支持多条件 `AND` 组合。
    *   示例：`行业 = 银行` AND `PE_TTM < 10` AND `股息率 > 5%`。

### 2.2 行业热力图与筛选 (Industry Filter)
*   **数据源**:
    *   API: `GET /api/screening/industries`
    *   逻辑：聚合 `stock_basic_info` 表，按 `industry` 分组统计股票数量。

### 2.3 筛选结果列表 (Results Table)
*   **展示**: 代码、名称、以及**所有参与筛选的指标值**（如筛选了 PE，列中必须显示 PE）。
*   **交互**:
    *   **一键分析**: 选中股票 -> `POST /api/analysis/batch`。
    *   **加入自选**: 选中股票 -> `PUT /api/favorites/{code}`。

---

## 3. 核心逻辑设计 (Backend Logic)

### 3.1 宽表预计算架构 (Wide-Table Pre-computation)
为了避免筛选时进行复杂的连表查询（Join），系统维护了一张超级宽表 `stock_basic_info`。

*   **什么是宽表？**
    *   传统设计：`基础信息表` (代码, 名称) + `财务表` (代码, PE) + `行情表` (代码, 收盘价)。筛选时需要 Join 3张表，慢。
    *   宽表设计：`stock_basic_info` (代码, 名称, PE, 收盘价)。所有字段都在一张表里，查起来飞快。

*   **维护机制**:
    *   **每日定时任务** (`00:00`): `MultiSourceBasicsSyncService` 运行。
    *   **数据聚合**:
        1.  从 Tushare/AkShare 拉取基础信息 (Code, Name, Industry)。
        2.  从 `market_quotes` 获取最新收盘价、涨跌幅、成交量。
        3.  从 `financial_data` 获取最新 PE, PB, ROE。
    *   **落库**: 将所有字段打平存入 `stock_basic_info` 文档中。

### 3.2 筛选引擎实现 (Screening Engine)
`DatabaseScreeningService` 负责将前端 JSON 条件转换为 MongoDB Aggregation Pipeline。

**条件转换逻辑**:
*   Frontend: `{ "field": "pe_ttm", "op": "lt", "value": 20 }`
*   Backend (`_build_match_stage`):
    ```python
    # 映射表
    OPS = {
        "lt": "$lt", "gt": "$gt", "lte": "$lte", "gte": "$gte",
        "eq": "$eq", "in": "$in", "between": "special_handling"
    }
    # 转换结果
    { "pe_ttm": { "$lt": 20 } }
    ```

**执行流程**:
1.  **构建 Match Stage**: 组合所有过滤条件。
2.  **构建 Sort Stage**: 处理排序 (e.g., `{ "market_cap": -1 }`)。
3.  **构建 Project Stage**: 仅返回需要的字段（减少网络传输）。
4.  **执行 Aggregate**: `db.stock_basic_info.aggregate([match, sort, skip, limit, project])`。

---

## 4. 📂 代码导航 (Code Navigation)

*   **服务层 (Services)**:
    *   `app/services/database_screening_service.py`: **核心筛选逻辑**。包含了如何把 JSON 转成 MongoDB Query 的代码。
    *   `app/services/enhanced_screening_service.py`: 上层封装，未来可能加入内存筛选（Pandas），目前主要调用 DatabaseService。

*   **接口层 (Router)**:
    *   `app/routers/screening.py`: 接收筛选请求。

*   **数据同步 (Worker)**:
    *   `app/services/basics_sync_service.py`: 负责把各个表的数据凑到一起，更新 `stock_basic_info` 宽表。

---

## 5. 🚀 初级开发指南 (Developer Guide)

**任务：我想新增一个筛选字段“股息率 (dividend_yield)”，该怎么做？**

1.  **Step 1: 确认数据源**
    *   先确认 `stock_basic_info` 表里有没有 `dividend_yield` 字段。
    *   如果没有，需要修改 `basics_sync_service.py`，在每日同步时从 Tushare 拉取该字段并存入。

2.  **Step 2: 注册字段元数据**
    *   打开 `app/constants/screening_fields.py` (假设有这个文件，或在 `screening.py` 中的 `get_screening_fields` 函数)。
    *   添加：
        ```python
        "dividend_yield": {
            "name": "股息率",
            "type": "number",
            "unit": "%",
            "category": "financial"
        }
        ```

3.  **Step 3: 重启服务**
    *   前端调用 `/api/screening/fields` 时就能看到新字段了。
    *   由于我们用的是动态 MongoDB 查询，后端筛选逻辑**不需要**修改代码，它会自动识别 `dividend_yield` 并生成 `{ "dividend_yield": { "$gt": ... } }`。

---

## 6. 接口设计 (API Specification)

### 6.1 获取筛选字段配置
*   **URL**: `/api/screening/fields`
*   **Method**: `GET`
*   **Response**:
    ```json
    {
      "fields": {
        "pe_ttm": { "label": "市盈率(TTM)", "type": "number", "unit": "倍", "min": 0, "max": 500 },
        "roe": { "label": "净资产收益率", "type": "number", "unit": "%", "min": -100, "max": 100 },
        "industry": { "label": "行业", "type": "string", "options": ["银行", "白酒", ...] }
      },
      "groups": {
        "基本面": ["pe_ttm", "pb", "roe", "revenue_growth"],
        "行情": ["market_cap", "pct_chg", "turnover_rate"]
      }
    }
    ```

### 6.2 执行筛选
*   **URL**: `/api/screening/run`
*   **Method**: `POST`
*   **Request Body**:
    ```json
    {
      "conditions": [
        { "field": "industry", "op": "in", "value": ["银行", "证券"] },
        { "field": "pe_ttm", "op": "lt", "value": 10 },
        { "field": "market_cap", "op": "gt", "value": 10000000000 } // 100亿
      ],
      "sort_by": "market_cap",
      "sort_order": "desc",
      "page": 1,
      "limit": 50
    }
    ```
*   **Response**:
    ```json
    {
      "total": 25,
      "items": [
        { "code": "601398", "name": "工商银行", "pe_ttm": 5.2, "market_cap": 2000000000000, "industry": "银行" },
        ...
      ]
    }
    ```

---

## 7. 数据存储设计 (Database Schema)

### 7.1 股票基础宽表 (`stock_basic_info`)
这是筛选器的核心依赖表。

```javascript
{
  "_id": ObjectId("..."),
  "code": "600519",          // 唯一索引
  "name": "贵州茅台",
  "industry": "白酒",        // 索引
  "area": "贵州",
  "market": "主板",
  "list_date": "2001-08-27",
  
  // --- 财务指标 (每日更新) ---
  "pe": 30.5,
  "pe_ttm": 28.4,            // 索引
  "pb": 8.2,
  "roe": 25.6,               // 索引
  "total_assets": 250000000000,
  "revenue": 120000000000,
  
  // --- 行情指标 (每日更新) ---
  "close": 1750.0,
  "pct_chg": 1.5,
  "turnover_rate": 0.8,
  "volume": 50000,
  "amount": 87500000,
  "market_cap": 2200000000000, // 索引 (总市值)
  "circ_mv": 2200000000000,    // 流通市值
  
  // --- 技术指标 (可选, 仅部分热门股预计算) ---
  "ma_5": 1740.0,
  "ma_20": 1720.0,
  "rsi_14": 65.2,
  
  "updated_at": ISODate("2023-10-27T18:00:00Z")
}
```
