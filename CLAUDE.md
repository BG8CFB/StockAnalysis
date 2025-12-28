# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **modular monolith** stock analysis platform supporting multi-user authentication with complete data isolation between users. Built with Vue 3 + FastAPI + MongoDB + Redis.

**Core Features:**
- Multi-user authentication with JWT
- Role-Based Access Control (RBAC): `GUEST`, `USER`, `ADMIN`, `SUPER_ADMIN`
- Complete user data isolation (MongoDB + Redis)
- System initialization flow (first-run admin setup)
- User approval workflow (admin review required before activation)
- Stock analysis with FinanceMCP integration (Tushare API)
- Responsive UI (PC + Mobile)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue 3 + TypeScript + Vite + Element Plus + Pinia |
| Backend | FastAPI + Python 3.11+ + Pydantic |
| Database | MongoDB (Motor async driver) |
| Cache | Redis (hiredis) |
| Auth | JWT (python-jose) + bcrypt |
| Finance Data | FinanceMCP (Tushare API integration) |
| Container | Docker + Docker Compose |

## Development Commands

### Quick Start (Recommended)
```bash
# Windows
scripts\dev.bat

# Linux/Mac
chmod +x scripts/dev.sh && ./scripts/dev.sh
```

### Manual Development

**Start databases:**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

**Backend (Python 3.11+):**
```bash
cd backend
cp .env.example .env
poetry install
poetry run uvicorn main:app --reload
```

**Frontend (Node.js 18+):**
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### Build & Test

**Frontend:**
```bash
npm run build         # Production build
npm run type-check    # TypeScript check
npm run lint          # ESLint
```

**Backend:**
```bash
poetry run pytest     # Run tests
poetry run black .    # Format code
poetry run ruff .     # Lint
poetry run mypy .     # Type check
```

### Docker Production
```bash
docker-compose up -d              # Full stack
docker-compose -f docker-compose.dev.yml up -d  # Dev databases only
```

### Access URLs
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Admin Dashboard: http://localhost:8000/admin (FastAPI Admin UI)
- Health Check: http://localhost:8000/health

## Architecture

### Core vs Modules Distinction (CRITICAL)

**核心原则**：
- `core/` = 项目核心框架（认证、用户、设置、管理员）
- `modules/` = 业务功能模块（股票分析、新闻、交易等可独立扩展的功能）

```
StockAnalysis/
├── backend/
│   ├── core/                    # 核心框架（不模块化）
│   │   ├── auth/                # 认证核心（JWT、密码哈希、依赖注入）
│   │   ├── user/                # 用户核心（模型、服务、状态管理）
│   │   ├── rbac/                # RBAC 核心（角色、权限、检查）
│   │   ├── admin/               # 管理员核心（用户管理、审核、日志）
│   │   ├── settings/            # 设置核心（系统配置、用户偏好）
│   │   ├── db/                  # 数据库连接
│   │   ├── config.py            # Pydantic Settings
│   │   ├── logging_config.py    # 日志配置
│   │   └── exceptions.py        # Custom exceptions
│   ├── modules/                 # 业务功能模块（可独立扩展）
│   │   ├── trading_agents/      # TradingAgents 智能体分析模块
│   │   ├── analysis/            # 分析模块
│   │   ├── task_center/         # 任务中心模块
│   │   ├── screener/            # 智能选股模块
│   │   ├── ask_stock/           # AI 问股模块
│   │   ├── dashboard/           # 仪表板模块
│   │   └── ...
│   └── main.py                  # App factory
├── frontend/
│   ├── src/
│   │   ├── core/                # 核心框架
│   │   │   ├── auth/            # 认证核心（Pinia store）
│   │   │   ├── user/            # 用户核心（类型、接口）
│   │   │   ├── admin/           # 管理员核心
│   │   │   ├── settings/        # 设置核心
│   │   │   ├── api/http.ts      # Axios instance
│   │   │   ├── router/          # Vue Router config
│   │   │   └── layout/          # MainLayout, Sidebar
│   │   └── modules/             # 业务功能模块
│   │       ├── trading_agents/  # TradingAgents 模块
│   │       │   ├── views/       # 页面组件
│   │       │   │   ├── analysis/    # 分析页面
│   │       │   │   ├── task/        # 任务中心
│   │       │   │   └── admin/       # 管理员页面
│   │       │   ├── components/  # 共享组件
│   │       │   ├── api.ts       # API 调用
│   │       │   ├── store.ts     # Pinia store
│   │       │   └── types.ts     # TypeScript 类型
│   │       ├── dashboard/       # 仪表板
│   │       ├── screener/        # 智能选股
│   │       └── ask_stock/       # AI 问股
│   └── vite.config.ts           # Path aliases: @/, @core, @modules
├── FinanceMCP/                  # Finance MCP Server (Tushare)
└── docs/                        # Documentation
```

