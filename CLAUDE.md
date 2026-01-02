# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概览

这是一个 **模块化单体 (Modular Monolith)** 股票分析平台，支持多用户认证和完全的用户数据隔离。

**核心技术栈：** Vue 3 + FastAPI + MongoDB + Redis + LangGraph

**核心特性：**
- 基于 JWT 的多用户认证和 RBAC 权限控制（4 角色 + 细粒度权限）
- 完整的用户数据隔离 (MongoDB + Redis，强制 user_id 过滤)
- TradingAgents 智能体分析系统（基于 LangGraph 的四阶段工作流）
- MCP (Model Context Protocol) 服务器集成与工具调用
- WebSocket 实时任务进度推送
- 并发控制与任务队列管理
- 报告归档与过期任务自动清理

详细技术栈和部署说明请参考 [README.md](README.md)。

## 快速启动

```bash
# 推荐方式：使用开发脚本
scripts\dev.bat        # Windows
./scripts/dev.sh       # Linux/Mac

# 或手动启动各服务（详见 README.md）
```

### 构建与测试

**前端：**
- `npm run dev` - 启动开发服务器
- `npm run build` - 生产构建
- `npm run type-check` - TypeScript 类型检查
- `npm run lint` - ESLint 代码检查

**后端：**
- `poetry run pytest` - 运行测试
- `poetry run black .` - 代码格式化
- `poetry run ruff .` - Lint 检查
- `poetry run mypy .` - 类型检查

## 架构设计

### 核心与模块的区别 (关键)

**核心原则**：
- `core/` = 项目核心框架（认证、用户、设置、管理员、安全、AI 基础、系统），不可随意修改。
- `modules/` = 业务功能模块（股票分析、TradingAgents、仪表板等），可独立扩展。

### 目录结构

