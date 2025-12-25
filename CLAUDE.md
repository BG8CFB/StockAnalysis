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
│   │   └── exceptions.py        # Custom exceptions
│   ├── modules/                 # 业务功能模块（可独立扩展）
│   │   ├── stock_analysis/      # 股票分析模块
│   │   ├── news/                # 新闻模块
│   │   ├── trading/             # 交易模块
│   │   └── dashboard/           # 仪表板模块
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
│   │       ├── stock_analysis/  # 股票分析
│   │       ├── news/            # 新闻
│   │       └── dashboard/       # 仪表板
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
│   ├── AI 分析
│   └── 智能选股
├── 新闻资讯 (news)              # modules/news
├── 交易终端 (trading)           # modules/trading
└── 设置 (settings)              # core/settings
    ├── 个人资料                 # 普通用户可访问
    ├── 用户管理                 # adminOnly: true
    └── 系统设置                 # adminOnly: true
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
app.include_router(system_router)   # First (system init check)
app.include_router(user_router)     # Core user routes
app.include_router(admin_router)    # Core admin routes
app.include_router(settings_router) # Core settings routes
app.include_router(stock_router)    # Business modules
app.include_router(news_router)     # Business modules
```

**5. Frontend Module Loading**
- Add routes to [`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts)
- Use lazy loading: `component: () => import('@modules/...')`
- Meta flags: `requiresAuth`, `adminOnly`, `title`

**6. Configuration Management**
- Backend: Pydantic Settings in [`backend/core/config.py`](backend/core/config.py)
- All config accessed via `settings` singleton
- Environment-specific: `settings.is_development`, `settings.is_production`

## Critical File Paths

| Purpose | Path |
|---------|------|
| App entrypoint | [`backend/main.py`](backend/main.py) |
| Config | [`backend/core/config.py`](backend/core/config.py) |
| RBAC | [`backend/core/rbac/rbac.py`](backend/core/rbac/rbac.py) |
| JWT/Security | [`backend/core/auth/security.py`](backend/core/auth/security.py) |
| User model | [`backend/core/user/models.py`](backend/core/user/models.py) |
| User service | [`backend/core/user/service.py`](backend/core/user/service.py) |
| Admin API | [`backend/core/admin/api.py`](backend/core/admin/api.py) |
| MongoDB | [`backend/core/db/mongodb.py`](backend/core/db/mongodb.py) |
| Redis | [`backend/core/db/redis.py`](backend/core/db/redis.py) |
| Frontend router | [`frontend/src/core/router/index.ts`](frontend/src/core/router/index.ts) |
| HTTP client | [`frontend/src/core/api/http.ts`](frontend/src/core/api/http.ts) |
| System design | [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) |

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
- 🔄 Phase 2: Stock Data Integration (FinanceMCP)
- ⏳ Phase 3: AI Analysis, Smart Stock Picker
- ⏳ Phase 4: WebSocket, Performance Optimization

---

## Known Issues & Solutions

### Issue 1: Frontend Component Import Errors

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

### Issue 2: API Parameter Format Mismatch

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

### Issue 3: Missing API Endpoints

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