### 前端导航结构

```
侧边栏菜单：
├── 仪表板 (dashboard)
├── 市场中心 (market)
│   ├── 股票行情
│   └── 基金行情
├── 分析工具 (analysis)
│   ├── 单股分析                 # TradingAgents 单股分析
│   ├── 批量分析                 # TradingAgents 批量分析
│   ├── AI 问股                  # AI 问股模块
│   └── 智能选股                 # 智能选股模块
├── 任务中心 (task-center)       # TradingAgents 任务中心
├── 新闻资讯 (news)              # modules/news
├── 交易终端 (trading)           # modules/trading
└── 设置 (settings)              # core/settings
    ├── 用户管理                 # adminOnly: true
    ├── 系统设置                 # adminOnly: true
    ├── AI 模型管理              # TradingAgents 模型管理
    ├── MCP 服务器管理           # TradingAgents MCP 管理
    ├── 智能体配置               # TradingAgents 智能体配置
    └── 分析设置                 # TradingAgents 分析设置
```

### Key Architectural Patterns

**1. User Data Isolation (Mandatory)**
- MongoDB: All user documents MUST include `user_id` field
- Redis: Use `UserRedisKey` class for namespaced keys (`user:{user_id}:...`)
- Service layer MUST enforce `user_id` filtering

**2. RBAC System** ([`backend/core/rbac/rbac.py`](backend/core/rbac/rbac.py))
- Roles: `GUEST`, `USER`, `ADMIN`, `SUPER_ADMIN`
- Permissions: `user:read`, `user:create`, `user:approve`, `system:config`, `stock:analyze`, etc.
- Use `require_role()` or `require_permission()` decorators
- Frontend: Set `meta.adminOnly: true` for admin-only routes

```python
# Role hierarchy (higher = more permissions)
SUPER_ADMIN > ADMIN > USER > GUEST

# Permission check example
from core.rbac.rbac import Role, Permission, has_permission
if has_permission(Role.ADMIN, Permission.USER_DELETE):
    # Can delete users
```

**3. User Status Workflow**
```
注册 → PENDING (待审核)
       ↓
    管理员审核
       ↓
    ├─ APPROVE → ACTIVE (已激活，可登录)
    ├─ REJECT → REJECTED (已拒绝，1天后自动清除数据)
    └─ 禁用 → DISABLED (不清除数据，管理员可恢复)
```

**4. Backend Module Registration**
```python
# In main.py - router registration order matters!
app.include_router(settings_router)   # System settings (first)
app.include_router(core_admin_router) # Core admin
app.include_router(system_router)     # System init check
app.include_router(user_router)       # Core user routes
app.include_router(trading_agents_router)     # TradingAgents
app.include_router(trading_agents_admin_router)  # TradingAgents Admin
# ... other business modules
```

**5. Background Tasks System**
The project uses APScheduler for scheduled tasks:
- Task expiry handler: Auto-fails tasks older than 24 hours
- Report archival service: Archives reports older than 30 days
- Scheduler configured in [`backend/core/admin/tasks.py`](backend/core/admin/tasks.py)

**6. Logging Configuration**
- Colored console formatter: [`backend/core/colored_formatter.py`](backend/core/colored_formatter.py)
- Logging setup: [`backend/core/logging_config.py`](backend/core/logging_config.py)
- All modules use `logging.getLogger(__name__)`

