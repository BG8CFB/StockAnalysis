# 00_SYSTEM_OVERVIEW.md

# TradingAgents-CN 系统总览与开发指南

## 1. 项目简介
TradingAgents-CN 是一个基于 AI Agent 的智能股票分析与交易模拟系统。它集成了多源数据采集（A股/港股/美股）、智能体分析（新闻/基本面/技术面）、模拟交易和选股器功能。

对于初级工程师来说，可以将本系统理解为：**一个带有 AI 大脑的量化投研平台**。

### 1.1 新人阅读路径 (Learning Path)
如果你是刚加入团队的初级工程师，建议按照以下顺序阅读文档：

1.  **先看全局**: 阅读本文件 (`00_SYSTEM_OVERVIEW`)，了解系统长什么样，代码在哪。
2.  **再看数据**: 阅读 `02_MARKET`，因为数据是系统的血液，不理解数据来源就无法做分析。
3.  **接着看核心**: 阅读 `03_ANALYSIS`，了解 AI 是怎么工作的。
4.  **最后看应用**: 阅读 `04_SCREENER` 和 `05_TRADING`，了解上层业务功能。

---

## 2. 模块化架构 (Modular Architecture)

系统采用经典的分层架构，数据流向清晰，便于维护和扩展。

```mermaid
graph TD
    Client[前端 (Vue3/Vite)] -->|HTTP/WebSocket| API[接口层 (FastAPI)]
    
    subgraph "后端核心 (Backend Core)"
        API --> Service[业务逻辑层 (Services)]
        Service --> Model[数据模型层 (Models)]
        Service --> Agent[智能体层 (Agents)]
    end
    
    subgraph "数据与基础设施 (Infrastructure)"
        Service --> DataFlow[数据采集层 (DataFlows)]
        DataFlow -->|API| Tushare[Tushare Pro]
        DataFlow -->|Spider| AkShare[AkShare]
        DataFlow -->|API| YFinance[Yahoo Finance]
        
        Service --> DB[(MongoDB)]
        Service --> Cache[(Redis)]
    end
```

### 2.1 核心模块划分

| 模块名称 | 对应文档 | 核心功能 | 对应代码目录 |
| :--- | :--- | :--- | :--- |
| **仪表盘** | 01_DASHBOARD | 全局概览、资产聚合 | `app/routers/dashboard.py` |
| **行情中心** | 02_MARKET | K线、实时报价、数据采集 | `tradingagents/dataflows` |
| **AI分析** | 03_ANALYSIS | 智能体调度、报告生成 | `app/services/analysis_service.py` |
| **选股器** | 04_SCREENER | 条件选股、数据库筛选 | `app/services/screening_service.py` |
| **交易终端** | 05_TRADING | 模拟撮合、账户管理 | `app/routers/paper.py` |
| **用户设置** | 06_SETTINGS | 权限、配额、API Key管理 | `app/routers/system_config.py` |

---

## 3. 代码目录导航 (Code Navigation)

初级工程师在进行开发时，请遵循以下目录规范：

*   **`app/` (Web 服务端)**
    *   `routers/`: **接口层**。这里存放所有的 API 接口定义。如果你要新增一个 URL，请在这里修改。
    *   `services/`: **业务层**。这里写具体的业务逻辑，比如“怎么计算收益率”、“怎么调度 Agent”。不要在 routers 里写复杂逻辑。
    *   `models/`: **模型层**。这里定义数据库表结构 (Pydantic Models)。如果你要给用户表加个字段，改这里。
    *   `worker/`: **后台任务**。这里存放耗时的异步任务，比如“每天凌晨同步全市场数据”。

*   **`tradingagents/` (AI 与数据核心)**
    *   `agents/`: **智能体定义**。`StockAnalysis.yaml` 定义了 Agent 的人设和 Prompt。
    *   `dataflows/`: **数据管道**。
        *   `providers/`: 具体的数据源实现（Tushare, AkShare, YFinance）。
        *   `stock_data_service.py`: 统一的数据获取入口。

---

## 4. 初级工程师开发指南 (Developer Guide)

### 4.1 场景一：我要新增一个 API 接口
**步骤**：
1.  **定义数据模型**：在 `app/models/` 下找到对应文件（或新建），定义 Request 和 Response 的结构。
2.  **编写业务逻辑**：在 `app/services/` 下编写具体的函数。
3.  **暴露接口**：在 `app/routers/` 下新建路由，调用 Service 层函数，并定义 URL 路径。

### 4.2 场景二：我要修改数据库结构
**步骤**：
1.  **修改 Model**：在 `app/models/` 中修改 Pydantic 模型。
2.  **数据迁移**：由于 MongoDB 是无模式的（Schema-less），通常不需要像 SQL 那样写迁移脚本。但你需要确保新代码能兼容旧数据（使用 `Optional` 字段或默认值）。

### 4.3 场景三：我要调试数据源
**技巧**：
*   不要直接运行整个庞大的 Web 服务。
*   在 `examples/` 目录下有很多独立的脚本（如 `tushare_demo.py`），你可以复制一个，修改后单独运行，测试数据源是否正常。

---

## 5. 技术栈说明
*   **语言**: Python 3.10+
*   **Web框架**: FastAPI (高性能、自动生成文档)
*   **数据库**: MongoDB (主库), Redis (缓存/队列)
*   **AI框架**: OpenAI SDK (适配多种大模型)
*   **数据源**: Tushare Pro, AkShare, YFinance
