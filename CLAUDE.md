# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

---

## 项目概览

**模块化单体 (Modular Monolith)** 股票分析平台，支持多用户认证和完全的用户数据隔离。

**核心特性：**
- 基于 JWT 的多用户认证和 RBAC 权限控制（4 角色 + 细粒度权限）
- 完整的用户数据隔离 (MongoDB + Redis，强制 user_id 过滤)
- TradingAgents 智能体分析系统（基于 LangGraph 的四阶段工作流）
- MCP (Model Context Protocol) 服务器集成与工具调用
- WebSocket 实时任务进度推送
- 并发控制与任务队列管理
- 报告归档与过期任务自动清理

**技术栈：**
- **后端**: FastAPI + Pydantic + Motor + Redis + LangGraph + MCP SDK
- **前端**: Vue 3 + TypeScript + Vite + Element Plus + Pinia
- **数据库**: MongoDB + Redis
- **容器化**: Docker + Docker Compose
- **依赖管理**: Poetry (Python) + npm (前端)

> 详细技术栈和部署说明请参考 [README.md](README.md)

---

## 快速启动

```bash
# 推荐方式：使用开发脚本
scripts\dev.bat        # Windows
./scripts/dev.sh       # Linux/Mac

# 或手动启动（详见"开发命令"章节）
```

---

## 开发命令

### 后端命令

```bash
# 依赖管理
poetry install                    # 安装依赖

# 开发服务器
poetry run uvicorn main:app --reload

# 代码质量
poetry run pytest                 # 运行测试
poetry run black .                # 代码格式化
poetry run ruff .                 # Lint 检查
poetry run mypy .                 # 类型检查
```

### 前端命令

```bash
# 依赖管理
npm install                       # 安装依赖

# 开发服务器
npm run dev                       # 启动开发服务器

# 构建与检查
npm run build                     # 生产构建
npm run type-check                # TypeScript 类型检查
npm run lint                      # ESLint 代码检查
```

### Docker 命令

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up -d

# 生产环境
docker-compose up -d

# 仅启动数据库
docker-compose -f docker-compose.dev.yml up -d mongodb redis

# 实用命令
docker-compose -f docker-compose.dev.yml logs -f      # 查看日志
docker-compose -f docker-compose.dev.yml restart       # 重启服务
docker-compose -f docker-compose.dev.yml down -v       # 停止并清理
docker exec -it stock-analysis-backend-dev /bin/bash   # 进入容器
```

---

## 架构设计

### 核心原则

**核心与模块的区别：**
- `core/` = 项目核心框架（认证、用户、设置、管理员、安全、AI 基础、系统、**市场数据**），不可随意修改
- `modules/` = 业务功能模块（TradingAgents、仪表板等），可独立扩展

### 目录结构

> 📁 完整目录结构、前端导航结构和关键文件路径请参考 [项目目录结构.md](docs/项目目录结构.md)

### 关键架构模式

**1. 用户数据隔离（强制执行）**
- **MongoDB**: 所有用户相关文档 **必须** 包含 `user_id` 字段
- **Redis**: 使用带命名空间的键 (`user:{user_id}:...`)
- **Service 层**: 所有查询和操作 **必须** 强制过滤 `user_id`，严禁直接查询全表（除非是管理员功能的明确需求）

**2. RBAC 权限系统** ([`backend/core/auth/rbac.py`](backend/core/auth/rbac.py))
- **角色**: `GUEST` (访客), `USER` (普通用户), `ADMIN` (管理员), `SUPER_ADMIN` (超级管理员)
- **权限**: 细粒度权限如 `user:read`, `user:create`, `system:config`, `audit:read` 等
- **使用**: 后端使用 `@require_role()` 或 `@require_permission()` 装饰器；前端路由使用 `meta.adminOnly: true`

**3. 用户状态工作流**
```
注册 → PENDING (待审核)
       ↓
    管理员审核
       ↓
    ├─ APPROVE → ACTIVE (已激活，可登录)
    ├─ REJECT → REJECTED (已拒绝，数据保留但不可登录)
    └─ 禁用 → DISABLED (暂时禁止登录)