**7. Frontend Module Loading**
- Add routes to [`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts)
- Use lazy loading: `component: () => import('@modules/...')`
- Meta flags: `requiresAuth`, `adminOnly`, `title`

**8. Configuration Management**
- Backend: Pydantic Settings in [`backend/core/config.py`](backend/core/config.py)
- All config accessed via `settings` singleton
- Environment-specific: `settings.is_development`, `settings.is_production`

## Critical File Paths

| Purpose | Path |
|---------|------|
| App entrypoint | [`backend/main.py`](backend/main.py) |
| Config | [`backend/core/config.py`](backend/core/config.py) |
| RBAC | [`backend/core/auth/rbac.py`](backend/core/auth/rbac.py) |
| JWT/Security | [`backend/core/auth/security.py`](backend/core/auth/security.py) |
| User model | [`backend/core/user/models.py`](backend/core/user/models.py) |
| User service | [`backend/core/user/service.py`](backend/core/user/service.py) |
| Admin API | [`backend/core/admin/api.py`](backend/core/admin/api.py) |
| MongoDB | [`backend/core/db/mongodb.py`](backend/core/db/mongodb.py) |
| Redis | [`backend/core/db/redis.py`](backend/core/db/redis.py) |
| Logging setup | [`backend/core/logging_config.py`](backend/core/logging_config.py) |
| Background tasks | [`backend/core/admin/tasks.py`](backend/core/admin/tasks.py) |
| Frontend router | [`frontend/src/core/router/index.ts`](frontend/src/core/router/index.ts) |
| Frontend module loader | [`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts) |
| HTTP client | [`frontend/src/core/api/http.ts`](frontend/src/core/api/http.ts) |
| TradingAgents API | [`backend/modules/trading_agents/api.py`](backend/modules/trading_agents/api.py) |
| TradingAgents Engine | [`backend/modules/trading_agents/core/agent_engine.py`](backend/modules/trading_agents/core/agent_engine.py) |
| TradingAgents Task Manager | [`backend/modules/trading_agents/core/task_manager.py`](backend/modules/trading_agents/core/task_manager.py) |
| TradingAgents Concurrency | [`backend/modules/trading_agents/core/concurrency_controller.py`](backend/modules/trading_agents/core/concurrency_controller.py) |
| TradingAgents WebSocket | [`backend/modules/trading_agents/websocket/manager.py`](backend/modules/trading_agents/websocket/manager.py) |
| System design | [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) |
| Fix report | [`docs/FixReport.md`](docs/FixReport.md) |

## User Management Rules

### User Status States

| 状态 | 代码 | 登录权限 | 数据处理 |
|------|------|----------|----------|
| 待审核 | `PENDING` | ❌ 不可登录 | 保留 |
| 已激活 | `ACTIVE` | ✅ 可登录 | 保留 |
| 已禁用 | `DISABLED` | ❌ 不可登录 | 保留 |
| 已拒绝 | `REJECTED` | ❌ 不可登录 | 1天后自动清除 |

### Password Reset Workflow

**管理员无法直接查看或修改用户密码**，但可以触发密码重置流程：

1. **管理员发起重置** → 生成带 token 的重置链接
2. **系统发送邮件** → 用户收到重置链接（预留接口，当前开发环境打印到控制台）
3. **用户点击链接** → 跳转到重置密码页面
4. **用户输入新密码** → 完成重置

**安全措施**：
- 重置 token 有效期：1小时
- Token 使用后立即失效
- 接口需验证码保护（防暴力调用）
- 记录所有重置操作审计日志

### Approval Workflow

**默认行为**：注册后状态为 `PENDING`，需管理员审核

**管理员配置选项**：
- `REQUIRE_APPROVAL`: 是否需要审核（`true`/`false`）
- 设置为 `false` 时，注册后自动激活

**审核 API**：
- `PUT /api/admin/users/{id}/approve` - 通过审核
- `PUT /api/admin/users/{id}/reject` - 拒绝（需填写原因）
- `PUT /api/admin/users/{id}/disable` - 禁用用户
- `PUT /api/admin/users/{id}/enable` - 启用用户

## API Endpoints

### System
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/system/initialize` | First-run admin setup | Public (once) |
| GET | `/api/system/status` | System status | Authenticated |
| PUT | `/api/system/config` | Update system config | ADMIN |

### User Management
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/users/register` | User registration | Public |
| POST | `/api/users/login` | User login | Public |
| GET | `/api/users/me` | Current user info | Authenticated |
| PUT | `/api/users/me` | Update profile | Authenticated |
| POST | `/api/users/request-reset` | Request password reset | Public |
| POST | `/api/users/reset-password` | Reset password with token | Public |

