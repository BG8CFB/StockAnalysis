# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**StockAnalysis** 是一个基于 **LangChain 多智能体工作流** 的股票分析平台,采用 **模块化单体架构**,支持多用户登录注册,每个用户的配置和数据完全隔离。

**核心特性**:
- TradingAgents 智能分析系统(基于 LangChain 四阶段工作流)
- MCP (Model Context Protocol) 工具集成
- 市场数据统一接入(A股/美股/港股)
- 用户数据完全隔离(MongoDB + Redis)

## 开发环境与命令

### Docker 容器化部署(推荐)

```bash
# 开发环境(热重载)
docker-compose -f docker-compose.dev.yml up -d

# 生产环境
docker-compose up -d

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
docker-compose -f docker-compose.dev.yml logs backend

# 重启服务
docker-compose -f docker-compose.dev.yml restart

# 停止服务
docker-compose -f docker-compose.dev.yml down
```

### 本地开发

```bash
# 后端
cd backend
cp .env.example .env
poetry install
poetry run uvicorn main:app --reload

# 前端
cd frontend
cp .env.example .env
npm install
npm run dev
```

### 测试与代码质量

```bash
# 后端测试
cd backend
poetry run pytest                    # 运行所有测试
poetry run pytest -v                # 详细输出
poetry run pytest --cov=modules     # 覆盖率报告
poetry run pytest tests/core/mcp/  # 运行核心模块测试

# 后端代码检查
poetry run black .                  # 代码格式化(line-length: 100)
p Poetry run ruff check .             # Lint 检查
poetry run mypy .                   # 类型检查(Python 3.11, disallow_untyped_defs: true)

# 前端
cd frontend
npm run lint                        # ESLint 检查
npm run build                       # 构建生产版本
npm run test                        # Vitest 测试
```

### 开发环境访问地址

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- MongoDB: localhost:27017
- Redis: localhost:6379

## 项目架构(大局观)

### 模块化单体架构

项目采用**模块化单体架构**:

**backend/core/** - 核心框架(非模块化部分):
- **auth/** - 认证核心(JWT、RBAC、用户模型)
- **db/** - 数据库连接(MongoDB motor + Redis)
- **ai/** - AI 基础设施(模型管理、LLM Provider、定价)
- **mcp/** - MCP 协议核心(连接池、适配器、配置管理)
- **security/** - 安全模块(滑块验证码、限流器、IP 信任)
- **settings/** - 统一设置(系统设置、用户设置)
- **market_data/** - 市场数据核心(多数据源统一接入)
- **user/** - 用户核心
- **admin/** - 管理员核心(任务清理、审计日志)

**backend/modules/** - 业务功能模块(可插拔):
- **trading_agents/** - TradingAgents 智能体分析核心(完整实现)
  - **workflow/** - 工作流调度器 + 四阶段智能体(phase1-4)
  - **manager/** - 任务管理器、批量管理、并发控制、业务服务
  - **api/** - HTTP API + WebSocket 实时推送
  - **tools/** - MCP 工具集成
  - **config/** - 智能体 YAML 配置管理
  - **models/** - 数据模型
- **screener/ask_stock/dashboard/** - 预留框架

### 前端架构

前端采用 **React 19 + TypeScript** 技术栈，按功能域组织代码：

**frontend/src/features/** - 按业务功能组织的模块目录：

- **analysis/** - 智能分析(TradingAgents)相关组件、Hooks、Schema
- **config/** - 配置管理(数据源/模型目录等)
- **dashboard/** - 仪表板功能
- **mcp/** - MCP 工具配置与管理
- **scheduler/** - 任务调度相关
- **screening/** - 智能选股
- **stocks/** - 股票相关功能

**frontend/src/pages/** - 路由级页面组件：

- 每个子目录对应一个路由页面，通常组合 `features/` 中的组件

**frontend/src/stores/** - Zustand 全局状态管理：

- **auth.store.ts** - 认证状态(Token、用户信息、自动刷新)
- **app.store.ts** - 应用级状态(主题等)
- **notification.store.ts** - 通知状态

**frontend/src/services/** - 服务端通信：

- **api/** - 各模块 API 请求函数
- **http/** - Axios 实例、拦截器、错误处理、消息引用
- **websocket/** - WebSocket 连接管理

**frontend/src/router/** - React Router v7 路由配置

**frontend/src/components/** - 通用组件：

- **charts/** - ECharts 图表封装(BarChart/KlineECharts/PieChart 等)
- **ui/** - 基础 UI 组件(ErrorBoundary、MarkdownRenderer、VirtualTable)
- **feedback/** - 反馈组件(NetworkStatus)

### 路由注册顺序

路由注册顺序很重要(backend/main.py):
1. 核心设置路由
2. 核心管理路由
3. AI 核心路由
4. 系统路由
5. 用户路由
6. 业务模块路由(Screener, AskStock, MCP, TradingAgents, MarketData)

### 用户数据隔离设计

**MongoDB 数据隔离**:
- 每个用户数据包含 `user_id` 字段
- 数据库层创建 `user_id` 索引
- 后端服务层强制校验

**Redis 缓存隔离**:
- Key 命名规范: `user:{user_id}:...`
- 示例: `user:{user_id}:session:{session_id}`

## TradingAgents 模块关键概念

TradingAgents 是基于 **LangChain** 的多阶段 AI 股票分析系统,模拟专业投资分析团队的工作模式。

### 四阶段工作流

1. **Phase 1: 信息收集与基础分析** - 并行执行6个分析师(财经新闻/社交媒体/中国市场/技术面/基本面/短线资金)
2. **Phase 2: 多空博弈与投资决策** - 看涨/看跌辩论 + 投资组合经理决策 + 专业交易员制定交易计划
3. **Phase 3: 策略风格与风险评估** - 激进/中性/保守策略并行分析 + 风险管理委员会主席审查
4. **Phase 4: 总结智能体** - 汇总所有阶段输出，生成最终投资报告与价格预测

### 并发控制机制

三层并发控制:
- **模型级**: 双模型并发槽位管理
- **任务级**: 单任务内并发控制
- **批量级**: 批量任务队列管理

### 关键组件

- **WorkflowScheduler** (`backend/modules/trading_agents/workflow/scheduler.py`) - 工作流调度器
- **TaskManager** (`backend/modules/trading_agents/manager/task_manager.py`) - 核心任务管理
- **ConcurrencyController** (`backend/modules/trading_agents/manager/concurrency_controller.py`) - 并发控制
- **智能体配置** (`backend/modules/trading_agents/config/agents/*.yaml`) - YAML 配置文件

## MCP 模块关键概念

MCP (Model Context Protocol) 是统一的工具调用协议。

### 关键组件

- **MCP 连接池** (`backend/core/mcp/pool/pool.py`) - 连接池管理
- **MCP 适配器** (`backend/core/mcp/adapter/adapter.py`) - LangChain MCP 适配器
- **默认配置** (`backend/core/mcp/config/default_config.yaml`) - 默认配置
- **MCP 服务** (`backend/core/mcp/service/mcp_service.py`) - MCP 服务器管理服务
- **健康检查** (`backend/core/mcp/service/health_checker.py`) - 定期健康检查

## 市场数据模块关键概念

多数据源统一接入,支持 A股/美股/港股。

### 关键组件

- **数据源路由器** (`backend/core/market_data/managers/source_router.py`) - 数据源路由
- **数据源适配器** (`backend/core/market_data/sources/`) - 各数据源适配器
  - **a_stock/** - A股数据源(TuShare, AkShare)
  - **us_stock/** - 美股数据源(Yahoo Finance, Alpha Vantage, AkShare)
  - **hk_stock/** - 港股数据源(Yahoo Finance, AkShare, iTick)

## 技术栈

### 后端

- **框架**: FastAPI + Python 3.11+
- **工作流引擎**: LangChain (create_agent)
- **LLM 集成**: 智谱 AI (glm-4.6), OpenAI 兼容接口
- **工具协议**: MCP (Model Context Protocol) >=1.9.2,<2.0.0
- **数据库**: MongoDB (motor) + Redis
- **认证**: JWT (python-jose) + bcrypt
- **市场数据源**: TuShare, AkShare
- **任务调度**: APScheduler
- **依赖管理**: Poetry
- **测试**: pytest + pytest-asyncio
- **代码质量**: black (line-length: 100), ruff, mypy (disallow_untyped_defs: true)

### 前端

- **框架**: React 19 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: Ant Design 6
- **状态管理**: Zustand
- **路由**: React Router v7
- **图表**: ECharts + echarts-for-react
- **表单**: React Hook Form + Zod
- **测试**: Vitest + React Testing Library

## 前端路径别名

Vite 配置中定义的路径别名:
- `@/` → `frontend/src/`
- `@components/` → `frontend/src/components/`
- `@pages/` → `frontend/src/pages/`
- `@features/` → `frontend/src/features/`
- `@hooks/` → `frontend/src/hooks/`
- `@stores/` → `frontend/src/stores/`
- `@services/` → `frontend/src/services/`
- `@utils/` → `frontend/src/utils/`
- `@types/` → `frontend/src/types/`
- `@config/` → `frontend/src/constants/`

## 关键文件路径

### 后端

| 用途 | 路径 |
|------|------|
| 应用入口与路由注册 | `backend/main.py` |
| 全局配置 | `backend/core/config.py` |
| RBAC 权限系统 | `backend/core/auth/rbac.py` |
| 用户模型 | `backend/core/user/models.py` |
| MongoDB 连接 | `backend/core/db/mongodb.py` |
| Redis 连接 | `backend/core/db/redis.py` |
| AI 模型管理 | `backend/core/ai/` |
| 安全服务 | `backend/core/security/` |
| MCP 连接池 | `backend/core/mcp/pool/pool.py` |
| MCP 适配器 | `backend/core/mcp/adapter/adapter.py` |
| MCP 服务 | `backend/core/mcp/service/mcp_service.py` |
| TradingAgents 工作流调度器 | `backend/modules/trading_agents/scheduler/workflow_scheduler.py` |
| TradingAgents 任务管理器 | `backend/modules/trading_agents/manager/task_manager.py` |
| 数据源路由器 | `backend/core/market_data/managers/source_router.py` |

### 前端

| 用途 | 路径 |
|------|------|
| 应用入口 | `frontend/src/App.tsx` |
| 路由配置 | `frontend/src/router/` |
| HTTP 实例与拦截器 | `frontend/src/services/http/` |
| 认证 Store | `frontend/src/stores/auth.store.ts` |
| 分析功能模块 | `frontend/src/features/analysis/` |
| 页面组件 | `frontend/src/pages/` |

## 环境变量配置

### 后端 (`backend/.env`)

```bash
# 应用基础配置
APP_NAME=StockAnalysis
APP_VERSION=0.1.0
DEBUG=true
ENVIRONMENT=development

# MongoDB 配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=stock_analysis

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# JWT 配置
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 限流与安全配置
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
LOGIN_MAX_ATTEMPTS=5
```

### 前端 (`frontend/.env`)

```bash
VITE_API_BASE_URL=/api
```

## 开发规范

### Python 代码规范

- **Line Length**: 100 字符
- **Python Version**: 3.11
- **Type Hints**: 强制使用 (`disallow_untyped_defs = true`)
- **测试**: pytest + pytest-asyncio
- **代码检查**: ruff + black + mypy

### 前端代码规范

- **TypeScript**: 严格模式
- **组件**: React 函数组件 + Hooks
- **状态管理**: Zustand
- **路由**: React Router v7

### 日志规范

**适用范围**: 后端服务、CLI、脚本、数据处理。**不适用**: 纯前端 UI 代码、测试代码。

**日志级别**:
- **ERROR**: 功能异常、需要人工介入(数据库连接失败、API 调用异常)
- **WARN**: 潜在问题、但程序可继续(配置缺失用默认值、重试后成功)
- **INFO**: 关键业务节点(用户登录登出、订单状态变更、任务开始/结束)
- **DEBUG**: 调试信息(入参出参、SQL 语句、缓存命中情况)

**必须添加日志的位置**:
- catch 块添加 ERROR 日志(含错误信息、堆栈、上下文)
- 关键业务节点添加 INFO 日志
- 外部调用(API、数据库、第三方服务)前后
- 重要状态变更时添加 INFO 日志

**禁止添加日志的情况**:
- 高频调用的接口/循环内部(避免日志污染)
- 大量重复执行的代码段

**日志内容**:
- 必须包含足够的上下文信息(用户ID、订单号、请求ID 等)
- 禁止记录敏感信息(密码、Token、密钥 等)
- 脱敏处理(手机号、身份证)

## 添加新功能模块

### 后端模块

创建 `backend/modules/your_module/api.py`:

```python
from fastapi import APIRouter, Depends
from core.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/your-module", tags=["your-module"])

@router.get("/")
async def get_data(user=Depends(get_current_user)):
    # user_id 在 user 对象中,数据自动隔离
    pass
```

在 `backend/main.py` 中注册路由:

```python
from modules.your_module.api import router as your_module_router

app.include_router(your_module_router)
```

### 前端模块

创建 `frontend/src/features/your_feature/` 目录，包含：

- `components/` - 功能相关组件
- `hooks/` - 功能相关自定义 Hooks
- `schemas/` - Zod 校验规则

创建 `frontend/src/pages/your_page/` 目录，包含页面级组件：

```tsx
// frontend/src/pages/your_page/index.tsx
export default function YourPage() {
  return <div>Your Page Content</div>
}
```

在 `frontend/src/router/` 中注册路由：

```tsx
import { RouteObject } from 'react-router-dom'

export const yourRoutes: RouteObject[] = [
  {
    path: '/your-page',
    element: <YourPage />,
  },
]
```

## 前后端 API 对齐记录 (2026-04-19)

### 已完成的对齐工作

**后端新增模块（15个，约108个API端点）：**

| 模块 | 路径前缀 | 端点数 | 说明 |
|------|---------|--------|------|
| Analysis 适配器 | `/api/analysis/*` | 21 | 前端 `/api/analysis/*` → 后端 `trading_agents` 服务 |
| Config 适配器 | `/api/config/*` | 48 | 统一配置路由（LLM Provider/Model Catalog/Market Category） |
| Reports 适配器 | `/api/reports/*` | 5 | 报告列表/详情/下载 |
| Stock Data | `/api/stocks/*` + `/api/stock-data/*` | 11 | 股票数据查询 |
| Sync | `/api/sync/*` | 9 | 数据同步管理 |
| Favorites | `/api/favorites/*` | 7 | 用户自选股 CRUD |
| Screening | `/api/screening/*` | 6 | 智能选股筛选 |
| Multi-Market | `/api/markets/*` | 5 | 跨市场查询 |
| Scheduler | `/api/scheduler/*` | 13 | 定时任务管理 |
| Cache | `/api/cache/*` | 5 | 缓存管理 |
| Database Admin | `/api/system/database/*` | 9 | 数据库管理 |
| System Logs | `/api/system/system-logs/*` | 5 | 系统日志 |
| Operation Logs | `/api/system/logs/*` | 4 | 操作日志 |
| Usage | `/api/usage/*` | 5 | 使用统计 |
| Tools | `/api/tools/*` | 4 | 工具管理 |

**后端新增服务文件：**
- `core/ai/provider_service.py` + `provider_models.py` — LLM 厂家管理
- `core/ai/model_catalog_service.py` + `model_catalog_models.py` — 模型目录
- `core/market_data/category_service.py` + `category_models.py` — 市场分类

**前端新增页面（4个）：**
- `/admin/users` — 管理员用户管理
- `/admin/trading-agents` — TradingAgents 管理
- `/system/data-source-status` — 数据源状态监控
- Settings 页面完善（核心设置/通知/配额）

**前端类型清理：**
- 合并 `auth.types.ts` + `auth.types.new.ts` → 统一 `auth.types.ts`
- 删除未使用的 `trading-agents.types.ts`
- 修复 47 个 TypeScript 编译错误

## 项目文档

- [系统设计文档](docs/系统设计文档.md) - 系统架构设计
- [TradingAgents 模块文档](docs/TradingAgents/README.md) - TradingAgents 完整文档
- [市场数据模块文档](docs/market_data/README.md) - 市场数据模块文档
- [MCP 模块文档](docs/MCP/MCP模块设计方案.md) - MCP 模块完整文档
- [项目目录结构](docs/项目目录结构.md) - 完整目录结构说明
