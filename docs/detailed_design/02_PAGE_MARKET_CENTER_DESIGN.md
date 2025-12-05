# 02_PAGE_MARKET_CENTER_DESIGN.md

# 前端页面设计：行情中心 (Market Center)

## 1. 概述

行情中心是用户查看股票实时行情、历史走势和基础数据的核心页面。它不仅展示数据，更是系统底层 **数据采集与管理系统** (`tradingagents/dataflows`) 的前端呈现。

**核心能力**：
系统不仅支持A股，还基于 `UnifiedStockService` 实现了对 **港股 (HK)** 和 **美股 (US)** 的全覆盖，数据源自动降级和补全。

---

## 2. 页面功能模块详解

### 2.1 多市场行情列表 (Multi-Market Quotes)
*   **Tabs 分组**：`A股` / `港股` / `美股` / `自选`。
*   **字段差异化**：
    *   **A股**：显示代码 (600519)、涨跌幅、换手率、PE-TTM。
    *   **港股**：显示代码 (00700.HK)、市值 (HKD)、52周高低。
    *   **美股**：显示代码 (AAPL)、盘前/盘后价格、市值 (USD)。
*   **数据流**：
    *   前端调用 `GET /api/markets/quotes?market=HK`。
    *   后端根据市场类型分发给 `ChinaStockService` 或 `ForeignStockService`。

### 2.2 K线走势图 (Interactive Chart)
*   **功能描述**：展示股票的历史价格走势，支持日K、周K、月K及分钟线。
*   **技术实现**：
    *   前端：TradingView 组件。
    *   后端：`GET /api/stocks/{code}/kline`。
*   **数据补全逻辑**：
    *   如果请求的是美股 `NVDA` 的日线：
    *   1. 查 MongoDB `market_quotes_us` 表。
    *   2. 发现数据只到昨天 -> 实时调用 `YFinance` 补全今日数据 -> 返回合并结果。

---

## 3. 核心逻辑设计 (Backend Logic)

### 3.1 多市场数据源架构 (Multi-Market Data Source Architecture)

系统针对不同市场采用了最优的数据源组合策略，所有策略均在 `tradingagents/dataflows/providers` 中实现。

#### A. 中国A股 (China A-Shares)
*   **策略**: **备份制度 (Failover)**。即采用串行降级策略，而非并行获取。
*   **优先级**:
    1.  **Tushare Pro** (API): 
        *   *优势*: 数据规范，包含复权因子、财务指标。
        *   *限制*: 需要积分/Token。
        *   *代码*: `providers/china/tushare.py`
    2.  **AkShare** (Scraper):
        *   *优势*: 免费，接口丰富（东方财富源）。
        *   *触发条件*: Tushare Token 无效、配额耗尽或接口超时。
        *   *代码*: `providers/china/akshare.py`
    3.  **Baostock**:
        *   *用途*: 仅用于补充超长历史周期的日线数据。
*   **入库逻辑**:
    *   无论来自哪个源，数据经过 `_standardize_data()` 标准化后，统一使用 `Upsert` (按 `code` + `date` 唯一索引) 写入 MongoDB `market_quotes` 集合。

#### B. 港股 (Hong Kong Stocks)
*   **策略**: **混合模式 (Hybrid)**。不同类型的数据使用不同的源。
*   **数据源分工**:
    1.  **行情数据 (Quotes/KLine)**: 
        *   首选 **YFinance** (`_get_hk_quote_from_yfinance`)。
        *   备选 **AkShare**。
    2.  **财务数据 (Financials)**:
        *   使用 **Tushare** (`hk_income`, `hk_balance`) 接口，因为 Yahoo 的财务数据格式难以标准化。

#### C. 美股 (US Stocks)
*   **策略**: **单一主源 + 辅助源**。
*   **优先级**:
    1.  **YFinance**:
        *   *用途*: 核心数据源，获取实时行情、历史K线。
    2.  **Finnhub**:
        *   *用途*: 获取公司基本面信息（行业、CEO、员工数）。

### 3.2 自动识别与路由 (Auto-Routing)
后端 `UnifiedStockService` 实现了智能路由：
*   输入 `600519` -> 路由至 **A股管道** -> 检查 Tushare Token。
*   输入 `00700` 或 `00700.HK` -> 路由至 **港股管道** -> 调用 Yahoo。
*   输入 `TSLA` -> 路由至 **美股管道** -> 调用 Yahoo。

---

## 4. 📂 代码导航 (Code Navigation)

*   **数据采集核心 (DataFlows)**:
    *   `tradingagents/dataflows/data_source_manager.py`: 总指挥，决定用哪个数据源。
    *   `tradingagents/dataflows/providers/`: 这里存放了所有数据源的具体实现代码。
        *   `china/tushare.py`: Tushare 适配器。
        *   `us/yfinance.py`: Yahoo Finance 适配器。

