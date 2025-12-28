# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在处理本项目代码时提供指导。

## 项目概览

这是一个 **模块化单体 (Modular Monolith)** 股票分析平台，支持多用户认证和完全的用户数据隔离。基于 Vue 3 + FastAPI + MongoDB + Redis 构建。

**核心特性：**
- 基于 JWT 的多用户认证系统
- 基于角色的访问控制 (RBAC)：`GUEST`, `USER`, `ADMIN`, `SUPER_ADMIN`
- 完整的用户数据隔离 (MongoDB + Redis)
- 系统初始化流程 (首次运行设置管理员)
- 用户注册审批工作流 (管理员审核后激活)
- 股票分析功能，集成 FinanceMCP (Tushare API)
- 响应式 UI 设计 (PC + 移动端适配)
- 智能体交易分析 (TradingAgents 模块)

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia |
| 后端 | FastAPI + Python 3.11+ + Pydantic |
| 数据库 | MongoDB (Motor 异步驱动) |
| 缓存 | Redis (hiredis) |
| 认证 | JWT (python-jose) + bcrypt |
| 金融数据 | FinanceMCP (Tushare API 集成) |
| 容器化 | Docker + Docker Compose |

## 开发命令

### 快速开始 (推荐)
```bash
# Windows
scripts\dev.bat

# Linux/Mac
chmod +x scripts/dev.sh && ./scripts/dev.sh
```

### 手动开发

**启动数据库：**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

**后端 (Python 3.11+)：**
```bash
cd backend
cp .env.example .env
poetry install
poetry run uvicorn main:app --reload
```

**前端 (Node.js 18+)：**
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### 构建与测试

**前端：**
```bash
npm run build         # 生产环境构建
npm run type-check    # TypeScript 类型检查
npm run lint          # ESLint 代码检查
```

**后端：**
```bash
poetry run pytest     # 运行测试
poetry run black .    # 代码格式化
poetry run ruff .     # 代码 Lint 检查
poetry run mypy .     # 类型检查
```

### Docker 生产环境部署
```bash
docker-compose up -d              # 启动全栈服务
docker-compose -f docker-compose.dev.yml up -d  # 仅启动开发数据库
```

### 访问地址
- 前端页面: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 管理员仪表板: http://localhost:8000/admin (FastAPI Admin UI)
- 健康检查: http://localhost:8000/health

## 架构设计

### 核心与模块的区别 (关键)

**核心原则**：
- `core/` = 项目核心框架（认证、用户、设置、管理员、安全、AI 基础），不可随意修改。
- `modules/` = 业务功能模块（股票分析、TradingAgents、仪表板等），可独立扩展。

```
StockAnalysis/
├── backend/
│   ├── core/                    # 核心框架（非模块化部分）
│   │   ├── admin/               # 管理员核心（用户管理、审核、日志）
│   │   ├── ai/                  # AI 基础（LLM 提供商、模型服务）
│   │   ├── auth/                # 认证核心（JWT、密码哈希、RBAC）
│   │   ├── db/                  # 数据库连接 (MongoDB, Redis)
│   │   ├── security/            # 安全模块 (验证码、IP 信任、限流)
│   │   ├── settings/            # 设置核心（系统配置）
│   │   ├── system/              # 系统初始化与状态
│   │   ├── user/                # 用户核心（模型、服务、配置）
│   │   ├── config.py            # Pydantic 全局配置
│   │   ├── logging_config.py    # 日志配置
│   │   └── exceptions.py        # 自定义异常
│   ├── modules/                 # 业务功能模块（可插拔）
│   │   ├── trading_agents/      # TradingAgents 智能体分析核心模块
│   │   ├── analysis/            # 基础分析模块
│   │   ├── task_center/         # 任务中心模块
│   │   ├── screener/            # 智能选股模块
│   │   ├── ask_stock/           # AI 问股模块
│   │   ├── dashboard/           # 仪表板模块
│   │   └── ...
│   └── main.py                  # 应用入口与路由注册
├── frontend/
│   ├── src/
│   │   ├── core/                # 前端核心框架
│   │   │   ├── auth/            # 认证（登录、注册、Store）
│   │   │   ├── admin/           # 管理员视图与逻辑
│   │   │   ├── api/http.ts      # Axios 实例与拦截器
│   │   │   ├── router/          # Vue Router 配置
│   │   │   └── layout/          # 布局组件 (MainLayout, Sidebar)
│   │   └── modules/             # 业务功能模块前端实现
│   │       ├── trading_agents/  # TradingAgents 模块
│   │       │   ├── views/       # 页面视图 (分析、任务、配置)
│   │       │   ├── components/  # 模块组件
│   │       │   ├── store.ts     # 状态管理
│   │       │   └── api.ts       # API 调用
│   │       ├── dashboard/       # 仪表板视图
│   │       ├── screener/        # 选股视图
│   │       └── ask_stock/       # 问股视图
│   └── vite.config.ts           # 路径别名配置: @/, @core, @modules
├── FinanceMCP/                  # Finance MCP 服务器 (Tushare 数据源)
└── docs/                        # 项目文档
```