```
StockAnalysis/
├── backend/
│   ├── core/                          # 核心框架（非模块化部分）
│   │   ├── admin/                     # 管理员核心
│   │   │   ├── api.py                 # 管理员 API 路由
│   │   │   ├── service.py             # 管理员业务逻辑
│   │   │   ├── audit_logger.py        # 审计日志记录
│   │   │   ├── audit_models.py        # 审计日志模型
│   │   │   └── tasks.py               # 定时任务（任务清理、报告归档）
│   │   ├── ai/                        # AI 基础
│   │   │   ├── api.py                 # AI 核心 API（模型管理）
│   │   │   ├── llm/                   # LLM 提供商
│   │   │   │   ├── provider.py        # LLM Provider（OpenAI 兼容）
│   │   │   │   ├── openai_compat.py   # OpenAI 接口适配
│   │   │   │   ├── thinking_adapter.py # 思考模式适配器
│   │   │   │   └── thinking_parser.py  # 思考模式解析器
│   │   │   └── model/                 # 模型服务
│   │   │       ├── service.py         # 模型 CRUD 与连接测试
│   │   │       └── schemas.py         # 模型数据模型
│   │   ├── auth/                      # 认证核心
│   │   │   ├── dependencies.py        # 依赖注入（get_current_user）
│   │   │   ├── models.py              # 用户模型与认证相关模型
│   │   │   ├── rbac.py                # RBAC 权限系统
│   │   │   └── security.py            # 安全工具（JWT、密码哈希）
│   │   ├── db/                        # 数据库连接
│   │   │   ├── mongodb.py             # MongoDB 客户端
│   │   │   ├── redis.py               # Redis 客户端
│   │   │   └── models.py              # 通用数据模型
│   │   ├── security/                  # 安全模块
│   │   │   ├── captcha_service.py     # 滑块验证码
│   │   │   ├── email_verification.py  # 邮箱验证（预留）
│   │   │   ├── encryption.py          # 加密工具
│   │   │   ├── ip_trust.py            # IP 信任机制
│   │   │   ├── migration.py           # 数据迁移
│   │   │   └── rate_limiter.py        # 限流器
│   │   ├── settings/                  # 设置核心
│   │   │   ├── api.py                 # 系统设置 API
│   │   │   └── service.py             # 系统设置服务
│   │   ├── system/                    # 系统初始化
│   │   │   └── api.py                 # 系统初始化 API
│   │   ├── user/                      # 用户核心
│   │   │   ├── api.py                 # 用户 API
│   │   │   ├── service.py             # 用户服务
│   │   │   ├── dependencies.py        # 用户依赖注入
│   │   │   ├── models.py              # 用户数据模型
│   │   │   ├── settings_api.py         # 用户设置 API
│   │   │   ├── settings_service.py    # 用户设置服务
│   │   │   ├── settings_database.py   # 用户设置数据库
│   │   │   └── settings_models.py     # 用户设置模型
│   │   ├── background_tasks.py        # 后台任务管理
│   │   ├── colored_formatter.py       # 彩色日志格式化器
│   │   ├── config.py                  # Pydantic 全局配置
│   │   ├── logging_config.py          # 日志配置
│   │   └── exceptions.py              # 自定义异常
│   ├── modules/                       # 业务功能模块（可插拔）
│   │   ├── trading_agents/            # TradingAgents 智能体分析核心模块
│   │   │   ├── api.py                 # TradingAgents API（用户端）
│   │   │   ├── admin_api.py           # TradingAgents API（管理端）
│   │   │   ├── schemas.py             # 数据模型
│   │   │   ├── agents/                # 智能体定义
│   │   │   │   ├── base.py            # 智能体基类
│   │   │   │   ├── phase1/            # 第一阶段：分析师团队
│   │   │   │   │   └── analysts.py    # 分析师工厂
│   │   │   │   ├── phase2/            # 第二阶段：研究员辩论
│   │   │   │   │   ├── debate_manager.py   # 辩论管理器
│   │   │   │   │   ├── debaters.py         # 辩手
│   │   │   │   │   └── research_manager.py # 研究经理
│   │   │   │   ├── phase3/            # 第三阶段：风险评估
│   │   │   │   │   ├── risk_analysts.py    # 风险分析师
│   │   │   │   │   ├── risk_manager.py     # 风险经理
│   │   │   │   │   └── risk.py            # 风险模型
│   │   │   │   └── phase4/            # 第四阶段：总结输出
│   │   │   │       └── summary.py     # 总结智能体
│   │   │   ├── config/                # 配置管理
│   │   │   │   ├── loader.py          # YAML 配置加载器
│   │   │   │   └── templates/
│   │   │   │       └── agents.yaml    # 默认智能体配置模板
│   │   │   ├── core/                  # 核心引擎
│   │   │   │   ├── agent_engine.py    # 智能体工作流引擎
│   │   │   │   ├── task_manager.py     # 任务管理器
│   │   │   │   ├── task_manager_restore.py  # 任务恢复
│   │   │   │   ├── batch_manager.py   # 批量任务管理器
│   │   │   │   ├── concurrency_controller.py # 并发控制器
│   │   │   │   ├── concurrency.py     # 并发管理
│   │   │   │   ├── task_queue.py      # 任务队列
│   │   │   │   ├── task_expiry.py     # 任务过期处理
│   │   │   │   ├── state.py           # 工作流状态
│   │   │   │   ├── database.py        # 数据库操作
│   │   │   │   ├── exceptions.py      # 异常定义
│   │   │   │   └── alerts.py          # 告警机制
│   │   │   ├── services/              # 服务层
│   │   │   │   ├── agent_config_service.py  # 智能体配置服务
│   │   │   │   ├── mcp_service.py     # MCP 服务器服务
│   │   │   │   ├── mcp_patch.py       # MCP 兼容性补丁
│   │   │   │   ├── mcp_health_checker.py    # MCP 健康检查
│   │   │   │   ├── mcp_session_manager.py   # MCP 会话管理
│   │   │   │   ├── settings_service.py     # 分析设置服务
│   │   │   │   ├── report_service.py       # 报告服务
│   │   │   │   └── report_archival.py      # 报告归档
│   │   │   ├── tools/                 # 工具层
│   │   │   │   ├── registry.py        # 工具注册表
│   │   │   │   ├── mcp_adapter.py     # MCP 工具适配器
│   │   │   │   ├── mcp_concurrency.py # MCP 并发控制
│   │   │   │   ├── loop_detector.py   # 工具循环检测器
│   │   │   │   ├── local_tools.py     # 本地工具
│   │   │   │   └── registry_timeout.py # 工具超时
│   │   │   ├── websocket/             # WebSocket 模块
│   │   │   │   ├── manager.py         # WebSocket 管理器
│   │   │   │   └── events.py          # 事件定义
│   │   │   └── tests/                 # 测试
│   │   ├── mcp/                        # MCP 模块（独立）
│   │   │   ├── api/                    # API 层
│   │   │   │   └── routes.py           # MCP API 路由
│   │   │   ├── pool/                   # 连接池
│   │   │   │   ├── pool.py             # 连接池管理
│   │   │   │   ├── queue.py            # 队列管理
│   │   │   │   └── connection.py       # 连接管理
│   │   │   ├── service/                # 服务层
│   │   │   │   ├── mcp_service.py      # MCP 服务
│   │   │   │   └── health_checker.py   # 健康检查服务
│   │   │   ├── core/                   # 核心层
│   │   │   │   ├── adapter.py          # MCP 适配器
│   │   │   │   ├── session.py          # 会话管理
│   │   │   │   ├── interceptors.py     # 拦截器
│   │   │   │   └── exceptions.py       # 异常定义
│   │   │   ├── config/                 # 配置管理
│   │   │   │   ├── loader.py           # 配置加载器
│   │   │   │   ├── settings_service.py # 设置服务
│   │   │   │   ├── settings_models.py  # 设置模型
│   │   │   │   └── default_config.yaml # 默认配置
│   │   │   └── schemas.py              # 数据模型
│   │   ├── analysis/                  # 基础分析模块
│   │   │   ├── api.py                 # 分析 API
│   │   │   ├── batch_api.py           # 批量分析 API
│   │   │   └── single_api.py          # 单股分析 API
│   │   ├── task_center/               # 任务中心模块
│   │   │   └── api.py
│   │   ├── screener/                  # 智能选股模块
│   │   │   └── api.py
│   │   ├── ask_stock/                 # AI 问股模块
│   │   │   └── api.py
│   │   └── dashboard/                 # 仪表板模块
│   ├── background_tasks.py            # 后台任务入口
│   ├── main.py                        # 应用入口与路由注册
│   ├── pyproject.toml                 # Poetry 依赖配置
│   └── Dockerfile                     # 后端 Dockerfile
├── frontend/
│   ├── src/
│   │   ├── core/                      # 前端核心框架
│   │   │   ├── admin/                 # 管理员视图与逻辑
│   │   │   │   ├── api.ts
│   │   │   │   ├── index.ts
│   │   │   │   ├── store.ts
│   │   │   │   ├── types.ts
│   │   │   │   └── views/
│   │   │   │       └── UserManagementView.vue
│   │   │   ├── api/                   # HTTP 客户端
│   │   │   │   └── http.ts            # Axios 实例与拦截器
│   │   │   ├── auth/                  # 认证
│   │   │   │   ├── api.ts
│   │   │   │   ├── store.ts           # Pinia 认证 Store
│   │   │   │   └── views/
│   │   │   │       ├── LoginView.vue
│   │   │   │       └── RegisterView.vue
│   │   │   ├── components/            # 核心组件
│   │   │   │   └── SliderCaptcha.vue # 滑块验证码
│   │   │   ├── events/                # 事件总线
│   │   │   │   └── bus.ts
│   │   │   ├── layout/                # 布局组件
│   │   │   │   ├── MainLayout.vue     # 主布局
│   │   │   │   ├── Sidebar.vue        # 侧边栏
│   │   │   │   └── components/        # 布局子组件
│   │   │   ├── router/                # Vue Router 配置
│   │   │   │   ├── index.ts           # 路由实例
│   │   │   │   └── module_loader.ts   # 模块路由加载器
│   │   │   ├── settings/              # 设置模块
│   │   │   │   ├── api.ts
│   │   │   │   ├── index.ts
│   │   │   │   ├── store.ts
│   │   │   │   ├── types.ts
│   │   │   │   └── views/
│   │   │   │       └── SystemSettingsView.vue
│   │   │   ├── system/                # 系统模块
│   │   │   │   ├── api.ts
│   │   │   │   ├── store.ts
│   │   │   │   └── views/
│   │   │   │       └── InitView.vue   # 系统初始化视图
│   │   │   ├── user/                  # 用户模块
│   │   │   │   ├── api.ts
│   │   │   │   ├── index.ts
│   │   │   │   ├── settings-api.ts
│   │   │   │   ├── settings-types.ts
│   │   │   │   └── types.ts
│   │   │   ├── shared/                # 共享工具
│   │   │   │   ├── index.ts
│   │   │   │   └── types.ts
│   │   │   └── views/                 # 核心视图
│   │   │       └── NotFoundView.vue
│   │   └── modules/                   # 业务功能模块前端实现
│   │       ├── trading_agents/        # TradingAgents 模块
│   │       │   ├── views/             # 页面视图
│   │       │   │   ├── analysis/      # 分析相关视图
│   │       │   │   │   ├── SingleAnalysisView.vue
│   │       │   │   │   ├── BatchAnalysisView.vue
│   │       │   │   │   └── AnalysisDetailView.vue
│   │       │   │   ├── task/          # 任务相关视图
│   │       │   │   │   └── TaskCenterView.vue
│   │       │   │   ├── settings/      # 设置相关视图
│   │       │   │   │   ├── ModelManagementView.vue
│   │       │   │   │   ├── MCPServerManagementView.vue
│   │       │   │   │   ├── AgentConfigView.vue
│   │       │   │   │   └── AnalysisSettingsView.vue
│   │       │   │   └── admin/         # 管理员视图
│   │       │   │       ├── SystemModelView.vue
│   │       │   │       └── AllTasksView.vue
│   │       │   ├── components/        # 模块组件
│   │       │   ├── store.ts           # 状态管理
│   │       │   └── api.ts             # API 调用
│   │       ├── dashboard/             # 仪表板视图
│   │       │   └── views/
│   │       │       └── DashboardView.vue
│   │       ├── screener/              # 选股视图
│   │       │   └── views/
│   │       │       └── ScreenerView.vue
│   │       ├── ask_stock/             # 问股视图
│   │       │   └── views/
│   │       │       └── AskStockView.vue
│   │       └── settings/              # 设置视图
│   │           └── views/
│   │               └── ...
│   ├── vite.config.ts                 # Vite 配置（路径别名: @/, @core, @modules）
│   ├── package.json                   # npm 依赖
│   └── Dockerfile                     # 前端 Dockerfile
├── docs/                              # 项目文档
│   ├── MCP模块设计方案.md
│   ├── 股票数据源模块设计方案.md
│   └── 系统设计文档.md
├── docker/                            # Docker 配置
│   ├── mongodb/init/
│   │   └── init.js                    # MongoDB 初始化脚本
│   └── redis/
│       └── redis.conf                 # Redis 配置
├── docker-compose.yml                 # 生产环境编排
├── docker-compose.dev.yml             # 开发环境编排
├── docker-compose.local.yml           # 本地开发编排
└── scripts/                           # 工具脚本
    ├── dev.bat                        # Windows 开发启动
    └── dev.sh                         # Linux/Mac 开发启动
```

