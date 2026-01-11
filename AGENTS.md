
## 开发命令

**前端 (Vue 3 + TypeScript):**
- `npm run dev` - 开发服务器
- `npm run build` - 构建
- `npm run build:check` - 类型检查 + 构建
- `npm run lint` - ESLint 检查并自动修复

**后端 (FastAPI + Python):**
- `poetry run pytest tests/` - 运行所有测试
- `poetry run pytest tests/test_file.py::test_func` - 运行单个测试
- `poetry run pytest -m unit` - 运行单元测试
- `poetry run pytest -m integration` - 运行集成测试
- `poetry run ruff check .` - 代码检查
- `poetry run black .` - 代码格式化
- `poetry run mypy .` - 类型检查

**Docker:**
- `docker-compose -f docker-compose.dev.yml up -d` - 启动开发环境
- `docker-compose -f docker-compose.dev.yml logs backend` - 查看后端日志

## 代码规范

**Python:**
- Black 格式化：100 字符行宽
- Ruff 检查：E, F, I, N, W 规则
- MyPy：严格类型检查，禁止未类型化定义
- 命名：snake_case 函数/变量，PascalCase 类
- 异常：全局异常处理器 + 上下文日志

**TypeScript/Vue:**
- ESLint：Vue3-recommended + TypeScript-recommended
- 命名：camelCase 变量/函数，PascalCase 组件
- 禁止：`no-explicit-any` (警告)，`no-unused-vars` (允许 `_` 前缀)
- Vue：单文件组件 `<script setup lang="ts">`

**用户数据隔离:**
- MongoDB：所有文档包含 `user_id` 字段
- Redis：Key 格式 `user:{user_id}:...`
- API 层：通过 `get_current_user` 依赖注入强制校验

**日志级别:**
- ERROR：需要人工介入的异常
- WARN：潜在问题但可继续
- INFO：关键业务节点（登录、任务状态变更）
- DEBUG：调试信息（禁止高频调用）
