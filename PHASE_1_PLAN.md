# 第一阶段实施计划：模块化单体架构搭建 (Phase 1: Modular Monolith Infrastructure)

## 1. 阶段目标
本阶段旨在建立 **TradingAgents-CN** 的 **模块化单体 (Modular Monolith)** 架构。
核心目标是构建一个纯净的**主体 (Core Host)**，它**绝对不包含任何业务逻辑**，只负责提供基础设施（数据库、鉴权、事件总线）和**插件化机制**。
所有的业务功能（行情、分析、交易）都将作为**完全独立的子模块 (Modules)** 接入主体。

## 2. 架构设计理念：严格边界 + 事件驱动 (Strict Boundaries + Event-Driven)

基于对现有设计文档的深度分析和最佳实践调研，我们采用 **垂直切片架构 (Vertical Slice Architecture)** + **事件驱动解耦** 的混合模式。

### 2.1 核心设计原则
1.  **主体零业务**: `core/` 目录下不允许出现任何与股票、交易、分析相关的业务代码。
2.  **模块自包含**: 每个模块必须包含其所需的全部代码（API、Service、Model），不依赖其他模块的内部实现。
3.  **事件通信**: 模块间通信必须通过 Core 提供的事件总线，禁止直接调用其他模块的 Service。

### 2.2 目录结构预览 (Directory Structure)
系统将严格分为 **后端 (Backend)** 和 **前端 (Frontend)** 两个独立工程，但在内部结构上保持**完全对齐**。

```text
StockAnalysis/
├── backend/                  # 后端工程 (FastAPI)
│   ├── core/                 # [主体] 核心基础设施 (绝对不含业务)
│   │   ├── db/               # 数据库连接抽象层
│   │   │   ├── mongodb.py    # MongoDB 连接
│   │   │   └── redis.py      # Redis 连接
│   │   ├── auth/             # 基础鉴权逻辑 (JWT)
│   │   │   ├── dependencies.py # FastAPI 依赖注入
│   │   │   └── models.py     # User 模型 (仅用户相关)
│   │   ├── events/            # 事件总线 (模块间通信)
│   │   │   ├── bus.py        # 事件发布/订阅
│   │   │   └── schemas.py    # 事件定义
│   │   ├── bootstrap.py        # 模块自动加载器 (关键)
│   │   └── exceptions.py      # 全局异常处理
│   │
│   └── modules/              # [模块] 所有业务功能 (完全独立)
│       ├── user_management/    # -> 用户管理模块 (Phase 1)
│       │   ├── api.py        # FastAPI 路由
│       │   ├── service.py    # 业务逻辑
│       │   ├── models.py     # 数据库模型
│       │   └── __init__.py   # 模块导出定义
│       │
│       └── dashboard/        # -> 仪表盘模块 (Phase 1 验证)
│           ├── api.py
│           ├── service.py
│           ├── models.py
│           └── __init__.py
│
└── frontend/                 # 前端工程 (Vue 3)
    ├── src/
    │   ├── core/             # [主体] 公共组件与布局
    │   │   ├── layout/       # 侧边栏、顶部导航
    │   │   ├── router/       # 路由守卫
    │   │   ├── api/          # HTTP 客户端封装
    │   │   └── events/       # 前端事件总线
    │   │
    │   └── modules/          # [模块] 业务界面 (与后端一一对应)
    │       ├── user_management/ # -> 用户管理前端
    │       │   ├── views/    # 页面
    │       │   ├── components/
    │       │   ├── store.ts  # Pinia 状态管理
    │       │   └── routes.ts # 路由定义
    │       │
    │       └── dashboard/    # -> 仪表盘前端
    │           ├── views/
    │           ├── components/
    │           ├── store.ts
    │           └── routes.ts
```

### 2.3 模块化加载机制 (基于最佳实践)
*   **后端**: `core/bootstrap.py` 实现基于 Python `importlib` 的动态加载：
    1.  扫描 `modules/` 目录下的所有子文件夹。
    2.  检查每个模块是否包含 `__init__.py` 和 `api.py`。
    3.  动态导入并注册 APIRouter 到主应用。
    4.  将模块的 Models 注册到 MongoDB 连接中。
*   **前端**: `core/router/module_loader.ts` 实现基于 Vite 动态导入：
    1.  使用 `import.meta.glob('./modules/*/routes.ts')` 扫描所有模块路由。
    2.  动态注册到 Vue Router。
    3.  自动生成侧边栏菜单。

## 3. 技术栈确认 (Tech Stack)
*   **后端**: Python 3.10+ / FastAPI (利用 Dependency Injection 实现模块解耦)
*   **前端**: Vue 3 / Vite / TypeScript / Pinia (模块化 Store) / Naive UI (或 Ant Design Vue)
*   **数据**: MongoDB (业务数据) + Redis (缓存/队列)
*   **测试**: Pytest (后端) + Vitest (前端)

## 4. 详细执行步骤 (Task Breakdown)