### 前端导航结构

对应 `frontend/src/core/router/module_loader.ts` 中的配置：

```
侧边栏菜单：
├── 仪表板 (dashboard)                # /dashboard
├── 智能选股 (screener)               # /screener
├── AI 问股 (ask-stock)               # /ask-stock
├── TradingAgents 分析工具
│   ├── 单股分析                      # /trading-agents/analysis/single
│   ├── 批量分析                      # /trading-agents/analysis/batch
│   └── 任务中心                      # /trading-agents/tasks
├── 设置 (settings)
│   ├── 用户管理                      # /settings/users [adminOnly]
│   ├── 系统设置                      # /settings/system [adminOnly]
│   ├── MCP 服务器管理                # /settings/mcp-servers
│   ├── AI 模型管理                   # /settings/trading-agents/models
│   ├── 智能体配置                    # /settings/trading-agents/agent-config
│   └── 分析设置                      # /settings/trading-agents/analysis
└── 管理员 (admin)                    # [adminOnly]
    ├── 系统模型管理                  # /admin/system-models
    └── 所有任务管理                  # /admin/all-tasks
```

### 关键架构模式

**1. 用户数据隔离 (强制执行)**
- **MongoDB**: 所有用户相关的文档 **必须** 包含 `user_id` 字段。
- **Redis**: 使用带命名空间的键 (`user:{user_id}:...`)。
- **Service 层**: 所有查询和操作 **必须** 强制过滤 `user_id`，严禁直接查询全表（除非是管理员功能的明确需求）。