### 前端导航结构

对应 `frontend/src/core/router/module_loader.ts` 中的配置：

```
侧边栏菜单：
├── 仪表板 (dashboard)           # @modules/dashboard
├── 智能选股 (screener)          # @modules/screener
├── AI 问股 (ask-stock)          # @modules/ask_stock
├── TradingAgents 分析工具
│   ├── 单股分析                 # /trading-agents/analysis/single
│   ├── 批量分析                 # /trading-agents/analysis/batch
│   └── 任务中心                 # /trading-agents/tasks
├── 设置 (settings)
│   ├── 用户管理                 # adminOnly: true (@core/admin)
│   ├── 系统设置                 # adminOnly: true (@core/settings)
│   ├── AI 模型管理              # @modules/trading_agents
│   ├── MCP 服务器管理           # @modules/trading_agents
│   ├── 智能体配置               # @modules/trading_agents
│   └── 分析设置                 # @modules/trading_agents
└── 管理员 (admin)               # adminOnly: true
    ├── 系统模型管理             # @modules/trading_agents
    └── 所有任务管理             # @modules/trading_agents
```

### 关键架构模式

**1. 用户数据隔离 (强制执行)**
- **MongoDB**: 所有用户相关的文档 **必须** 包含 `user_id` 字段。
- **Redis**: 使用 `UserRedisKey` 类生成带命名空间的键 (`user:{user_id}:...`)。
- **Service 层**: 所有查询和操作 **必须** 强制过滤 `user_id`，严禁直接查询全表（除非是管理员功能的明确需求）。

**2. RBAC 权限系统** ([`backend/core/auth/rbac.py`](backend/core/auth/rbac.py))
- **角色**: `GUEST` (访客), `USER` (普通用户), `ADMIN` (管理员), `SUPER_ADMIN` (超级管理员)。
- **权限**: 定义了如 `user:read`, `system:config` 等细粒度权限。
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

**4. 后端模块注册机制**
- 在 `backend/main.py` 中注册路由。
- 顺序很重要：核心路由 (Admin, Auth) 优先，业务模块 (TradingAgents 等) 在后。
- 生命周期管理 (`lifespan`)：统一处理数据库连接、调度器启动、MCP 服务初始化等。

**5. 后台任务系统**
- 使用 `APScheduler` 处理定时任务。
- **任务过期处理**: 自动清理 24 小时前的过期任务。
- **报告归档**: 自动归档 30 天前的分析报告。
- 配置位于 [`backend/core/admin/tasks.py`](backend/core/admin/tasks.py)。

**6. 日志配置**
- 使用自定义的彩色日志格式化器 [`backend/core/colored_formatter.py`](backend/core/colored_formatter.py)。
- 统一通过 `logging.getLogger(__name__)` 获取日志记录器。