```

**4. 后端模块注册机制** ([`backend/main.py`](backend/main.py))
- 在 `main.py` 中注册路由
- **顺序很重要**：核心路由优先，业务模块在后
- 注册顺序：settings → core_admin → ai_core → system → user → user_settings → **market_data** → screener → ask_stock → mcp → trading_agents → trading_agents_admin

**5. 应用生命周期管理** ([`backend/main.py`](backend/main.py) - `lifespan`)
- **启动阶段**：MongoDB → Redis → 定时任务 → TradingAgents 任务过期/归档/队列 → 数据库索引 → 任务恢复 → 公共配置 → MCP 健康检查 → MCP 会话管理
- **关闭阶段**：按相反顺序关闭所有服务

**6. 后台任务系统**
- 使用 `APScheduler` 处理定时任务 ([`backend/core/admin/tasks.py`](backend/core/admin/tasks.py))
- **任务过期处理**: 自动清理 24 小时前的过期任务
- **报告归档**: 自动归档 30 天前的分析报告

**7. 日志与配置**
- 使用自定义彩色日志格式化器 ([`backend/core/colored_formatter.py`](backend/core/colored_formatter.py))
- 后端配置管理使用 Pydantic Settings ([`backend/core/config.py`](backend/core/config.py))
- 前端路由采用懒加载 ([`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts))

---

## 用户管理

### 用户状态

| 状态 | 代码 | 登录权限 | 说明 |
|------|------|----------|------|
| 待审核 | `PENDING` | ❌ | 注册后的默认状态（如开启审核） |
| 已激活 | `ACTIVE` | ✅ | 正常使用状态 |
| 已禁用 | `DISABLED` ❌ | 被管理员手动禁用，数据保留 |
| 已拒绝 | `REJECTED` | ❌ | 审核未通过 |

### 密码重置流程
1. **用户请求**: `/api/users/request-reset` (开发环境 Token 会打印在控制台)
2. **管理员触发**: 管理员可在后台手动触发特定用户的密码重置
3. **重置操作**: 用户携带 Token 访问重置页面设置新密码

### 注册审批流程
- **配置项**: `REQUIRE_APPROVAL` (在 `.env` 或 `config.py` 中设置)
- 若为 `True`，新用户状态为 `PENDING`，需管理员审核通过
- 若为 `False`，新用户状态直接为 `ACTIVE`

---

## TradingAgents 模块

基于 LangGraph 的多阶段 AI 股票分析系统，是本项目的核心业务模块。

### 四阶段工作流

| 阶段 | 名称 | 描述 | 输出 |
|------|------|------|------|
| 1 | 分析师团队 (Individual Analysis) | 3-4个分析师（技术面、基本面、市场情绪、新闻）并行分析 | 多份独立报告 |
| 2 | 研究与辩论 (Research & Debate) | 看多/看空辩手进行多轮辩论，研究经理裁决 | 辩论总结 |
| 3 | 风险评估 (Risk Assessment) | 激进/保守/中性三方讨论，首席风控官总结 | 风险报告 |
| 4 | 总结报告 (Summary) | 综合所有信息生成最终投资建议 | 最终报告 (买入/卖出/持有) |

### 关键特性

- **并发控制**: 公共模型资源池、用户级并发限制、批量任务并发 ([`concurrency_controller.py`](backend/modules/trading_agents/core/concurrency_controller.py))
- **工具循环检测**: 自动检测并中断连续重复的工具调用（阈值: 3次）([`loop_detector.py`](backend/modules/trading_agents/tools/loop_detector.py))
- **任务恢复机制**: 系统重启后自动恢复运行中的任务 ([`task_manager_restore.py`](backend/modules/trading_agents/core/task_manager_restore.py))
- **Token 消耗追踪**: 记录每个阶段的 Token 用量，前端展示预估成本
- **WebSocket 实时推送**: 任务状态变更实时推送，支持多客户端连接 ([`websocket/manager.py`](backend/modules/trading_agents/websocket/manager.py))
- **批量任务管理**: 支持一次性分析多只股票（1-50只）([`batch_manager.py`](backend/modules/trading_agents/core/batch_manager.py))