**2. RBAC 权限系统** ([`backend/core/auth/rbac.py`](backend/core/auth/rbac.py))
- **角色**: `GUEST` (访客), `USER` (普通用户), `ADMIN` (管理员), `SUPER_ADMIN` (超级管理员)。
- **权限**: 定义了如 `user:read`, `user:create`, `system:config`, `audit:read` 等细粒度权限。
- **使用**: 后端使用 `@require_role()` 或 `@require_permission()` 装饰器；前端路由使用 `meta.adminOnly: true`。

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
- 在 `main.py` 中注册路由。
- **顺序很重要**：核心路由优先，业务模块在后。
- 路由注册顺序：
  1. 核心路由：settings, core_admin, ai_core
  2. 基础设施路由：system, user, user_settings
  3. 业务模块路由：screener, ask_stock, mcp, trading_agents, trading_agents_admin

**5. 应用生命周期管理** ([`backend/main.py`](backend/main.py) - `lifespan`)
- **启动阶段**：
  1. MongoDB 连接
  2. Redis 连接
  3. 定时任务调度器启动
  4. TradingAgents 任务过期处理器启动
  5. TradingAgents 报告归档服务启动
  6. TradingAgents 任务队列启动
  7. 数据库索引初始化
  8. 任务恢复（恢复运行中的任务）
  9. 公共配置初始化
  10. MCP 健康检查器启动
  11. MCP 会话管理器启动
- **关闭阶段**：按相反顺序关闭所有服务

**6. 后台任务系统**
- 使用 `APScheduler` 处理定时任务 ([`backend/core/admin/tasks.py`](backend/core/admin/tasks.py))
- **任务过期处理**: 自动清理 24 小时前的过期任务。
- **报告归档**: 自动归档 30 天前的分析报告。

**7. 日志配置**
- 使用自定义的彩色日志格式化器 ([`backend/core/colored_formatter.py`](backend/core/colored_formatter.py))
- 统一通过 `logging.getLogger(__name__)` 获取日志记录器

**8. 前端模块动态加载**
- 路由配置在 [`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts)
- 采用路由懒加载 (`import(...)`) 优化性能

**9. 配置管理**
- 后端使用 Pydantic Settings ([`backend/core/config.py`](backend/core/config.py))
- 支持 `.env` 文件加载
- 区分开发 (`DEBUG=True`) 和生产环境

## 关键文件路径

| 用途 | 路径 |
|------|------|
| 应用入口 | [`backend/main.py`](backend/main.py) |
| 全局配置 | [`backend/core/config.py`](backend/core/config.py) |
| RBAC 定义 | [`backend/core/auth/rbac.py`](backend/core/auth/rbac.py) |
| 用户模型 | [`backend/core/user/models.py`](backend/core/user/models.py) |
| 安全服务 | [`backend/core/security/`](backend/core/security/) |
| 数据库连接 | [`backend/core/db/`](backend/core/db/) |
| 后台任务入口 | [`backend/background_tasks.py`](backend/background_tasks.py) |
| TradingAgents API | [`backend/modules/trading_agents/api.py`](backend/modules/trading_agents/api.py) |
| TradingAgents 管理员 API | [`backend/modules/trading_agents/admin_api.py`](backend/modules/trading_agents/admin_api.py) |
| 智能体引擎 | [`backend/modules/trading_agents/core/agent_engine.py`](backend/modules/trading_agents/core/agent_engine.py) |
| 任务管理器 | [`backend/modules/trading_agents/core/task_manager.py`](backend/modules/trading_agents/core/task_manager.py) |
| 并发控制器 | [`backend/modules/trading_agents/core/concurrency_controller.py`](backend/modules/trading_agents/core/concurrency_controller.py) |
| MCP 工具过滤器 | [`backend/modules/trading_agents/tools/mcp_tool_filter.py`](backend/modules/trading_agents/tools/mcp_tool_filter.py) |
| 智能体配置模板 | [`backend/modules/trading_agents/config/templates/agents.yaml`](backend/modules/trading_agents/config/templates/agents.yaml) |
| MCP 模块 API | [`backend/modules/mcp/api/routes.py`](backend/modules/mcp/api/routes.py) |
| MCP 连接池 | [`backend/modules/mcp/pool/pool.py`](backend/modules/mcp/pool/pool.py) |
| MCP 适配器 | [`backend/modules/mcp/core/adapter.py`](backend/modules/mcp/core/adapter.py) |
| MCP 默认配置 | [`backend/modules/mcp/config/default_config.yaml`](backend/modules/mcp/config/default_config.yaml) |
| 前端路由加载 | [`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts) |
| 前端 HTTP 客户端 | [`frontend/src/core/api/http.ts`](frontend/src/core/api/http.ts) |