*   **Web 接口 (Routers)**:
    *   `app/routers/stocks.py`: A股相关接口。
    *   `app/routers/multi_market_stocks.py`: 港美股相关接口（正在逐步统一到这里）。

*   **业务服务 (Services)**:
    *   `app/services/unified_stock_service.py`: 统一对外的股票服务，封装了底层的 DataFlows。

---

## 5. 🚀 初级开发指南 (Developer Guide)

**任务：Tushare 的某个接口改名了，导致报错，怎么修？**

1.  **Step 1: 定位文件**
    *   去 `tradingagents/dataflows/providers/china/tushare.py`。

2.  **Step 2: 查找函数**
    *   找到调用该接口的函数（例如 `get_daily_data`）。

3.  **Step 3: 修改参数**
    *   修改 `ts.pro_api().daily(...)` 中的参数名。

4.  **Step 4: 本地测试**
    *   不要启动整个后端。
    *   创建一个 `test_tushare.py`，手动实例化 `TushareProvider` 并调用该方法，打印结果看是否正常。

**任务：我想添加一个新的数据源（比如新浪财经）**

1.  在 `tradingagents/dataflows/providers/china/` 下新建 `sina.py`。
2.  继承 `BaseStockDataProvider` 类。
3.  实现 `get_kline` 等标准方法。
4.  在 `data_source_manager.py` 中注册这个新 Provider。

---

## 6. 接口设计 (API Specification)

### 6.1 获取多市场行情列表
*   **URL**: `/api/markets/{market}/stocks`
*   **Method**: `GET`
*   **功能**: 获取指定市场的股票列表（分页）。
*   **Request Params**:
    *   `market` (path): `CN` | `HK` | `US`
    *   `page` (query): 页码 (default: 1)
    *   `limit` (query): 每页数量 (default: 20)
    *   `sort_by` (query): `pct_chg` | `turnover` | `amount`
*   **Response**:
    ```json
    {
      "total": 5000,
      "items": [
        {
          "symbol": "00700",
          "name": "腾讯控股",
          "price": 320.4,
          "pct_chg": 1.52,
          "market_cap": 3050000000000,
          "turnover": 50000000
        }
      ]
    }
    ```

### 6.2 获取个股实时行情
*   **URL**: `/api/stocks/{code}/quote`
*   **Method**: `GET`
*   **功能**: 获取单只股票的最新报价（实时性高）。
*   **Request Params**:
    *   `code`: `00700` (自动识别)
    *   `force_refresh`: `true` (跳过 Redis 缓存，强制调 API)
*   **Implementation Logic**:
    1.  调用 `_detect_market_and_code(code)`。
    2.  若 `force_refresh=false`，先查 Redis `quote:{market}:{code}`。
    3.  若未命中，根据 Market 调用对应 Provider (YFinance/Tushare)。
    4.  结果写入 Redis (TTL: 10s) 并返回。

### 6.3 获取K线数据
*   **URL**: `/api/markets/{market}/stocks/{code}/daily`
*   **Method**: `GET`
*   **功能**: 获取历史K线数据，用于前端绘制图表。
*   **Request Params**:
    *   `start_date`: `2023-01-01`
    *   `end_date`: `2023-12-31`
    *   `limit`: `200`
*   **Response**:
    ```json
    {
      "data": {
        "code": "00700",
        "quotes": [
          { "trade_date": "2023-01-01", "open": 300, "close": 305, "high": 310, "low": 295, "volume": 100000 }
        ]
      }
    }
    ```
*   **Implementation Logic**:
    1.  查询 MongoDB `market_quotes_{market}` 集合。
    2.  检查返回数据的最新日期 `last_db_date`。
    3.  若 `last_db_date < today`，触发**增量同步**：
        *   调用 Provider 获取 `last_db_date` 到 `today` 的数据。
        *   `Upsert` 入库。
        *   将新数据追加到 DB 结果中返回。

---

## 7. 数据存储设计 (Database Schema)

### 7.1 基础信息表
*   `stock_basic_info` (A股): `{ "code": "000001", "name": "平安银行", "industry": "银行", "area": "深圳" }`
*   `stock_basic_info_us` (美股): `{ "symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics" }`
*   `stock_basic_info_hk` (港股): `{ "symbol": "00700", "name": "Tencent", "lot_size": 100 }`

### 7.2 行情数据表
*   `market_quotes`: A股日线。
*   `market_quotes_us`: 美股日线。
*   `market_quotes_hk`: 港股日线。
*   **索引**: `{ "code": 1, "trade_date": -1 }` (复合唯一索引)。