**7. 前端模块动态加载**
- 路由配置在 [`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts)。
- 采用路由懒加载 (`import(...)`) 优化性能。

**8. 配置管理**
- 后端使用 Pydantic Settings ([`backend/core/config.py`](backend/core/config.py))。
- 支持 `.env` 文件加载。
- 区分开发 (`DEBUG=True`) 和生产环境。

## 关键文件路径

| 用途 | 路径 |
|------|------|
| 应用入口 | [`backend/main.py`](backend/main.py) |
| 全局配置 | [`backend/core/config.py`](backend/core/config.py) |
| RBAC 定义 | [`backend/core/auth/rbac.py`](backend/core/auth/rbac.py) |
| 用户模型 | [`backend/core/user/models.py`](backend/core/user/models.py) |
| 安全服务 | [`backend/core/security/`](backend/core/security/) |
| 数据库连接 | [`backend/core/db/`](backend/core/db/) |
| TradingAgents API | [`backend/modules/trading_agents/api.py`](backend/modules/trading_agents/api.py) |
| 智能体引擎 | [`backend/modules/trading_agents/core/agent_engine.py`](backend/modules/trading_agents/core/agent_engine.py) |
| 任务管理器 | [`backend/modules/trading_agents/core/task_manager.py`](backend/modules/trading_agents/core/task_manager.py) |
| 前端路由加载 | [`frontend/src/core/router/module_loader.ts`](frontend/src/core/router/module_loader.ts) |

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
- **配置项**: `REQUIRE_APPROVAL` (在 `.env` 或 `config.py` 中设置)。
- 若为 `True`，新用户状态为 `PENDING`，需管理员在后台点击"通过"。
- 若为 `False`，新用户状态直接为 `ACTIVE`。

## API 端点概览

### 系统与认证
- `POST /api/system/initialize`: 系统初始化（仅首次可用）
- `POST /api/users/register`: 用户注册
- `POST /api/users/login`: 用户登录
- `GET /api/users/me`: 获取当前用户信息

### 管理员接口 (Admin)
- `GET /api/admin/users`: 用户列表
- `PUT /api/admin/users/{id}/approve`: 审核通过
- `PUT /api/admin/users/{id}/disable`: 禁用用户
- `GET /api/admin/audit-logs`: 查看审计日志

### TradingAgents 模块
- `POST /api/trading-agents/tasks`: 创建分析任务
- `GET /api/trading-agents/tasks/{id}/stream`: SSE 实时报告流
- `GET /api/trading-agents/agent-config`: 获取智能体配置

## 新功能开发指南

### 业务模块开发 (modules/)
1. **后端**:
   - 在 `backend/modules/` 下创建新目录。
   - 编写 `api.py` (路由), `service.py` (逻辑), `models.py` (数据模型)。
   - **必须**使用 `get_current_user` 依赖，并确保所有数据库操作包含 `user_id` 过滤。
   - 在 `main.py` 中注册路由。

2. **前端**:
   - 在 `frontend/src/modules/` 下创建视图组件。
   - 在 `frontend/src/core/router/module_loader.ts` 中添加路由。

### 核心功能扩展 (core/)
- 修改核心逻辑（如认证、RBAC）需极其谨慎。
- 必须运行完整测试套件确保不破坏现有功能。
- 更新本文档。

## FinanceMCP 集成

本项目集成了 FinanceMCP (基于 Tushare API 的 MCP 服务器) 作为核心数据源。

**可用工具：**
- `stock_data`: 股票行情与技术指标 (MACD, RSI, KDJ 等)
- `company_performance`: 财务报表数据
- `fund_data`: 基金数据
- `macro_econ`: 宏观经济指标
- `finance_news`: 财经新闻

## TradingAgents 模块详解

这是本项目的核心业务模块——基于 LangGraph 的多阶段 AI 股票分析系统。

### 四阶段工作流

| 阶段 | 名称 | 描述 | 输出 |
|------|------|------|------|
| 1 | 独立分析 (Individual Analysis) | 3个分析师（基本面、技术面、市场情绪）并行分析 | 3份独立报告 |
| 2 | 研究与辩论 (Research & Debate) | 研究经理与看多/看空辩手进行多轮辩论 | 辩论总结 |
| 3 | 风险评估 (Risk Assessment) | 风险分析师评估市场、流动性和集中度风险 | 风险报告 |
| 4 | 总结报告 (Summary) | 综合所有信息生成最终投资建议 | 最终报告 (买入/卖出/持有) |

### 关键特性

1.  **并发控制**:
    - 公共模型资源池（默认 5 并发）。
    - 用户级并发限制。
    - 支持 FIFO 和优先级队列。

2.  **工具循环检测**:
    - 自动检测并中断连续重复的工具调用（阈值: 3次）。
    - 防止 AI 陷入死循环。

3.  **任务恢复机制**:
    - 系统重启后自动恢复运行中的任务。
    - 验证配置快照完整性。

4.  **Token 消耗追踪**:
    - 记录每个任务的 Token 用量。
    - 前端展示预估成本。

5.  **MCP 兼容性补丁 (重要)**:
    - 位于 `backend/modules/trading_agents/services/mcp_patch.py`。
    - 修复了 MCP Python SDK 的已知问题（如空 SSE 数据解析错误）和 FinanceMCP 的非标错误格式响应。
    - 在 `main.py` 启动时自动应用。

### 多用户配置优先级规则 (Mandatory)

系统支持三层配置优先级，确保灵活性与默认行为的统一：

1.  **用户自定义配置**: 若用户修改了配置（`is_customized=True`），优先级最高。
2.  **系统公共配置**: 若用户未自定义，使用系统公共配置（`user_id="system_public"`）。
3.  **默认 YAML 模板**: 若公共配置不存在，从代码库中的 YAML 文件重新创建。

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

## 环境与安全配置

### 后端 (.env)
```bash
# 应用基础
APP_NAME=StockAnalysis
DEBUG=true
SECRET_KEY=your-secret-key-min-32-chars

# 数据库
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379

# 安全与限流
LOGIN_MAX_ATTEMPTS=5          # 最大登录失败次数
LOGIN_BLOCK_DURATION=1800     # 锁定时间(秒)
CAPTCHA_ENABLED=true          # 启用滑块验证码
REQUIRE_APPROVAL=true         # 启用注册审核

# TradingAgents 配置
TRADING_AGENTS_ENABLED=true
TRADING_AGENTS_MAX_TASK_QUEUE_SIZE=100
TRADING_AGENTS_PUBLIC_MODEL_CONCURRENCY=5
```

### 前端 (.env)
```bash
VITE_API_BASE_URL=/api
```

### 安全注意事项
- **密码存储**: 使用 bcrypt (12 rounds) 哈希。
- **JWT**: HS256 算法，30分钟有效期。
- **数据隔离**: 严格执行 `user_id` 过滤。
- **敏感信息**: 智能体提示词 (`prompts`) 等敏感配置仅管理员可见，普通用户接口自动过滤。

## 已知问题与解决方案

1.  **SSE 换行符转义问题**
    - **现象**: SSE 流输出字面量 `\n\n` 而不是换行。
    - **解决**: Python f-string 中需使用双反斜杠 `\\n\\n`。

2.  **Vue 组件导入**
    - **现象**: `Failed to resolve component`.
    - **解决**: 自定义组件（非 Element Plus）必须在 `<script setup>` 中显式 import。

3.  **MCP 协议兼容性**
    - **现象**: 连接某些 MCP 服务器时报错。
    - **解决**: 确保 `mcp_patch.py` 已在 `main.py` 中正确加载。

## 开发规范备忘

1.  **始终使用 TodoWrite 工具**：在开始复杂任务前，先规划 Todo 列表。
2.  **验证优先**：修改代码后，务必进行语法验证和功能测试，测试后删除删除代码和文件。
3.  **文档更新**：如果修改了架构或核心逻辑，请同步更新本文档。
4.  **不随意新建文件**：优先修改现有文件，保持目录整洁。