## 用户管理规则

### 用户状态说明

| 状态 | 代码 | 登录权限 | 说明 |
|------|------|----------|------|
| 待审核 | `PENDING` | ❌ 不可登录 | 注册后的默认状态（如开启审核） |
| 已激活 | `ACTIVE` | ✅ 可登录 | 正常使用状态 |
| 已禁用 | `DISABLED` | ❌ 不可登录 | 被管理员手动禁用，数据保留 |
| 已拒绝 | `REJECTED` | ❌ 不可登录 | 审核未通过 |

### 密码重置流程
1. **用户请求**: `/api/users/request-reset` (暂未集成邮件服务，开发环境 Token 会打印在控制台)。
2. **管理员触发**: 管理员可在后台手动触发特定用户的密码重置。
3. **重置操作**: 用户携带 Token 访问重置页面设置新密码。

### 注册审批流程
- **配置项**: `REQUIRE_APPROVAL` (在 `.env` 或 `config.py` 中设置)
- 若为 `True`，新用户状态为 `PENDING`，需管理员在后台点击"通过"。
- 若为 `False`，新用户状态直接为 `ACTIVE`。

### 用户数据隔离规则（强制）
- **MongoDB**: 所有用户数据必须包含 `user_id` 字段
- **Redis**: 使用 `user:{user_id}:...` 格式的键
- **Service 层**: 所有查询必须强制过滤 `user_id`

## API 端点概览

### 系统与认证
- `GET /api/system/status` - 系统状态检查
- `POST /api/system/initialize` - 系统初始化（仅首次可用）
- `POST /api/users/captcha/generate` - 生成图形验证码
- `GET /api/users/captcha/required` - 检查是否需要验证码
- `POST /api/users/register` - 用户注册
- `POST /api/users/login` - 用户登录
- `POST /api/users/logout` - 用户登出
- `POST /api/users/refresh-token` - 刷新令牌
- `GET /api/users/me` - 获取当前用户信息
- `PUT /api/users/me` - 更新当前用户信息

### 管理员接口 (Admin) - 需要 ADMIN/SUPER_ADMIN 权限
- `GET /api/admin/users` - 用户列表
- `POST /api/admin/users` - 创建用户
- `PUT /api/admin/users/{id}` - 更新用户
- `DELETE /api/admin/users/{id}` - 删除用户
- `PUT /api/admin/users/{id}/approve` - 审核通过
- `PUT /api/admin/users/{id}/reject` - 审核拒绝
- `PUT /api/admin/users/{id}/disable` - 禁用用户
- `PUT /api/admin/users/{id}/enable` - 启用用户
- `PUT /api/admin/users/{id}/role` - 修改用户角色（SUPER_ADMIN 专用）
- `POST /api/admin/users/request-reset` - 触发用户密码重置
- `GET /api/admin/audit-logs` - 查看审计日志

### AI 模型管理 (core/ai)
- `GET /api/ai/models` - 获取模型列表
- `POST /api/ai/models` - 创建模型
- `GET /api/ai/models/{id}` - 获取模型详情
- `PUT /api/ai/models/{id}` - 更新模型
- `DELETE /api/ai/models/{id}` - 删除模型
- `POST /api/ai/models/{id}/test` - 测试模型连接
- `PUT /api/ai/models/{id}/default` - 设置为默认模型

