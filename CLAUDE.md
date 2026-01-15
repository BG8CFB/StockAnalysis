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
docker-compose -f docker-compose.dev.yml logs frontend

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
poetry run pytest tests/modules/mcp/  # 运行特定模块测试

# 后端代码检查
poetry run black .                  # 代码格式化(line-length: 100)
poetry run ruff check .             # Lint 检查
poetry run mypy .                   # 类型检查(Python 3.11, disallow_untyped_defs: true)

# 前端
cd frontend
npm run lint                        # ESLint 检查
npm run build                       # 构建生产版本
npm run build:check                 # 类型检查 + 构建
```

### 开发环境访问地址

- 前端: http://localhost:5173
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
- **security/** - 安全模块(滑块验证码、限流器、IP 信任)
- **settings/** - 统一设置(系统设置、用户设置)
- **market_data/** - 市场数据核心(多数据源统一接入)
- **user/** - 用户核心
- **admin/** - 管理员核心(任务清理、审计日志)

**backend/modules/** - 业务功能模块(可插拔):
- **trading_agents/** - TradingAgents 智能体分析核心(完整实现)
  - **scheduler/** - LangChain 工作流调度器
  - **phases/** - 四阶段工作流(phase1-4)
  - **manager/** - 任务管理器与并发控制
  - **websocket/** - WebSocket 实时推送
  - **tools/** - MCP 工具集成
- **mcp/** - MCP 模块(完整实现)
  - **pool/** - 连接池管理
  - **core/** - 适配器/会话/拦截器
  - **config/** - 配置管理
- **screener/ask_stock/dashboard/** - 预留框架

### 前端架构

**frontend/src/core/** - 核心框架:
- **auth/** - 认证(store + views)
- **router/** - Vue Router(模块化路由加载器)
- **api/** - Axios 实例与拦截器
- **settings/** - 统一设置模块
- **layout/** - 布局组件
- **components/** - 核心组件(滑块验证码等)

**frontend/src/modules/** - 业务模块前端实现:
- **trading_agents/** - TradingAgents 模块
- **settings/** - 设置模块
- **dashboard/screener/ask_stock/** - 其他模块

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

1. **Phase 1: 信息收集与基础分析** - 并行分析师团队(技术/基本面/情绪/新闻)
2. **Phase 2: 多空博弈与投资决策** - 观点辩论与决策
3. **Phase 3: 交易执行策划** - 风险评估
4. **Phase 4: 策略风格与风险评估** - 综合报告

### 并发控制机制

三层并发控制:
- **模型级**: 双模型并发槽位管理
- **任务级**: 单任务内并发控制
- **批量级**: 批量任务队列管理

### 关键组件

- **WorkflowScheduler** (`backend/modules/trading_agents/scheduler/workflow_scheduler.py`) - LangChain 工作流调度器
- **TaskManager** (`backend/modules/trading_agents/manager/task_manager.py`) - 核心任务管理
- **ConcurrencyController** (`backend/modules/trading_agents/manager/concurrency_controller.py`) - 并发控制
- **智能体配置** (`backend/modules/trading_agents/phases/*/agents/*.yaml`) - YAML 配置文件

## MCP 模块关键概念

MCP (Model Context Protocol) 是统一的工具调用协议。

### 关键组件

- **MCP 连接池** (`backend/modules/mcp/pool/pool.py`) - 连接池管理
- **MCP 适配器** (`backend/modules/mcp/core/adapter.py`) - MCP 适配器
- **默认配置** (`backend/modules/mcp/config/default_config.yaml`) - 默认配置

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

- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router
- **图表**: ECharts
- **代码编辑器**: CodeMirror 6

## 前端路径别名

Vite 配置中定义的路径别名:
- `@/` → `frontend/src/`
- `@core/` → `frontend/src/core/`
- `@modules/` → `frontend/src/modules/`

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
| TradingAgents 工作流调度器 | `backend/modules/trading_agents/scheduler/workflow_scheduler.py` |
| TradingAgents 任务管理器 | `backend/modules/trading_agents/manager/task_manager.py` |
| MCP 连接池 | `backend/modules/mcp/pool/pool.py` |
| 数据源路由器 | `backend/core/market_data/managers/source_router.py` |

### 前端

| 用途 | 路径 |
|------|------|
| 路由实例与模块加载器 | `frontend/src/core/router/index.ts` |
| Axios 实例与拦截器 | `frontend/src/core/api/http.ts` |
| 认证 Store | `frontend/src/core/auth/store.ts` |
| TradingAgents 状态管理 | `frontend/src/modules/trading_agents/store.ts` |

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
- **组件**: Vue 3 Composition API
- **状态管理**: Pinia
- **路由**: 基于模块的动态加载

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

创建 `frontend/src/modules/your_module/routes.ts`:

```typescript
export default [
  {
    path: '/your-module',
    component: () => import('./views/YourView.vue'),
    meta: { requiresAuth: true }
  }
]
```

路由会通过 `frontend/src/core/router/module_loader.ts` 自动加载。

## 项目文档

- [系统设计文档](docs/系统设计文档.md) - 系统架构设计
- [TradingAgents 模块文档](docs/TradingAgents/README.md) - TradingAgents 完整文档
- [市场数据模块文档](docs/market_data/README.md) - 市场数据模块文档
- [MCP 模块文档](docs/MCP/MCP模块设计方案.md) - MCP 模块完整文档
- [项目目录结构](docs/项目目录结构.md) - 完整目录结构说明
