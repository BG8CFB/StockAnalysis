# 第二阶段实施计划：市场数据与仪表盘 (Phase 2: Market Data & Dashboard)

## 1. 阶段目标
本阶段重点是构建系统的"血液系统"——**行情中心 (Market Center)**，并将其可视化展示在 **仪表盘 (Dashboard)** 上。
我们将接入多源数据（A股/港股/美股），建立自动化数据同步管道，并实现数据的标准化存储。

## 2. 模块化设计 (Module Specification)

### 2.1 新增模块：`modules/market`
*   **职责**: 负责所有市场数据的采集、清洗、存储和查询。
*   **关键服务**: `UnifiedStockService`, `DataFlowManager`
*   **数据源**: Tushare, AkShare, YFinance (Yahoo)

### 2.2 新增模块：`modules/dashboard`
*   **职责**: 作为系统首页，聚合展示核心指标。
*   **特点**: 不直接连接数据库，而是作为 "Aggregator" 调用其他模块的服务。

## 3. 详细执行步骤 (Task Breakdown)

### 步骤 1: 市场数据基础设施 (Backend - Market Infrastructure)
*   [ ] **数据源适配器 (Providers)**:
    *   在 `modules/market/providers/` 下实现 `TushareProvider` (A股)。
    *   实现 `AkShareProvider` (A股备用/免费)。
    *   实现 `YFinanceProvider` (港美股)。
    *   **测试**: 为每个 Provider 编写单元测试，验证数据格式统一性。
*   [ ] **统一数据模型**: 定义 `MarketQuote` 和 `KLineData` Pydantic 模型，屏蔽不同数据源的字段差异。
*   [ ] **智能路由服务**: 实现 `UnifiedStockService`，根据股票代码 (`600519` vs `AAPL`) 自动分发请求到对应的 Provider。

### 步骤 2: 实时行情与K线接口 (Backend - API)
*   [ ] **行情接口**: 实现 `GET /api/market/quotes`，支持多市场、多股票批量查询。
*   [ ] **K线接口**: 实现 `GET /api/market/kline/{code}`，支持日/周/月线。
*   [ ] **缓存层**: 引入 Redis 缓存热点行情数据 (TTL 5秒)。
*   [ ] **历史数据同步**: 实现"懒加载"机制——当用户请求某只股票K线时，若数据库缺失，自动触发增量同步。

### 3. 仪表盘聚合服务 (Backend - Dashboard)
*   [ ] **聚合接口**: 在 `modules/dashboard/service.py` 中实现 `get_market_overview`。
*   [ ] **指数数据**: 集成上证、恒生、纳斯达克三大指数的实时行情。
*   [ ] **资产概览 (Mock)**: 由于交易模块尚未开发，暂时返回 Mock 的资产数据供前端展示。

### 步骤 4: 前端行情中心开发 (Frontend - Market Center)
*   [ ] **行情表格组件**: 使用 Naive UI / AntDV Table 展示多市场股票列表。
*   [ ] **K线图表组件**: 集成 `TradingView Lightweight Charts` 或 `ECharts`，实现交互式K线图。
*   [ ] **搜索组件**: 实现股票代码联想搜索 (`debounce` 机制)。

### 步骤 5: 前端仪表盘开发 (Frontend - Dashboard)
*   [ ] **概览卡片**: 展示三大指数涨跌幅。
*   [ ] **自动刷新**: 使用 `useInterval` 或 SSE 实现每 5 秒刷新一次行情。

## 4. 验收标准
1.  输入 `600519` 能看到贵州茅台的 K 线，输入 `AAPL` 能看到苹果的 K 线。
2.  断开 Tushare 网络（模拟故障），系统能自动降级使用 AkShare。
3.  仪表盘能实时跳动显示上证指数。
4.  **测试要求**: 核心数据源 Provider 测试覆盖率 100%。