> 📖 任务详情可观测性设计请参考 [任务详情可观测性设计.md](docs/TradingAgents/任务详情可观测性设计.md)

### 配置规则

**多用户配置优先级（Mandatory）**：
1. 用户自定义配置（`is_customized=True`）
2. 系统公共配置（`user_id="system_public"`）
3. 默认 YAML 模板

**双模型配置**：
- **数据收集模型**（第一阶段）：需要调用 MCP 工具，通常选择较强且较快的模型
- **辩论模型**（第二、三、四阶段）：主要是文本生成，通常选择性价比高的模型

**模型选择优先级**：任务参数 > 用户模型偏好 > 系统默认模型

### 工具模块

TradingAgents 智能体通过调用工具模块获取市场数据：
- 市场行情类工具（实时报价、历史行情）
- 财务数据类工具（财务报表、财务指标）
- 公司信息类工具（公司资料、公告）
- 宏观经济工具（经济指标）
- 技术分析工具（技术指标）

> 📖 完整工具接口说明请参考 [工具模块设计方案.md](docs/TradingAgents/工具模块设计方案.md)

---

## 市场数据模块

A股市场数据接入模块，支持从多个数据源获取并存储股票相关数据。

### 数据源支持

| 数据源 | 类型 | 特点 | 主要数据类型 |
|--------|------|------|--------------|
| TuShare | API Token | 数据全面、官方接口稳定 | 股票列表、行情、财务、公司信息、宏观经济 |
| AkShare | 免费API | 无需Token、数据丰富 | 股票列表、行情、财务、SHIBOR、PMI |

### 模块架构

```
core/market_data/
├── admin_api.py              # 管理 API 路由
├── models/                   # 数据模型
│   ├── __init__.py          # 统一导出
│   ├── datasource.py        # 数据源相关模型
│   ├── stock_info.py        # 股票信息模型
│   ├── stock_quote.py       # 行情数据模型
│   ├── stock_financials.py  # 财务数据模型
│   ├── stock_company.py     # 公司信息模型
│   ├── stock_macro.py       # 宏观经济模型
│   ├── stock_other.py       # 其他数据模型（自选股、同步任务等）
│   └── watchlist.py         # 自选股模型
├── repositories/             # 数据存储层
│   ├── base.py              # Repository 基类
│   ├── datasource.py        # 数据源配置和状态
│   ├── stock_info.py        # 股票信息
│   ├── stock_quotes.py      # 行情数据
│   ├── stock_financial.py   # 财务数据和指标
│   ├── stock_company.py     # 公司信息
│   ├── macro_economic.py    # 宏观经济数据
│   └── watchlist.py         # 自选股
├── services/                 # 业务服务层
│   ├── data_sync_service.py      # 数据同步服务
│   ├── source_monitor_service.py # 数据源状态监控
│   ├── data_scheduler.py         # 数据调度服务
│   ├── market_data_service.py    # 市场数据服务
│   ├── dual_channel_service.py   # 双通道服务
│   └── rate_limiter.py           # 限流器
├── sources/                  # 数据源适配器
│   ├── base.py              # 适配器基类
│   ├── registry.py          # 数据源注册表
│   ├── a_stock/             # A股数据源
│   │   ├── tushare_adapter.py     # TuShare 适配器
│   │   └── akshare_adapter.py     # AkShare 适配器
│   ├── us_stock/            # 美股数据源
│   │   ├── yahoo_adapter.py       # Yahoo Finance 适配器
│   │   └── alphavantage_adapter.py # Alpha Vantage 适配器
│   ├── hk_stock/            # 港股数据源
│   │   ├── yahoo_adapter.py       # Yahoo Finance 适配器
│   │   └── akshare_adapter.py     # AkShare 适配器
│   └── metadata/            # 数据源元数据
│       └── sources_manifest.yaml  # 数据源清单
├── tools/                    # 工具类
│   ├── base_tool.py         # 工具基类
│   ├── field_mapper.py      # 字段映射转换工具
│   ├── a_stock_tools.py     # A股工具
│   ├── us_stock_tools.py    # 美股工具
│   └── hk_stock_tools.py    # 港股工具
├── managers/                 # 管理器
│   └── source_router.py     # 数据源路由器
└── config/                   # 配置管理
    ├── schemas.py           # 配置模型
    └── service.py           # 配置服务
```