### TradingAgents 模块 (用户端)
- `POST /api/trading-agents/tasks` - 创建分析任务（支持单股和批量）
- `GET /api/trading-agents/tasks` - 列出任务
- `GET /api/trading-agents/tasks/{id}` - 获取任务详情
- `POST /api/trading-agents/tasks/{id}/cancel` - 取消/停止任务
- `GET /api/trading-agents/tasks/{id}/stream` - SSE 实时报告流
- `DELETE /api/trading-agents/tasks/{id}` - 删除任务
- `POST /api/trading-agents/tasks/{id}/retry` - 重试失败任务
- `GET /api/trading-agents/tasks/{id}/queue-position` - 获取队列位置
- `GET /api/trading-agents/reports` - 列出报告
- `GET /api/trading-agents/reports/summary` - 获取报告统计摘要
- `GET /api/trading-agents/reports/{id}` - 获取报告详情
- `DELETE /api/trading-agents/reports/{id}` - 删除报告
- `GET /api/trading-agents/agent-config` - 获取智能体配置
- `PUT /api/trading-agents/agent-config` - 更新智能体配置
- `POST /api/trading-agents/agent-config/reset` - 重置为默认配置
- `POST /api/trading-agents/agent-config/export` - 导出配置
- `POST /api/trading-agents/agent-config/import` - 导入配置
- `GET /api/trading-agents/settings` - 获取分析设置
- `PUT /api/trading-agents/settings` - 更新分析设置

### TradingAgents 模块 (管理端) - 需要 ADMIN/SUPER_ADMIN 权限
- `GET /api/trading-agents/agent-config/public` - 获取公共智能体配置
- `PUT /api/trading-agents/agent-config/public` - 更新公共智能体配置
- `GET /api/trading-agents/admin/models` - 获取所有系统模型
- `POST /api/trading-agents/admin/models` - 创建系统模型
- `PUT /api/trading-agents/admin/models/{id}` - 更新系统模型
- `DELETE /api/trading-agents/admin/models/{id}` - 删除系统模型
- `GET /api/trading-agents/admin/all-tasks` - 获取所有任务（跨用户）
- `DELETE /api/trading-agents/admin/all-tasks/{id}` - 删除任意任务
- `POST /api/trading-agents/admin/all-tasks/{id}/cancel` - 取消/停止任意任务

### MCP 模块
- `GET /api/mcp/servers` - 列出 MCP 服务器
- `POST /api/mcp/servers` - 创建 MCP 服务器
- `GET /api/mcp/servers/{id}` - 获取 MCP 服务器详情
- `PUT /api/mcp/servers/{id}` - 更新 MCP 服务器
- `DELETE /api/mcp/servers/{id}` - 删除 MCP 服务器
- `POST /api/mcp/servers/{id}/test` - 测试 MCP 服务器连接
- `GET /api/mcp/servers/{id}/tools` - 获取 MCP 服务器工具列表
- `GET /api/mcp/settings` - 获取 MCP 设置
- `PUT /api/mcp/settings` - 更新 MCP 设置
- `POST /api/mcp/settings/reset` - 重置为默认设置
- `GET /api/mcp/config/default` - 获取默认配置

### WebSocket 端点
- `WS /api/trading-agents/ws/{task_id}?token={access_token}` - 实时任务进度推送

## 新功能开发指南

### 业务模块开发 (modules/)

**后端开发步骤**：
1. 在 `backend/modules/` 下创建新目录
2. 编写以下文件：
   - `api.py` - 路由定义
   - `service.py` - 业务逻辑
   - `models.py` - 数据模型（可选）
3. **必须** 使用 `get_current_user` 依赖注入
4. **必须** 确保所有数据库操作包含 `user_id` 过滤
5. 在 `main.py` 中注册路由（注意顺序）

**前端开发步骤**：
1. 在 `frontend/src/modules/` 下创建视图组件
2. 在 `frontend/src/core/router/module_loader.ts` 中添加路由
3. 创建对应的 API 调用文件（可选）
4. 创建状态管理 Store（可选）

### 核心功能扩展 (core/)
- 修改核心逻辑（如认证、RBAC）需极其谨慎
- 必须运行完整测试套件确保不破坏现有功能
- 更新本文档

## TradingAgents 模块详解

这是本项目的核心业务模块——基于 LangGraph 的多阶段 AI 股票分析系统。

### 四阶段工作流

| 阶段 | 名称 | 描述 | 输出 |
|------|------|------|------|
| 1 | 分析师团队 (Individual Analysis) | 3-4个分析师（技术面、基本面、市场情绪、新闻）并行分析 | 多份独立报告 |
| 2 | 研究与辩论 (Research & Debate) | 看多/看空辩手进行多轮辩论，研究经理裁决 | 辩论总结 |
| 3 | 风险评估 (Risk Assessment) | 激进/保守/中性三方讨论，首席风控官总结 | 风险报告 |
| 4 | 总结报告 (Summary) | 综合所有信息生成最终投资建议 | 最终报告 (买入/卖出/持有) |

### 关键特性

**1. 并发控制**
- **公共模型资源池**：每个模型有独立的并发槽位（max_concurrency）
- **用户级并发限制**：每个用户的任务并发数（task_concurrency）
- **批量任务并发**：批量任务的子任务并发数（batch_concurrency）
- 支持 FIFO 队列和优先级队列
- 实现位于 [`backend/modules/trading_agents/core/concurrency_controller.py`](backend/modules/trading_agents/core/concurrency_controller.py)

**2. 工具循环检测**
- 自动检测并中断连续重复的工具调用（阈值: 3次）
- 防止 AI 陷入死循环
- 实现位于 [`backend/modules/trading_agents/tools/loop_detector.py`](backend/modules/trading_agents/tools/loop_detector.py)