### Admin (User Management)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/admin/users` | List users (filterable) | ADMIN |
| GET | `/api/admin/users/pending` | Pending approvals | ADMIN |
| PUT | `/api/admin/users/{id}/approve` | Approve user | ADMIN |
| PUT | `/api/admin/users/{id}/reject` | Reject user | ADMIN |
| PUT | `/api/admin/users/{id}/disable` | Disable user | ADMIN |
| PUT | `/api/admin/users/{id}/enable` | Enable user | ADMIN |
| POST | `/api/admin/users/{id}/reset-password` | Trigger password reset | ADMIN |
| GET | `/api/admin/audit-logs` | Audit logs | ADMIN |
| PUT | `/api/admin/users/{id}/role` | Change role | SUPER_ADMIN |

### Settings
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/settings/system` | Get system config | ADMIN |
| PUT | `/api/settings/system` | Update system config | SUPER_ADMIN |

## Adding New Features

### Business Module (modules/)

**Backend Module:**
1. Create `backend/modules/your_module/` with `api.py`, `service.py`, `__init__.py`
2. Use `get_current_user` dependency for authenticated routes
3. Import router in `main.py`: `app.include_router(your_router, prefix=settings.API_V1_PREFIX)`
4. Add RBAC decorators if needed: `@require_role(Role.ADMIN)`

**Frontend Module:**
1. Create `frontend/src/modules/your_module/views/YourView.vue`
2. Add route to `module_loader.ts` under appropriate section
3. Optional: Create `api.ts` (API calls) and `store.ts` (Pinia store)

**Example Backend Route:**
```python
from fastapi import APIRouter, Depends
from core.auth.dependencies import get_current_user
from core.user.models import UserModel

router = APIRouter(prefix="/news", tags=["News"])

@router.get("/articles")
async def get_articles(current_user: UserModel = Depends(get_current_user)):
    # user_id filtering is mandatory
    return await service.get_user_articles(user_id=str(current_user.id))