### 核心功能

**1. 数据同步服务**
- 支持同步股票列表、日线行情、分钟K线、财务数据、公司信息、宏观经济数据
- 双通道数据流：直接返回 + 限速数据库写入
- 自动失败处理和数据源状态更新

**2. 数据源状态监控**
- 健康状态：healthy（健康）、degraded（降级）、unavailable（不可用）、standby（待命）
- 自动健康检查和状态变更记录
- 失败计数和自动降级机制
- 历史事件查询和错误统计

**3. 字段映射系统**
- `FieldMapper` 基类：通用字段标准化工具
- `TuShareFieldMapper`：TuShare 字段到统一字段映射
- `AkShareFieldMapper`：AkShare 字段到统一字段映射

### API 接口

**数据同步接口**：
- POST `/api/market-data/sync/stock-list` - 同步股票列表
- POST `/api/market-data/sync/daily-quotes` - 同步日线行情
- POST `/api/market-data/sync/minute-quotes` - 同步分钟K线
- POST `/api/market-data/sync/financials` - 同步财务数据
- POST `/api/market-data/sync/company-info` - 同步公司信息
- POST `/api/market-data/sync/macro-economic` - 同步宏观经济数据

**健康检查接口**：
- POST `/api/market-data/health/check` - 检查单个数据源健康状态
- POST `/api/market-data/health/check-all` - 检查所有数据源健康状态

**状态监控接口**：
- GET `/api/market-data/monitor/status-summary` - 获取状态汇总
- GET `/api/market-data/monitor/source-status/{source_id}` - 获取指定数据源状态
- GET `/api/market-data/monitor/recent-events` - 获取最近事件
- GET `/api/market-data/monitor/source-history/{source_id}` - 获取数据源历史
- GET `/api/market-data/monitor/error-statistics` - 获取错误统计

**数据源配置接口**：
- GET `/api/market-data/sources/configs` - 获取数据源配置列表
- GET `/api/market-data/sources/config/{source_id}` - 获取单个数据源配置

### 数据库表结构

| 表名 | 用途 | 主要字段 |
|------|------|---------|
| stock_info | 股票基础信息 | symbol, market, name, industry, listing_date |
| stock_quotes | 日线行情数据 | symbol, trade_date, open, high, low, close, volume |
| stock_financials | 财务报表数据 | symbol, report_date, income_statement, balance_sheet |
| stock_financial_indicators | 财务指标数据 | symbol, report_date, roe, roa, eps |
| stock_companies | 公司详细信息 | symbol, company_name, business, contact |
| macro_economic | 宏观经济数据 | indicator, period, value, yoy |
| system_data_sources | 系统数据源配置 | source_id, market, config, enabled |
| user_data_sources | 用户数据源配置 | user_id, source_id, market, config |
| data_source_status | 数据源健康状态 | market, data_type, source_id, status |
| data_source_status_history | 状态变更历史 | source_id, event_type, from_status, to_status |

### 测试脚本

完整的测试脚本位于 [`backend/test_market_data_comprehensive.py`](backend/test_market_data_comprehensive.py)，包含：
- 数据源配置 Repository 测试
- 数据源状态 Repository 测试
- 股票信息 Repository 测试
- 股票行情 Repository 测试
- 财务数据 Repository 测试
- 公司信息 Repository 测试
- 宏观经济数据 Repository 测试
- 数据同步服务测试
- 数据源状态监控服务测试

运行测试：
```bash
cd backend
python test_market_data_comprehensive.py
```

### 配置说明

数据源配置需要在 `system_data_sources` 表中创建：
- TuShare 需要配置 `api_token`
- AkShare 无需配置 Token

### 注意事项

