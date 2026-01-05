# 股票分析平台

一个基于 **LangGraph** 多智能体工作流的股票分析平台，支持多用户登录注册，每个用户的配置和数据完全隔离。

## 技术栈

| 层级 | 技术选择 |
|------|----------|
| 前端框架 | Vue 3 + TypeScript + Vite |
| UI组件库 | Element Plus |
| 状态管理 | Pinia |
| 路由 | Vue Router |
| 后端框架 | FastAPI + Python |
| 工作流引擎 | **LangGraph** (StateGraph) |
| LLM 接入 | 智谱 AI (glm-4.6) |
| 工具协议 | MCP (Model Context Protocol) |
| 数据库 | MongoDB + Redis |
| 认证 | JWT Token |
| 容器化 | Docker + Docker Compose |

## 项目结构

```
StockAnalysis/
├── docs/                           # 项目文档
│   └── SYSTEM_DESIGN.md           # 系统设计文档
├── frontend/                       # Vue 3 前端
│   ├── src/
│   │   ├── core/                  # 核心功能
│   │   │   ├── api/               # HTTP 客户端
│   │   │   ├── router/            # 路由系统
│   │   │   ├── events/            # 事件总线
│   │   │   └── layout/            # 主布局
│   │   └── modules/               # 功能模块
│   │       ├── user_management/   # 用户管理模块
│   │       └── dashboard/         # 仪表板模块
│   └── package.json
├── backend/                        # FastAPI 后端
│   ├── core/                      # 核心功能
│   │   ├── config.py              # 配置管理
│   │   ├── db/                    # 数据库连接
│   │   ├── auth/                  # 认证系统
│   │   └── exceptions.py          # 全局异常
│   ├── modules/                   # 功能模块
│   │   └── user_management/       # 用户管理模块
│   └── main.py                    # 应用入口
├── docker/                         # Docker 配置
│   ├── mongodb/init/
│   └── redis/
├── scripts/                        # 工具脚本
│   ├── dev.bat                    # Windows 开发启动
│   └── dev.sh                     # Linux/Mac 开发启动
├── docker-compose.yml              # 生产环境编排
├── docker-compose.dev.yml          # 开发环境编排
└── README.md
```

## 快速开始

### 环境要求

- Docker & Docker Compose（推荐，用于完整容器化部署）
- Node.js 18+（本地开发需要）
- Python 3.11+（本地开发需要）
- Poetry（本地开发需要）

### Docker 容器化部署（推荐）

#### 开发环境

```bash
# 启动开发环境（包含热重载）
docker-compose -f docker-compose.dev.yml up -d
```

**开发环境访问地址：**
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

#### 生产环境

```bash
# 启动生产环境
docker-compose up -d
```

**生产环境访问地址：**
- 应用: http://localhost（Nginx 自动代理后端 API）

### 本地开发部署

如果不使用完整 Docker 容器化，可以仅启动数据库服务：

1. **启动数据库**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d mongodb redis
   ```

2. **启动后端**
   ```bash
   cd backend
   cp .env.example .env
   poetry install
   poetry run uvicorn main:app --reload
   ```

3. **启动前端**
   ```bash
   cd frontend
   cp .env.example .env
   npm install
   npm run dev
   ```

### 快速命令参考

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up -d          # 启动
docker-compose -f docker-compose.dev.yml down           # 停止
docker-compose -f docker-compose.dev.yml logs -f        # 查看日志
docker-compose -f docker-compose.dev.yml restart        # 重启

# 生产环境
docker-compose up -d              # 启动
docker-compose down               # 停止
docker-compose logs -f             # 查看日志

# 实用命令
docker-compose -f docker-compose.dev.yml ps             # 查看容器
docker-compose -f docker-compose.dev.yml logs backend   # 后端日志
docker-compose -f docker-compose.dev.yml logs frontend  # 前端日志
```

## 功能特性

### 已实现

**核心功能：**
- **TradingAgents 智能分析系统**（基于 LangGraph）
  - 四阶段工作流：分析师团队 → 观点辩论 → 风险评估 → 总结报告
  - 多智能体协作：技术分析、基本面分析、情绪分析、新闻分析
  - MCP 工具集成：实时数据获取和外部工具调用
  - 并发控制：双模型并发槽位管理
  - 实时进度：WebSocket 推送任务进度
  - Token 追踪：成本预估和实际消耗统计

**用户系统：**
- 用户注册/登录（带图形验证码）
- JWT 认证
- 基于角色的访问控制（RBAC）：GUEST、USER、ADMIN、SUPER_ADMIN
- 用户数据完全隔离 (MongoDB + Redis)
- 登录安全保护：
  - 滑动拼图验证码
  - IP 限流（防暴力破解）
  - IP 信任机制（常用 IP 无感登录）
  - 渐进式防护策略

**技术特性：**
- 响应式布局（PC + 移动端）
- 模块化单体架构
- 异步任务处理
- WebSocket 实时通信
- Docker 容器化部署