```

### Core Extension (core/)

**修改核心逻辑时需要**：
1. 确认影响范围（核心逻辑影响全局）
2. 更新 CLAUDE.md 文档
3. 运行完整测试套件
4. 考虑向后兼容性

## FinanceMCP Integration

The project includes FinanceMCP - a professional finance data MCP server based on Tushare API.

**Available Tools:**
- `stock_data` - Stock quotes + technical indicators (MACD, RSI, KDJ, BOLL, MA)
- `company_performance` - A-share financial statements
- `company_performance_hk` - HK stock financials
- `company_performance_us` - US stock financials
- `fund_data` - Fund NAV, holdings, dividends
- `macro_econ` - Macro indicators (GDP, CPI, PMI...)
- `finance_news` - Financial news search
- `money_flow` - Capital flow analysis
- And more...

## TradingAgents Module (AI-Powered Stock Analysis)

The **TradingAgents** module is the core business feature - a multi-phase AI agent system for stock analysis using LangGraph.

### Architecture Overview

```
modules/trading_agents/
├── agents/                    # AI Agents (4 phases)
│   ├── base.py               # BaseAgent class
│   ├── phase1/               # Phase 1: Individual Analysts
│   │   ├── analysts.py       # Fundamental, Technical, Market analysts
│   ├── phase2/               # Phase 2: Research & Debate
│   │   ├── research_manager.py
│   │   ├── debaters.py       # Bull/Bear debaters
│   │   └── debate_manager.py
│   ├── phase3/               # Phase 3: Risk Assessment
│   │   ├── risk_analysts.py  # Market, Liquidity, Concentration risk
│   │   └── risk_manager.py
│   ├── phase4/               # Phase 4: Summary & Recommendation
│   │   └── summary.py        # Final report generator
├── core/
│   ├── agent_engine.py       # LangGraph workflow engine
│   ├── task_manager.py       # Task lifecycle management
│   ├── concurrency_controller.py  # Public model resource pool
│   ├── task_queue.py         # Background task queue
│   ├── state.py              # Workflow state management
│   ├── exceptions.py         # Custom exceptions
│   ├── alerts.py             # Alert system
│   ├── database.py           # MongoDB collections
│   └── task_expiry.py        # Task expiration handler
├── services/
│   ├── model_service.py      # AI model configuration
│   ├── mcp_service.py        # MCP server management
│   ├── agent_config_service.py  # Agent configuration
│   ├── report_service.py     # Report storage & query
│   ├── mcp_health_checker.py # MCP health monitoring
│   └── mcp_session_manager.py # MCP session management
├── tools/
│   ├── registry.py           # Tool registry with timeout
│   ├── loop_detector.py      # Tool loop detection
│   ├── mcp_adapter.py        # MCP tool adapter
│   └── local_tools.py        # Local tool implementations
├── llm/
│   ├── provider.py           # LLM provider interface
│   └── openai_compat.py      # OpenAI-compatible adapter
├── websocket/
│   ├── manager.py            # WebSocket connection manager
│   └── events.py             # Event definitions
├── api.py                    # Main API routes
├── admin_api.py              # Admin-only routes
└── schemas.py                # Pydantic models
```

### Four-Phase Workflow

| Phase | Name | Description | Output |
|-------|------|-------------|--------|
| 1 | Individual Analysis | 3 analysts (Fundamental, Technical, Market) analyze in parallel | 3 independent reports |
| 2 | Research & Debate | Research manager + Bull/Bear debaters debate (configurable rounds) | Debate summary |
| 3 | Risk Assessment | Risk analysts assess market/liquidity/concentration risk | Risk report |
| 4 | Summary | Synthesizes all reports into final recommendation | Final report with BUY/SELL/HOLD |

### Key Features

**1. Concurrency Control**
- Public model resource pool (default: 5 concurrent slots)
- Per-user limit: 1 slot per model
- Batch task limit: 5 concurrent tasks
- FIFO and priority queues supported
- TTL locks with Watchdog auto-renewal
- Force Release mechanism for deadlocks

**2. Tool Loop Detection**
- Detects consecutive identical tool calls (threshold: 3)
- Automatically disables problematic tools
- Prevents infinite loops in agent workflows

**3. Task Recovery**
- Automatic recovery on system restart
- Validates configuration snapshot integrity
- Validates agent existence (fails task if agent deleted)
- Preserves completed reports
- Tasks reset to PENDING for re-execution

**4. Token Tracking**
- Records prompt/completion tokens per LLM call
- Aggregates to task level
- Stores in MongoDB
- Frontend displays with estimated cost (¥)

**5. Real-time Communication**
- WebSocket for task progress updates
- SSE for streaming final report
- Heartbeat mechanism (30s interval)
- Max 5 WebSocket connections per user

**6. Alert System**
8 alert types: `tool_loop`, `quota_exhausted`, `mcp_unavailable`, `task_timeout`, `batch_failure`, `token_anomaly`, `model_error`, `task_failed`
4 severity levels: INFO, WARNING, ERROR, CRITICAL
Admin alert panel with timeline and list views

**7. MCP Server Management (基于官方 langchain-mcp-adapters)**
使用官方 LangChain MCP 适配器框架 (langchain-mcp-adapters >= 0.1.10)
支持 4 种传输模式：
- stdio: 标准输入输出（本地进程）
- sse: Server-Sent Events
- streamable_http: Streamable HTTP（推荐）
- websocket: WebSocket
自动健康检查、会话管理、工具发现与调用
支持 Bearer Token 和 Basic Auth 认证

**8. Tool Timeout Protection**
30-second timeout for tool calls
Automatic continuation after timeout
`ToolTimeoutException` for error handling

**9. MCP Bug Patching**

MCP Python SDK 和第三方服务器存在兼容性问题，已通过 monkey patch 修复：

### 已知问题与修复

**问题 1：空 SSE 数据导致 ValidationError**（Issue #1672）
- **症状**：`ValidationError: Invalid JSON: EOF while parsing a value`
- **原因**：MCP 服务器发送空 priming events，Python 客户端尝试解析为 JSON
- **修复**：在解析前检查 SSE 数据是否为空，跳过空数据

**问题 2：streamable_http ClosedResourceError**（Issue #1190）
- **症状**：`ClosedResourceError in streamable_http.py`
- **原因**：v1.12.0+ 的资源管理问题
- **修复**：通过 monkey patch 缓解（待官方修复）

**问题 3：自定义错误响应格式不兼容**（Finance MCP 服务器）
- **症状**：`ValidationError: 11 validation errors for JSONRPCMessage`
- **原因**：Finance MCP 返回 `{code: 1001, msg: "...", success: false}`，不符合 JSON-RPC 2.0 标准
- **修复**：检测自定义格式并记录日志，避免崩溃

### 补丁实现

**位置**：`backend/modules/trading_agents/services/mcp_patch.py`

**修复内容**：
```python
def apply_mcp_patches() -> None:
    """应用所有 MCP 补丁"""
    patches_applied = []

    # 1. 修复空 SSE 数据解析
    _patch_streamable_http_empty_sse()
    patches_applied.append("空 SSE 数据解析修复")

    # 2. 修复自定义错误响应格式
    _patch_streamable_http_custom_error_format()
    patches_applied.append("自定义错误响应格式兼容")

    logger.info(f"✅ MCP 补丁已应用: {', '.join(patches_applied)}")