**3. 任务恢复机制**
- 系统重启后自动恢复运行中的任务
- 验证配置快照完整性
- 实现位于 [`backend/modules/trading_agents/core/task_manager_restore.py`](backend/modules/trading_agents/core/task_manager_restore.py)

**4. Token 消耗追踪**
- 记录每个阶段的 Token 用量
- 前端展示预估成本
- 支持输入/输出/总计 Token 统计

**5. WebSocket 实时推送**
- 任务状态变更实时推送到前端
- 支持多客户端连接同一任务
- 心跳保活机制
- 实现位于 [`backend/modules/trading_agents/websocket/manager.py`](backend/modules/trading_agents/websocket/manager.py)

**6. 批量任务管理**
- 支持一次性分析多只股票（1-50只）
- 自动创建批量任务和子任务
- 批量任务状态聚合
- 实现位于 [`backend/modules/trading_agents/core/batch_manager.py`](backend/modules/trading_agents/core/batch_manager.py)

### 多用户配置优先级规则 (Mandatory)

系统支持三层配置优先级，确保灵活性与默认行为的统一：

1. **用户自定义配置**: 若用户修改了配置（`is_customized=True`），优先级最高
2. **系统公共配置**: 若用户未自定义，使用系统公共配置（`user_id="system_public"`）
3. **默认 YAML 模板**: 若公共配置不存在，从代码库中的 YAML 文件重新创建

**实现逻辑参考**:
```python
# 伪代码：获取生效配置
async def get_effective_config(user_id):
    user_config = db.find_one(user_id)
    if user_config and user_config.is_customized:
        return user_config
    
    public_config = db.find_one("system_public")
    if public_config:
        return public_config
        
    return create_from_yaml()
```

### 双模型配置

TradingAgents 支持使用两个不同的 AI 模型：

1. **数据收集模型**（第一阶段）
   - 用于分析师团队的数据收集和分析
   - 需要调用 MCP 工具获取实时数据
   - 通常选择较强且较快的模型

2. **辩论模型**（第二、三、四阶段）
   - 用于研究员辩论、风险评估和总结
   - 不需要调用外部工具，主要是文本生成
   - 通常选择性价比高的模型

**模型选择优先级**：
- 优先级1：任务参数指定（`data_collection_model` / `debate_model`）
- 优先级2：用户模型偏好（用户设置中的默认模型）
- 优先级3：系统默认模型

## MCP 模块

MCP (Model Context Protocol) 模块是系统的独立模块，负责管理与 MCP 服务器的连接和工具调用。

### 模块架构

**目录结构**：
- `api/` - API 层，提供 RESTful 接口
- `pool/` - 连接池，管理服务器连接和队列
- `service/` - 服务层，核心业务逻辑
- `core/` - 核心层，适配器和会话管理
- `config/` - 配置管理

### 核心特性

**1. 连接池管理**
- 支持个人和公共连接池
- 自动重连和错误恢复
- 连接复用和资源优化

**2. 传输协议支持**
- stdio（本地进程）
- http/streamable_http（推荐）
- websocket
- sse（已废弃）

**3. 健康检查**
- 自动检测服务器可用性
- 定期健康检查任务
- 失败自动重试机制

**4. 会话管理**
- 会话生命周期管理
- 会话复用和缓存
- 自动会话清理

**5. 工具容错策略**
- required: 失败阻止任务启动
- optional: 失败跳过该服务器
- 智能体级别的容错配置

### 配置优先级

1. 用户自定义配置（最高）
2. 系统公共配置
3. 默认 YAML 模板（最低）

### 与 TradingAgents 集成

TradingAgents 智能体通过 MCP 工具过滤器调用 MCP 服务器的工具：
- 位于 [`backend/modules/trading_agents/tools/mcp_tool_filter.py`](backend/modules/trading_agents/tools/mcp_tool_filter.py)
- 支持工具级别容错
- 自动工具发现和注册

## 环境与安全配置

### 后端环境变量 (.env)

```bash
# 应用基础
APP_NAME=股票分析平台
APP_VERSION=0.1.0
DEBUG=true
ENVIRONMENT=development
SECRET_KEY=your-secret-key-min-32-chars

# API 配置
API_V1_PREFIX=/api
HOST=0.0.0.0
PORT=8000

# CORS 配置
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["*"]
CORS_ALLOW_HEADERS=["*"]

# MongoDB 配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=stock_analysis
MONGODB_MAX_POOL_SIZE=10
MONGODB_MIN_POOL_SIZE=1
MONGODB_MAX_IDLE_TIME_MS=10000
MONGODB_SERVER_SELECTION_TIMEOUT_MS=30000
MONGODB_SOCKET_TIMEOUT_MS=60000

# Redis 配置
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# JWT 配置
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 密码安全
PASSWORD_MIN_LENGTH=8
BCRYPT_ROUNDS=12

# 限流配置
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD_SECONDS=60

# 登录安全配置
LOGIN_MAX_ATTEMPTS=5
LOGIN_BLOCK_DURATION=1800
LOGIN_FAIL_WINDOW=300

# IP 信任配置
IP_TRUST_THRESHOLD=5
IP_TRUST_EXPIRE_DAYS=30

# 图形验证码配置
CAPTCHA_ENABLED=true
CAPTCHA_EXPIRE_SECONDS=300
CAPTCHA_TOLERANCE=5
CAPTCHA_RATE_LIMIT=10

# 邮箱验证码配置（预留）
EMAIL_CODE_ENABLED=false
EMAIL_CODE_LENGTH=6
EMAIL_CODE_EXPIRE_SECONDS=300
EMAIL_CODE_COOLDOWN=60
EMAIL_CODE_RATE_LIMIT=1

# 注册安全配置
REGISTER_MAX_ATTEMPTS=3
REGISTER_WINDOW_SECONDS=3600

# 用户审核配置
REQUIRE_APPROVAL=true
```