### 预留扩展

- 市场中心
- AI 分析
- 智能选股
- 交易终端
- WebSocket 实时推送

## 用户隔离设计

### MongoDB 数据隔离

- 每个用户数据包含 `user_id` 字段
- 数据库层创建 `user_id` 索引
- 后端服务层强制校验

### Redis 缓存隔离

Key 命名规范: `user:{user_id}:...`

示例:
- `user:{user_id}:session:{session_id}` - 会话
- `user:{user_id}:preferences` - 用户配置
- `user:{user_id}:watchlist` - 自选股

## API 端点

### 认证

- `POST /api/v1/users/captcha/generate` - 生成图形验证码
- `GET /api/v1/users/captcha/required?email=` - 检查是否需要验证码
- `POST /api/v1/users/register` - 用户注册
- `POST /api/v1/users/login` - 用户登录
- `POST /api/v1/users/logout` - 用户登出
- `POST /api/v1/users/refresh-token` - 刷新令牌

### 用户

- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新用户信息
- `GET /api/v1/users/me/preferences` - 获取用户配置
- `PUT /api/v1/users/me/preferences` - 更新用户配置

### 管理员（需要 ADMIN 权限）

- `GET /api/v1/admin/users` - 获取用户列表
- `POST /api/v1/admin/users` - 创建用户
- `PUT /api/v1/admin/users/{id}` - 更新用户
- `DELETE /api/v1/admin/users/{id}` - 删除用户
- `PUT /api/v1/admin/users/{id}/role` - 修改用户角色（SUPER_ADMIN）

## 添加新功能模块

### 后端模块

创建 `backend/modules/your_module/api.py`:

```python
from fastapi import APIRouter, Depends
from core.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/your-module", tags=["your-module"])

@router.get("/")
async def get_data(user=Depends(get_current_user)):
    # user_id 在 user 对象中，数据自动隔离
    pass
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

## 部署

### Docker 部署（推荐）

项目支持完全容器化部署，提供开发和生产两种环境配置。

#### 开发环境部署

开发环境会暴露所有服务端口，便于开发和调试：

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 或使用 Makefile
make dev
```

**开发环境访问地址：**
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- MongoDB: localhost:27017
- Redis: localhost:6379

**开发环境特性：**
- ✅ 前端支持热重载（Vite dev server）
- ✅ 后端支持热重载（uvicorn --reload）
- ✅ 代码卷挂载，实时同步修改
- ✅ 暴露所有服务端口

#### 生产环境部署

生产环境只暴露前端 80 端口，其他服务在内部网络通信：

```bash
# 启动生产环境
docker-compose up -d

# 或使用 Makefile
make prod
```

**生产环境访问地址：**
- 应用入口: http://localhost
- Nginx 自动代理 `/api` 到后端服务

**生产环境特性：**
- ✅ 多阶段构建，镜像体积小
- ✅ 只暴露前端 80 端口
- ✅ Nginx 作为反向代理
- ✅ 非 root 用户运行（安全）
- ✅ Gzip 压缩优化
- ✅ 静态资源长期缓存

#### 实用命令

```bash
# 重新构建镜像
docker-compose -f docker-compose.dev.yml build --no-cache

# 清理所有容器、网络、卷
docker-compose -f docker-compose.dev.yml down -v

# 查看运行中的容器
docker-compose -f docker-compose.dev.yml ps

# 查看服务日志
docker-compose -f docker-compose.dev.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.dev.yml logs backend
docker-compose -f docker-compose.dev.yml logs frontend

# 进入后端容器（开发环境）
docker exec -it stock-analysis-backend-dev /bin/bash

# 连接到 MongoDB
docker exec -it stock-analysis-mongodb-dev mongosh

# 连接到 Redis
docker exec -it stock-analysis-redis-dev redis-cli
```

### 本地开发部署

如果不使用 Docker，可以在本地安装依赖直接运行：

**1. 启动数据库**
```bash
docker-compose -f docker-compose.dev.yml up -d mongodb redis
```

**2. 启动后端**
```bash
cd backend
cp .env.example .env
poetry install
poetry run uvicorn main:app --reload
```

**3. 启动前端**
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### 环境变量配置

**后端环境变量** (`backend/.env`):
```bash
ENVIRONMENT=development
SECRET_KEY=your-secret-key-change-in-production
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=stock_analysis
REDIS_URL=redis://localhost:6379/0
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:8000
```

**前端环境变量** (`frontend/.env`):
```bash
VITE_API_BASE_URL=/api
```

**生产环境** 可以创建 `.env` 文件或在 `docker-compose.yml` 中配置环境变量：
```bash
SECRET_KEY=<生产环境密钥>
CORS_ORIGINS=https://your-domain.com
```

## 文档

- [系统设计文档](docs/SYSTEM_DESIGN.md)
- [API 文档](http://localhost:8000/docs) (运行后端后访问)

## 许可证

MIT License