```

**应用方式**（已在 `main.py` 中集成）：
```python
from modules.trading_agents.services.mcp_patch import apply_mcp_patches
apply_mcp_patches()  # 应用启动时自动调用
```

### 参考链接
- https://github.com/modelcontextprotocol/python-sdk/issues/1672
- https://github.com/modelcontextprotocol/python-sdk/issues/1190
- https://github.com/FlowLLM-AI/finance-mcp (Finance MCP 服务器)

### API Endpoints (TradingAgents)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/trading-agents/tasks` | Create single analysis task | Authenticated |
| POST | `/api/trading-agents/tasks/batch` | Create batch analysis | Authenticated |
| GET | `/api/trading-agents/tasks` | List user tasks | Authenticated |
| GET | `/api/trading-agents/tasks/{id}` | Get task details | Authenticated |
| DELETE | `/api/trading-agents/tasks/{id}` | Delete task | Authenticated |
| POST | `/api/trading-agents/tasks/{id}/cancel` | Cancel task | Authenticated |
| POST | `/api/trading-agents/tasks/{id}/retry` | Retry failed task | Authenticated |
| GET | `/api/trading-agents/tasks/{id}/stream` | SSE report stream | Authenticated |
| WS | `/api/trading-agents/ws/{task_id}` | WebSocket connection | Authenticated (token) |
| GET | `/api/trading-agents/models` | List AI models | Authenticated |
| POST | `/api/trading-agents/models` | Create AI model config | Authenticated |
| GET | `/api/trading-agents/mcp-servers` | List MCP servers | Authenticated |
| POST | `/api/trading-agents/mcp-servers` | Create MCP server config | Authenticated |
| GET | `/api/trading-agents/reports` | List reports | Authenticated |
| GET | `/api/trading-agents/agent-config` | Get agent config | Authenticated |

### Frontend Views (TradingAgents)

| Path | Component | Description | Access |
|------|-----------|-------------|--------|
| `/trading-agents/analysis/single` | SingleAnalysisView | Single stock analysis | Authenticated |
| `/trading-agents/analysis/batch` | BatchAnalysisView | Batch stock analysis | Authenticated |
| `/trading-agents/analysis/:taskId` | AnalysisDetailView | Task detail with live updates | Authenticated |
| `/trading-agents/tasks` | TaskListView | Task center with filters | Authenticated |
| `/trading-agents/reports` | ReportListView | Report library | Authenticated |
| `/settings/trading-agents/models` | ModelManagementView | AI model management | Authenticated |
| `/settings/trading-agents/mcp-servers` | MCPServerManagementView | MCP server management | Authenticated |
| `/settings/trading-agents/agent-config` | AgentConfigView | Agent configuration | Authenticated |
| `/admin/all-tasks` | AllTasksView | All users' tasks | Admin only |
| `/admin/system-models` | SystemModelView | System AI models | Admin only |

### Environment Variables (TradingAgents)