### 前端环境变量 (.env)

```bash
VITE_API_BASE_URL=/api
```

### 安全注意事项

- **密码存储**: 使用 bcrypt (12 rounds) 哈希
- **JWT**: HS256 算法，30分钟有效期
- **数据隔离**: 严格执行 `user_id` 过滤
- **敏感信息**: 智能体提示词 (`prompts`) 等敏感配置仅管理员可见，普通用户接口自动过滤
- **验证码**: 滑块验证码防暴力破解
- **IP 信任**: 常用 IP 登录无感验证
- **限流**: API 请求频率限制

## 已知问题与解决方案

### 1. SSE 换行符转义问题

**现象**: SSE 流输出字面量 `\n\n` 而不是换行。

**解决**: Python f-string 中需使用双反斜杠 `\\n\\n`。

### 2. Vue 组件导入

**现象**: `Failed to resolve component`.

**解决**: 自定义组件（非 Element Plus）必须在 `<script setup>` 中显式 import。

### 3. 并发控制队列位置

**现象**: 批量任务队列位置不准确。

**解决**: 当前为简化实现，建议后续优化为更精确的排队机制。

## 开发注意事项

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

**必须使用日志的场景**（强制）：
- 后端服务（API、微服务）
- CLI 工具
- 定时任务/后台任务
- 数据处理脚本
- 文件/数据库操作代码

**日志级别选择**:
- **ERROR**: 功能异常、需要人工介入（数据库连接失败、API 调用异常、业务规则违反）
- **WARN**: 潜在问题、但程序可继续（配置缺失用默认值、重试后成功、性能降级）
- **INFO**: 关键业务节点（用户登录登出、订单状态变更、任务开始/结束）
- **DEBUG**: 调试信息（入参出参、SQL 语句、缓存命中情况）

**必须添加日志的位置**（强制）:
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

## 部署说明

### Docker 容器化部署（推荐）

**开发环境**:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

**生产环境**:
```bash
docker-compose up -d
```

**实用命令**:
```bash
# 查看日志
docker-compose -f docker-compose.dev.yml logs -f

# 重启服务
docker-compose -f docker-compose.dev.yml restart

# 停止并清理
docker-compose -f docker-compose.dev.yml down -v

# 进入容器
docker exec -it stock-analysis-backend-dev /bin/bash
```

### 本地开发部署

**启动数据库**:
```bash
docker-compose -f docker-compose.dev.yml up -d mongodb redis
```

**启动后端**:
```bash
cd backend
poetry install
poetry run uvicorn main:app --reload
```

**启动前端**:
```bash
cd frontend
npm install
npm run dev
```

## 贡献指南

### 提交规范

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

### 代码审查

- 所有修改必须通过 Lint 检查
- 核心模块修改需要特别谨慎
- 必须更新相关文档

## 版本历史

- **0.1.0**: 初始版本
  - 实现用户认证与授权
  - 实现 TradingAgents 核心功能
  - 实现 MCP 集成
  - 实现多用户数据隔离

## 附录

### 技术栈详解

**后端**:
- FastAPI - 现代异步 Web 框架
- Pydantic - 数据验证和设置管理
- Motor - 异步 MongoDB 驱动
- Redis - 异步 Redis 客户端
- LangGraph - 工作流编排
- LangChain MCP Adapters - MCP 协议适配器
- MCP SDK - MCP 协议支持 (>=1.9.2,<2.0.0)

**前端**:
- Vue 3 - 渐进式 JavaScript 框架
- TypeScript - 类型安全
- Vite - 快速构建工具
- Element Plus - UI 组件库
- Pinia - 状态管理
- Vue Router - 路由管理

**数据库**:
- MongoDB - 文档数据库
- Redis - 缓存和会话存储

**开发工具**:
- Poetry - Python 依赖管理
- npm/Node.js - 前端包管理
- Docker - 容器化
- Docker Compose - 服务编排

### 常用命令速查

**后端**:
```bash
# 安装依赖
poetry install

# 运行开发服务器
poetry run uvicorn main:app --reload

# 运行测试
poetry run pytest

# 代码格式化
poetry run black .

# Lint 检查
poetry run ruff .

# 类型检查
poetry run mypy .
```

**前端**:
```bash
# 安装依赖
npm install

# 运行开发服务器
npm run dev

# 生产构建
npm run build

# 类型检查
npm run type-check

# Lint 检查
npm run lint
```
