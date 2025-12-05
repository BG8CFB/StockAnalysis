# TradingAgents-CN

模块化单体架构的股票分析智能体系统

## 项目架构

采用 **模块化单体 (Modular Monolith)** 架构，具有严格的边界和事件驱动解耦特性。

- **主体 (Core Host)**: 提供基础设施（数据库、认证、事件总线）和插件化机制
- **模块 (Modules)**: 完全独立的业务功能模块，通过事件总线通信

## 技术栈

### 后端
- Python 3.10+
- FastAPI (异步Web框架)
- MongoDB (业务数据)
- Redis (缓存/队列)
- Motor (异步MongoDB驱动)

### 前端
- Vue 3
- TypeScript
- Vite (构建工具)
- Pinia (状态管理)
- Naive UI (UI组件库)

## 快速开始

### 使用Docker (推荐)

1. 启动基础设施服务（MongoDB + Redis）：
```bash
docker-compose up -d mongodb redis
```

2. 启动完整开发环境（包括前后端）：
```bash
docker-compose -f docker-compose.dev.yml up
```

### 手动启动

#### 后端

1. 安装依赖：
```bash
cd backend
pip install poetry
poetry install
```

2. 配置环境变量：
```bash
cp .env.example .env
# 编辑.env文件，配置数据库连接等
```

3. 启动服务：
```bash
poetry run uvicorn main:app --reload
```

#### 前端

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 配置环境变量：
```bash
cp .env.example .env
# 编辑.env文件，配置API地址等
```

3. 启动开发服务器：
```bash
npm run dev
```

## 服务地址

- 后端API: http://localhost:8000
- 前端界面: http://localhost:5173
- API文档: http://localhost:8000/docs
- MongoDB管理: http://localhost:8081
- Redis管理: http://localhost:8082

## 项目结构

```
StockAnalysis/
├── backend/                  # 后端工程
│   ├── core/                 # 核心基础设施
│   │   ├── db/               # 数据库连接抽象层
│   │   ├── auth/             # 基础鉴权逻辑
│   │   ├── events/           # 事件总线
│   │   └── bootstrap.py      # 模块自动加载器
│   └── modules/              # 业务功能模块
│       ├── user_management/  # 用户管理模块
│       └── dashboard/        # 仪表盘模块
├── frontend/                 # 前端工程
│   └── src/
│       ├── core/             # 公共组件与布局
│       └── modules/          # 业务界面模块
└── docker-compose.yml        # Docker配置
```

## 模块开发

### 后端模块

1. 在 `backend/modules/` 下创建新目录
2. 创建 `__init__.py`、`api.py`、`service.py`、`models.py`
3. 定义模块信息：
```python
# __init__.py
from core.bootstrap import ModuleInfo

MODULE_INFO = ModuleInfo(
    name="your_module",
    version="1.0.0",
    description="模块描述",
    router_prefix="/api/your_module"
)
```

### 前端模块

1. 在 `frontend/src/modules/` 下创建新目录
2. 创建 `routes.ts`、`views/`、`components/`、`store.ts`
3. 定义模块路由：
```typescript
// routes.ts
import type { ModuleInfo } from '@/core/router/module_loader'

export default {
  name: 'your_module',
  version: '1.0.0',
  description: '模块描述',
  routes: [
    {
      path: '/your-module',
      name: 'YourModule',
      component: () => import('./views/YourModuleView.vue'),
      meta: {
        title: '您的模块',
        icon: 'DashboardOutlined'
      }
    }
  ]
} as ModuleInfo
```

## 开发指南

### 代码规范

- 后端使用 Black + isort 进行格式化
- 前端使用 ESLint + Prettier 进行格式化
- 提交前请运行格式化工具

### 测试

```bash
# 后端测试
cd backend
poetry run pytest

# 前端测试
cd frontend
npm run test
```

### 数据库迁移

MongoDB的初始化脚本位于 `docker/mongodb/init/init.js`，会自动创建必要的集合和索引。

## 系统特性

- ✅ 模块化架构，支持即插即用
- ✅ 事件驱动通信，模块间解耦
- ✅ JWT认证系统
- ✅ 统一的错误处理
- ✅ 自动生成的API文档
- ✅ 响应式前端界面
- ✅ Docker容器化部署

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 许可证

MIT License