```bash
# TradingAgents基础配置
TRADING_AGENTS_ENABLED=true
TRADING_AGENTS_DEFAULT_MODEL_PROVIDER=zhipu
TRADING_AGENTS_MAX_TASK_QUEUE_SIZE=100
TRADING_AGENTS_TASK_TIMEOUT_SECONDS=3600

# 公共模型配置
TRADING_AGENTS_PUBLIC_MODEL_CONCURRENCY=5
TRADING_AGENTS_PUBLIC_MODEL_QUEUE_TIMEOUT=300
TRADING_AGENTS_BATCH_TASK_LIMIT=5

# 工具循环检测
TRADING_AGENTS_TOOL_LOOP_THRESHOLD=3
TRADING_AGENTS_TOOL_CALL_TIMEOUT=30

# MCP配置
TRADING_AGENTS_MCP_CONNECTION_TIMEOUT=10
TRADING_AGENTS_MCP_AUTO_CHECK_ON_STARTUP=true
TRADING_AGENTS_MCP_STDIO_POOL_SIZE=3

# 任务过期配置
TRADING_AGENTS_TASK_EXPIRY_HOURS=24

# 报告归档配置
TRADING_AGENTS_REPORT_ARCHIVE_DAYS=30
```

### Important Notes

**SSE String Escaping** (CRITICAL):
When using SSE streaming in Python f-strings, escape `\n\n` as `\\n\\n`:
```python
# ✅ Correct
yield f"data: {json.dumps(...)}\\n\\n"

# ❌ Wrong - literal "\n\n" will be output
yield f"data: {json.dumps(...)}\n\n"
```

**Task Status Support**:
When handling SSE streams, support all task statuses:
```python
["failed", "cancelled", "stopped", "expired", "completed"]
```

**MongoDB Collections**:
- `analysis_tasks` - Task metadata and status
- `analysis_reports` - Final analysis reports
- `ai_models` - AI model configurations
- `mcp_servers` - MCP server configurations
- `agent_configs` - Agent configurations
- `alerts` - System alerts

## Environment Variables

**Backend (.env):**
```bash
# App
APP_NAME=StockAnalysis
DEBUG=true
SECRET_KEY=your-secret-key-min-32-chars

# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=stock_analysis
REDIS_URL=redis://localhost:6379

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30

# User Approval
REQUIRE_APPROVAL=true    # Require admin approval for new users
```

**Frontend (.env):**
```bash
VITE_API_BASE_URL=/api
```

## Security Notes

- Passwords: bcrypt with 12 rounds, **admins cannot view passwords**
- JWT: HS256, 30-min expiry, includes role claim
- System init: Disabled after first admin creation
- RBAC: Enforced at route level via decorators
- Data isolation: All queries filtered by `user_id`
- Audit logs: All admin actions permanently logged
- Password reset: Token-based, 1-hour expiry, rate-limited

## Development Phases

- ✅ Phase 1: Auth, RBAC, System Init, User Management
- ✅ Phase 1.5: User Approval Workflow, Admin Dashboard
- ✅ Phase 2: Stock Data Integration (FinanceMCP)
- ✅ Phase 3: TradingAgents - AI Analysis System (95% complete)
- ⏳ Phase 4: WebSocket enhancements, Performance Optimization

---

## Known Issues & Solutions

### Issue 1: SSE String Escaping in Python

**Problem**: SSE streaming outputs literal `\n\n` instead of newlines.

**Root Cause**: In Python f-strings, `\n\n` is interpreted as a literal string, not escape sequences.

**Solution**: Double-escape the newline characters in SSE:
```python
# ✅ Correct
yield f"data: {json.dumps(...)}\\n\\n"

# ❌ Wrong - outputs literal "\n\n"
yield f"data: {json.dumps(...)}\n\n"
```

### Issue 2: Frontend Component Import Errors

**Problem**: `Vue warn: Failed to resolve component: Sidebar`

**Root Cause**: Vue component used without explicit import. The `unplugin-vue-components` plugin only auto-imports Element Plus components, not custom components.

**Solution**: Always explicitly import custom Vue components in `<script setup>`:

```vue
<script setup lang="ts">
import Sidebar from './components/Sidebar.vue'  // Required!
</script>

<template>
  <Sidebar />  <!-- Now works -->
</template>
```

### Issue 3: API Parameter Format Mismatch

**Problem**: `422 Unprocessable Content` when calling `PUT /api/admin/users/{id}/role`

**Root Cause**: Backend expects Query parameter `?new_role=ROLE`, but frontend sent Body `{ role }`.