### 步骤 1: 工程结构初始化 (Project Infrastructure)
*   [ ] **根目录初始化**: 建立 Git 仓库，配置 `.gitignore`。
*   [ ] **后端环境搭建**: 创建 `backend/`，配置 `pyproject.toml` (使用 Poetry 管理依赖)。
*   [ ] **前端环境搭建**: 创建 `frontend/`，使用 Vite 初始化 Vue3 + TS + Pinia 项目。
*   [ ] **基础设施容器化**: 编写 `docker-compose.yml` (MongoDB, Redis)。

### 步骤 2: 后端核心主体开发 (Backend Core Host)
*   [ ] **核心骨架**: 搭建 FastAPI 应用入口 (`main.py`)，配置全局异常处理和 CORS。
*   [ ] **数据库抽象层**: 
    *   实现 `core/db/mongodb.py` (Motor 异步连接)。
    *   实现 `core/db/redis.py` (连接池管理)。
*   [ ] **事件总线**: 实现 `core/events/bus.py`，支持发布/订阅模式。
*   [ ] **认证基础**: 
    *   实现 `core/auth/dependencies.py` (JWT 验证)。
    *   实现 `core/auth/models.py` (User 模型)。
*   [ ] **模块加载器 (Module Loader)**: 开发 `core/bootstrap.py`，实现基于 `importlib` 的动态加载。

### 步骤 3: 前端核心主体开发 (Frontend Core Host)
*   [ ] **主体布局 (App Shell)**: 开发 `core/layout/MainLayout.vue`，包含动态侧边栏和顶部栏。
*   [ ] **HTTP 客户端**: 封装 `core/api/http.ts`，统一处理 Token、错误和 Loading 状态。
*   [ ] **前端事件总线**: 实现 `core/events/bus.ts`，与后端事件系统对应。
*   [ ] **模块路由加载器**: 编写 `core/router/module_loader.ts`，实现动态路由注册。

### 步骤 4: 验证模块 - 用户管理 (User Management Module)
*   [ ] **后端实现**: 
    *   在 `modules/user_management/` 下创建完整闭环代码。
    *   实现 `POST /api/auth/register`, `POST /api/auth/login` 接口。
    *   实现 `GET /api/users/me` 接口。
*   [ ] **前端实现**:
    *   在 `src/modules/user_management/` 下创建登录/注册页面。
    *   实现 Pinia store 管理用户状态。
*   [ ] **验证**: 测试完整的注册-登录-获取用户信息流程。

### 步骤 5: 验证模块 - 仪表盘 (Dashboard Module)
*   [ ] **后端实现**: 
    *   在 `modules/dashboard/` 下创建 Mock 数据接口。
    *   实现 `GET /api/dashboard/summary` (返回系统概览)。
*   [ ] **前端实现**:
    *   在 `src/modules/dashboard/` 下创建概览页面。
    *   验证侧边栏自动生成"仪表盘"菜单项。
*   [ ] **验证**: 登录后能正常跳转到仪表盘并显示 Mock 数据。

### 步骤 6: 自动化测试与CI基础 (Testing)
*   [ ] **测试框架**: 配置 Pytest (后端) 和 Vitest (前端)。
*   [ ] **模块测试规范**: 
    *   为 `user_management` 模块编写单元测试。
    *   为 `dashboard` 模块编写集成测试。
*   [ ] **API 文档**: 验证 FastAPI 自动生成的 Swagger 文档可访问。

## 5. 验收标准 (Acceptance Criteria)
1.  **即插即用**: 新增一个空模块文件夹后，重启服务，系统不报错且能识别该模块（至少在日志中）。
2.  **隔离性**: 删除 `modules/dashboard` 文件夹后，系统核心（登录、设置）仍能正常运行。
3.  **代码规范**: 所有模块内部引用使用相对路径，跨模块引用必须通过 Core 提供的接口。
4.  **用户流程完整性**: 
    *   用户能成功注册账号。
    *   用户能登录并获取 JWT Token。
    *   登录后能访问仪表盘页面。
    *   侧边栏自动显示"用户管理"、"仪表盘"菜单项。
5.  **测试覆盖**: 
    *   后端核心功能（认证、模块加载）测试覆盖率 > 80%。
    *   前端核心组件（布局、路由）测试覆盖率 > 70%。
6.  **API 文档**: FastAPI 自动生成的 Swagger 文档 (`/docs`) 能正常访问，包含所有注册的接口。

## 6. 风险与缓解措施 (Risk & Mitigation)
| 风险 | 影响 | 缓解措施 |
| :--- | :--- | :--- |
| **模块加载失败** | 系统启动异常 | 在 `bootstrap.py` 中添加 try-catch，失败时记录详细日志并跳过该模块 |
| **JWT 安全性** | 认证绕过 | 使用 `python-jose` 库，配置合理的过期时间和强密钥 |
| **MongoDB 连接池** | 性能瓶颈 | 实现连接池监控，设置最大连接数限制 |
| **前端路由冲突** | 页面无法访问 | 在模块加载器中验证路由路径唯一性 |