1. **数据保留策略**：自选股的日线和分钟数据保留1周
2. **限流机制**：Token 限流、并发控制、失败重试
3. **数据源优先级**：按配置的 priority 顺序使用，自动降级到备用源
4. **字段标准化**：所有数据源数据经过 field_mapper 统一转换

---

## MCP 模块

MCP (Model Context Protocol) 模块负责管理与 MCP 服务器的连接和工具调用。

> 📖 完整业务文档请参考 [MCP模块完整文档.md](docs/MCP/MCP模块完整文档.md)

### 模块架构

- **api/** - API 层，提供 RESTful 接口
- **pool/** - 连接池，管理服务器连接和队列
- **service/** - 服务层，核心业务逻辑
- **core/** - 核心层，适配器和会话管理
- **config/** - 配置管理

### 核心特性

- **连接池管理**：支持个人和公共连接池，自动重连和错误恢复
- **传输协议**：stdio、http/streamable_http（推荐）、websocket
- **健康检查**：自动检测服务器可用性，定期检查任务
- **会话管理**：会话生命周期管理、复用和缓存
- **工具容错**：required/optional 容错策略

### 关键文件路径

| 用途 | 路径 |
|------|------|
| MCP 模块 API | [`backend/modules/mcp/api/routes.py`](backend/modules/mcp/api/routes.py) |
| MCP 连接池 | [`backend/modules/mcp/pool/pool.py`](backend/modules/mcp/pool/pool.py) |
| MCP 适配器 | [`backend/modules/mcp/core/adapter.py`](backend/modules/mcp/core/adapter.py) |
| MCP 默认配置 | [`backend/modules/mcp/config/default_config.yaml`](backend/modules/mcp/config/default_config.yaml) |

### 与 TradingAgents 集成

通过 MCP 工具过滤器调用 MCP 服务器的工具 ([`mcp_tool_filter.py`](backend/modules/trading_agents/tools/mcp_tool_filter.py))，支持工具级别容错和自动工具发现。

---

## 新功能开发指南

### 业务模块开发 (modules/)

**后端开发步骤**：
1. 在 `backend/modules/` 下创建新目录
2. 编写 `api.py`（路由定义）、`service.py`（业务逻辑）、`models.py`（数据模型，可选）
3. **必须** 使用 `get_current_user` 依赖注入
4. **必须** 确保所有数据库操作包含 `user_id` 过滤
5. 在 `main.py` 中注册路由（注意顺序）

**前端开发步骤**：
1. 在 `frontend/src/modules/` 下创建视图组件
2. 在 [`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts) 中添加路由
3. 创建对应的 API 调用文件和状态管理 Store（可选）

### 核心功能扩展 (core/)

- 修改核心逻辑（如认证、RBAC）需极其谨慎
- 必须运行完整测试套件确保不破坏现有功能
- 更新本文档

---

## 环境配置

项目使用环境变量进行配置管理。模板文件位于：

- **后端**: [`backend/.env.example`](backend/.env.example)
- **前端**: [`frontend/.env.example`](frontend/.env.example)

**使用方法**：复制模板文件并重命名为 `.env`，根据实际环境修改配置值。

**主要配置项**：
- 数据库连接（MongoDB、Redis）
- JWT 密钥和过期时间
- CORS 跨域设置
- 安全相关（限流、验证码、IP 信任等）
- 用户审核开关

---

## 开发规范

### 代码规范

**Python**:
- 遵循 PEP 8 规范
- 使用 Black 格式化（行长度 100）
- 使用 Ruff 进行 Lint 检查
- 使用 Mypy 进行类型检查
- 使用 Poetry 管理依赖

**TypeScript/Vue**:
- 遵循 ESLint 规则
- 使用 Prettier 格式化（可选）
- 使用 Vue 3 Composition API
- 使用 Pinia 进行状态管理

### 日志规范

**必须使用日志的场景（强制）**：后端服务、CLI 工具、定时任务、数据处理脚本、文件/数据库操作代码

**日志级别选择**:
- **ERROR**: 功能异常、需要人工介入（数据库连接失败、API 调用异常、业务规则违反）
- **WARN**: 潜在问题、但程序可继续（配置缺失用默认值、重试后成功、性能降级）
- **INFO**: 关键业务节点（用户登录登出、订单状态变更、任务开始/结束）
- **DEBUG**: 调试信息（入参出参、SQL 语句、缓存命中情况）

**必须添加日志的位置（强制）**：
- try-catch 的 catch 块
- 外部调用前后（API、数据库、文件 IO、第三方服务）
- 业务入口
- 重要对象状态改变时
- 重要条件分支

### 数据库操作规范

**MongoDB**:
- 所有用户数据必须包含 `user_id` 字段
- 使用 Motor 异步驱动
- 使用 ObjectId 进行查询
- 建立合适的索引

**Redis**:
- 使用带命名空间的键：`user:{user_id}:...`
- 使用异步客户端
- 设置合理的过期时间

### 安全规范

- **禁止**在代码中硬编码敏感信息（密码、API Key、Token、密钥等）
- 敏感信息必须使用环境变量或配置中心
- 涉及数据库操作时，SQL 使用参数化查询，禁止字符串拼接
- 涉及用户输入展示时，注意 XSS 防护
- 生产环境禁止执行破坏性操作（除非经过严格确认）

**密码存储**: 使用 bcrypt (12 rounds) 哈希
**JWT**: HS256 算法，30分钟有效期
**数据隔离**: 严格执行 `user_id` 过滤
**敏感信息**: 智能体提示词 (`prompts`) 等敏感配置仅管理员可见
**验证码**: 滑块验证码防暴力破解
**IP 信任**: 常用 IP 登录无感验证
**限流**: API 请求频率限制

---

## Git 提交规范

**提交信息格式**:
```
<类型>: <简要描述>

类型：新增 | 修复 | 重构 | 优化 | 文档 | 配置
```

**示例**:
```
新增: 用户登录模块
修复: 订单列表分页异常
重构: 支付流程代码结构
```

---

## 已知问题与解决方案

### 1. SSE 换行符转义问题
**现象**: SSE 流输出字面量 `\n\n` 而不是换行
**解决**: Python f-string 中需使用双反斜杠 `\\n\\n`

### 2. Vue 组件导入
**现象**: `Failed to resolve component`
**解决**: 自定义组件（非 Element Plus）必须在 `<script setup>` 中显式 import

### 3. 并发控制队列位置
**现象**: 批量任务队列位置不准确
**解决**: 当前为简化实现，建议后续优化为更精确的排队机制

---

## API 文档

> 📡 完整的 API 接口文档（包含请求格式、返回格式、数据模型等）请参考 [API文档.md](docs/API文档.md)

---

## 文档维护规则

**重要**: 本项目记忆文档由 AI 完全自主维护。以下文档维护规则必须遵守：

### docs/ 目录文档维护

| 文档 | 内容 | 维护触发条件 |
|------|------|-------------|
| [项目目录结构.md](docs/项目目录结构.md) | 完整目录结构、前端导航、关键文件路径 | 新增/删除/移动/重命名文件或目录 |
| [API文档.md](docs/API文档.md) | API 接口规范（请求格式、返回格式、数据模型） | 新增/修改/删除 API 接口或数据模型 |

**必须同步更新的情况**：
1. **文件/目录变更**：新增、删除、移动、重命名文件或目录时，更新 [项目目录结构.md](docs/项目目录结构.md)
2. **API 变更**：新增、修改、删除 API 接口时，更新 [API文档.md](docs/API文档.md)
3. **数据模型变更**：修改 Pydantic 模型时，同步更新 API 文档中的请求/返回格式
4. **路由变更**：新增、修改、删除路由时，更新前端导航结构说明

**维护建议**：
- 每次完成功能开发后，检查是否有文件结构或 API 变更
- 参考 `backend/modules/*/schemas/` 中的 Pydantic 模型定义，确保 API 文档与代码一致
- 提交代码前，检查相关文档是否已更新
- 定期（每周/每月）审查 docs/ 目录文档与实际代码的一致性

---