**Solution**: Match frontend API call to backend parameter type:
```typescript
// ✅ Correct (Query parameter)
changeUserRole: (id: string, role: string) =>
  httpPut(`/admin/users/${id}/role?new_role=${role}`, {})

// ❌ Wrong (Request Body)
changeUserRole: (id: string, role: string) =>
  httpPut(`/admin/users/${id}/role`, { role })
```

**Rule**: When backend uses `Query(...)`, frontend must use URL parameters. When backend uses `Body(...)`, frontend must send request body.

### Issue 4: Missing API Endpoints

**Problem**: `404 Not Found` for `/api/users/me/preferences`

**Root Cause**: Frontend called an API that didn't exist in backend.

**Solution**: Implement the missing endpoints in backend:
```python
@router.get("/users/me/preferences")
async def get_user_preferences(current_user: UserModel = Depends(get_current_active_user)):
    preferences = await user_service.get_preferences(str(current_user.id))
    return preferences

@router.put("/users/me/preferences")
async def update_user_preferences(
    preferences: dict,
    current_user: UserModel = Depends(get_current_active_user)
):
    updated = await user_service.update_preferences(str(current_user.id), preferences)
    return updated
```

---

## Important Development Notes

### Frontend Component Imports

1. **Custom components MUST be explicitly imported**
   - `unplugin-vue-components` only handles Element Plus
   - Custom components like `Sidebar`, `Header`, etc. need manual import

2. **Component naming for debugging**
   ```vue
   <script setup>
   import Sidebar from './Sidebar.vue'
   Sidebar.name = 'Sidebar'  // Helps with Vue DevTools
   </script>
   ```

### API Parameter Consistency

1. **Check backend parameter type before implementing frontend**
   - `Query(...)` → Use URL parameters: `?key=value`
   - `Body(...)` → Use request body: `payload`
   - `Path(...)` → Use URL path: `/resource/{id}`

2. **Test API endpoints before frontend integration**
   - Use Swagger UI at http://localhost:8000/docs
   - Verify parameter types and response formats

### Response Format Consistency

1. **Backend response formats must match frontend expectations**
   - If frontend expects `UserPreferences`, backend should return that type directly
   - Avoid wrapping in `{ success, data }` unless consistently used throughout

2. **Error handling**
   - Use proper HTTP status codes (400, 401, 403, 404, 422, 500)
   - Return meaningful error messages in `detail` field

---

## TradingAgents Development Notes

### Task Lifecycle

```
CREATED → PENDING → QUEUED → RUNNING → COMPLETED
                    ↓         ↓
                  CANCELLED  FAILED
                              ↓
                            EXPIRED (24h)
```

### Modifying Agent Behavior

When modifying agents in `modules/trading_agents/agents/`:
1. Keep the `BaseAgent` interface unchanged
2. Use `config_snapshot` for runtime configuration
3. Return structured reports (dict with `content`, `confidence`, `reasoning`)
4. Handle `ToolTimeoutException` gracefully

### Adding New Tools

1. Add tool handler to `tools/local_tools.py`
2. Register in `tools/registry.py`
3. Add to MCP adapter if needed
4. Update agent prompts to mention new tools

### Testing TradingAgents

```bash
# Run unit tests
cd backend
poetry run pytest modules/trading_agents/tests/

# Run specific test
poetry run pytest modules/trading_agents/tests/test_task_manager.py

# Run property tests
poetry run pytest modules/trading_agents/tests/property_tests.py -v
```

### Common Pitfalls

1. **Forgetting user_id filtering**: All database queries MUST filter by `user_id`
2. **Missing configuration snapshot**: Tasks must save `config_snapshot` for recovery
3. **Not handling expired tasks**: SSE streams must handle `expired` status
4. **Hardcoding model IDs**: Use `get_model_service()` to get user's configured model
5. **Blocking async operations**: Always use `await` for I/O operations

### Performance Considerations

- **Concurrent tasks**: Public models limited to 5 concurrent slots
- **Tool timeout**: 30-second timeout prevents hanging
- **WebSocket limits**: Max 5 connections per user
- **Task expiry**: Auto-fail tasks after 24 hours
- **Report archival**: Auto-archive reports older than 30 days
