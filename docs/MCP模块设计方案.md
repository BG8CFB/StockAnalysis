# MCP 模块设计方案

## 一、模块目录结构

```
backend/modules/mcp/              # MCP 独立模块（新建）
│
├── __init__.py                   # 模块初始化
│
├── pool/                         # 连接池子模块
│   ├── __init__.py
│   ├── pool.py                   # MCPConnectionPool 主池管理器
│   ├── connection.py             # MCPConnection 长连接对象
│   ├── registry.py               # 连接注册表
│   └── queue.py                  # 请求队列管理
│
├── core/                         # 核心功能
│   ├── __init__.py
│   ├── adapter.py                # MCP 适配器（基于 langchain-mcp-adapters）
│   ├── session.py                # 会话管理
│   └── exceptions.py             # 自定义异常
│
├── service/                      # 服务层
│   ├── __init__.py
│   ├── mcp_service.py            # MCP 服务器 CRUD 服务
│   └── health_checker.py         # 健康检查服务
│
├── api/                          # API 路由（前端调用）
│   ├── __init__.py
│   └── routes.py                 # MCP 相关 API 端点
│
└── config/                       # 配置
    ├── __init__.py
    ├── loader.py                 # 配置加载器
    └── templates/
        └── agents.yaml           # 智能体配置模板


backend/modules/trading_agents/tools/  # TradingAgents 模块
│
├── mcp_tool_filter.py            # MCP 工具过滤（智能体配置相关）← 新增
├── registry.py                   # 工具注册表（现有）
└── ...
```

---

## 二、连接池设计

### 2.1 MCPConnection（长连接对象）

```python
class MCPConnection:
    """任务级长连接对象"""

    # 属性
    connection_id: str           # 连接唯一 ID
    server_id: str               # MCP 服务器 ID
    task_id: str                 # 任务 ID
    user_id: str                 # 用户 ID
    state: ConnectionState       # 连接状态
    client: MultiServerMCPClient # langchain-mcp-adapters 客户端
    session: MCPSession          # MCP 会话
    tools: List[BaseTool]        # LangChain 工具列表
    created_at: datetime
    last_used_at: datetime
    cleanup_timer: Optional[Task]

    # 状态
    enum ConnectionState:
        CONNECTING    # 连接中
        ACTIVE        # 活跃（长连接保持）
        CLOSING       # 关闭中（任务完成后 10 秒）
        FAILED_CLEANUP # 失败清理中（30 秒）
        CLOSED        # 已关闭

    # 关键方法
    async def initialize() -> List[BaseTool]:
        """初始化连接，返回工具列表"""

    async def mark_complete() -> None:
        """标记任务完成，启动 10 秒倒计时"""

    async def mark_failed() -> None:
        """标记任务失败，启动 30 秒倒计时"""

    async def close() -> None:
        """优雅关闭"""

    async def destroy() -> None:
        """强制销毁"""
```

### 2.2 MCPConnectionPool（统一连接池）

```python
class MCPConnectionPool:
    """统一 MCP 连接池"""

    # 服务器配置注册表
    _servers: Dict[server_id, ServerConfig]

    # 活跃连接
    _connections: Dict[conn_id, MCPConnection]

    # 并发控制（每个 server_id 独立）
    _semaphores: Dict[server_id, Semaphore]

    # 请求队列（每个 server_id 独立）
    _queues: Dict[server_id, Queue]

    # 任务-连接映射
    _task_connections: Dict[task_id, conn_id]

    # 并发参数配置
    PERSONAL_MAX_CONCURRENCY = 100   # 个人 MCP：每个用户 100 并发
    PUBLIC_PER_USER_MAX = 10        # 公共 MCP：每个用户 10 并发

    # 关键方法
    async def register_server(config) -> None:
        """注册服务器到池子"""

    async def unregister_server(server_id) -> None:
        """从池子注销服务器"""

    async def acquire_connection(
        server_id, task_id, user_id
    ) -> MCPConnection:
        """获取或创建长连接"""

    async def release_connection(conn_id) -> None:
        """释放连接（标记完成）"""

    async def disable_server(server_id) -> None:
        """禁用服务器（不影响进行中的任务）"""

    async def get_connection_stats(server_id) -> Dict:
        """获取连接统计"""
```

---

## 三、连接生命周期

### 3.1 状态机

```
┌──────────┐  acquire_connection()   ┌────────────┐
│  IDLE    │ ───────────────────────→│ CONNECTING │
└──────────┘                         └────────────┘
     ↑                                      │
     │                                      │ 连接成功
     │  销毁完成                             ↓
     │  (10s/30s后)                   ┌──────────────┐
     │                             │    ACTIVE     │ ← 长连接状态
     │                             └──────────────┘
     │                                      │
     │                                      │ 任务完成
     │                                      ↓
     │                             ┌──────────────┐
     │                             │   CLOSING    │
     │                             │  (10秒倒计时)  │
     │                             └──────────────┘
     │                                      │
     │                                      │ 任务失败
     │                                      ↓
     │                             ┌──────────────┐
     │                             │FAILED_CLEANUP│
     │                             │  (30秒倒计时)  │
     │                             └──────────────┘
     │                                      │
     └──────────────────────────────────────┘
                超时后销毁
```

### 3.2 时间线

**正常完成**：
```
T0: 创建任务 → acquire_connection()
T1: 连接建立 → 返回工具给 LLM → 任务执行...
Tx: 任务完成 → mark_complete() → 启动 10 秒倒计时
T10: 倒计时结束 → destroy()
```

**失败清理**：
```
T0: 创建任务 → acquire_connection()
T1: 连接建立 → 返回工具给 LLM → 任务执行...
Tx: 任务失败 → mark_failed() → 启动 30 秒倒计时
T30: 倒计时结束 → destroy()
```

**MCP 关闭**：
```
T0: 任务正在使用 MCP_X
T1: 管理员禁用 MCP_X → disable_server()
    → 标记服务器为 disabled
    → 已有连接继续运行
    → 新任务无法获取此连接
Tx: 任务完成 → 自然销毁
```

---

## 四、并发控制

### 4.1 并发限制

| 类型 | 限制 | 说明 |
|------|------|------|
| 个人 MCP | 每用户 100 并发 | `Semaphore(user_id, 100)` |
| 公共 MCP | 每用户 10 并发 | `Semaphore(user_id, 10)` |

### 4.2 队列模型

```
用户请求（120 个任务）
      ↓
┌─────────────────┐
│  Semaphore(100) │ ← 只允许 100 个并发
└─────────────────┘
      ↓
┌───── 100 个执行中 ─────┐
└────────────────────────┘
      ↓
┌────── 20 个在队列 ──────┐ ← asyncio.Queue(maxsize=20)
└────────────────────────┘
      ↓
执行完成 → 从队列取下一个
```

---

## 五、MCP 关闭的处理

### 5.1 处理流程

```
管理员点击"禁用"MCP_X
      ↓
┌─────────────────────────────────────────┐
│  service.update_server(enabled=False)    │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│  pool.disable_server(server_id)          │
│  ├── 标记服务器配置为 disabled            │
│  ├── 遍历活跃连接列表                     │
│  └── 对每个连接：                         │
│      ├── 标记为 CLOSING（如果任务完成）    │
│      └── 保持 ACTIVE（如果任务运行中）     │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│  后续行为：                               │
│  • 正在运行的任务继续使用 MCP_X           │
│  • 新任务无法获取 MCP_X 的连接            │
│  • 任务完成后自然销毁                     │
└─────────────────────────────────────────┘
```

### 5.2 连接状态感知

```python
# MCPConnection 内部检测
async def _check_server_status(self):
    """定期检查服务器状态"""
    while self.state == ConnectionState.ACTIVE:
        server = await get_server_config(self.server_id)

        if not server.enabled:
            # 服务器被禁用，但不立即断开
            # 只是标记，让任务自然完成
            logger.info(
                f"服务器 {self.server_id} 已被禁用，"
                f"连接 {self.connection_id} 将在任务完成后关闭"
            )
            break

        await asyncio.sleep(5)  # 每 5 秒检查一次
```

---

## 六、智能体 MCP 工具过滤

### 6.1 过滤位置

```
MCP 模块:
    建立长连接 → 返回所有工具
        ↓
TradingAgents 模块:
    mcp_tool_filter.py:
        ├── 读取智能体配置
        ├── 获取 enabled_mcp_servers
        └── 过滤工具
        ↓
    传给 LLM
```

### 6.2 过滤逻辑

```python
# backend/modules/trading_agents/tools/mcp_tool_filter.py

async def filter_tools_for_agent(
    all_tools: List[BaseTool],
    agent_config: AgentConfig,
    user_id: str
) -> List[BaseTool]:
    """
    根据智能体配置过滤 MCP 工具

    Args:
        all_tools: MCP 连接返回的所有工具
        agent_config: 智能体配置（包含 enabled_mcp_servers）
        user_id: 用户 ID

    Returns:
        过滤后的工具列表
    """
    # 获取用户可用的 MCP 服务器
    available_servers = await get_available_servers(user_id)
    available_server_ids = {s.id for s in available_servers}

    # 智能体启用的 MCP 服务器
    enabled_server_ids = set(agent_config.enabled_mcp_servers)

    # 取交集
    valid_server_ids = available_server_ids & enabled_server_ids

    # 过滤工具
    filtered_tools = []
    for tool in all_tools:
        # 假设工具有 mcp_server_id 属性
        if hasattr(tool, 'mcp_server_id'):
            if tool.mcp_server_id in valid_server_ids:
                filtered_tools.append(tool)

    return filtered_tools
```

---

## 七、健康检查

### 7.1 手动触发

```
用户点击"测试连接"按钮
    ↓
前端调用: POST /api/mcp/servers/{id}/test
    ↓
后端: mcp_service.test_server_connection()
    ├── 创建临时连接
    ├── 尝试获取工具列表
    ├── 记录延迟
    ├── 更新数据库状态
    └── 返回测试结果
    ↓
前端显示: 绿色 ✓ / 红色 ✗
```

### 7.2 自动定时检查

```python
# backend/modules/mcp/service/health_checker.py

class MCPHealthChecker:
    """MCP 健康检查器"""

    CHECK_INTERVAL = 300  # 5 分钟

    async def start(self):
        """启动定时检查"""
        while True:
            try:
                await self._check_all_servers()
                await asyncio.sleep(self.CHECK_INTERVAL)
            except asyncio.CancelledError:
                break

    async def _check_all_servers(self):
        """检查所有启用的服务器"""
        servers = await get_all_enabled_servers()

        for server in servers:
            try:
                result = await test_server(server)

                # 更新状态
                await update_server_status(
                    server.id,
                    MCPServerStatusEnum.AVAILABLE
                    if result.success
                    else MCPServerStatusEnum.UNAVAILABLE
                )

            except Exception as e:
                logger.error(f"健康检查失败: {server.id}, error={e}")
```

### 7.3 健康检查与连接池的交互

```
健康检查发现 MCP_X 不可用
    ↓
更新数据库状态为 UNAVAILABLE
    ↓
┌─────────────────────────────────────────┐
│  连接池行为：                             │
│  • 不主动断开现有连接                    │
│  • 新任务尝试获取连接时：                 │
│      ├── 先检查数据库状态                 │
│      ├── 如果 UNAVAILABLE，返回错误       │
│      └── 或者尝试重新连接                 │
└─────────────────────────────────────────┘
```

---

## 八、API 端点

```python
# backend/modules/mcp/api/routes.py

# MCP 服务器 CRUD
GET    /api/mcp/servers                    # 获取服务器列表（公共/个人）
POST   /api/mcp/servers                    # 创建服务器
GET    /api/mcp/servers/{id}               # 获取单个服务器
PUT    /api/mcp/servers/{id}               # 更新服务器
DELETE /api/mcp/servers/{id}               # 删除服务器

# 服务器操作
POST   /api/mcp/servers/{id}/test          # 测试连接（手动健康检查）
GET    /api/mcp/servers/{id}/tools         # 获取工具列表

# 连接池管理（内部使用，不暴露给前端）
GET    /api/mcp/pool/stats                 # 获取连接池统计（管理员）
```

---

## 九、配置文件

```yaml
# backend/modules/mcp/config/default_config.yaml

# 连接池配置
pool:
  # 个人 MCP 并发限制
  personal:
    max_concurrency: 100       # 每用户最大并发
    queue_size: 200            # 队列大小
    queue_timeout: 600         # 队列等待超时（秒）

  # 公共 MCP 并发限制
  public:
    per_user_max: 10           # 每用户最大并发
    queue_size: 50             # 队列大小
    queue_timeout: 300         # 队列等待超时（秒）

# 连接生命周期
connection:
  complete_timeout: 10         # 完成后等待时间（秒）
  failed_timeout: 30           # 失败后等待时间（秒）
  idle_timeout: 600            # 空闲超时（秒）

  # 连接参数
  connect_timeout: 30          # 连接超时（秒）
  read_timeout: 120            # 读取超时（秒）
  keepalive_interval: 30       # 保活间隔（秒）

# 健康检查
health_check:
  enabled: true                # 是否启用自动健康检查
  interval: 300                # 检查间隔（秒）
  timeout: 30                  # 检查超时（秒）
  retry_attempts: 3            # 重试次数

# 清理任务
cleanup:
  interval: 60                 # 清理间隔（秒）
  batch_size: 10               # 每次清理数量
```

---

## 十、关键流程示例

### 10.1 任务使用 MCP 的完整流程

```
用户点击"分析 AAPL"
    ↓
┌─────────────────────────────────────────┐
│  1. 创建任务                              │
│     task_id = "task_001"                 │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  2. AgentEngine 启动任务                 │
│     phase1_agents = [...]                │
│     每个智能体有 enabled_mcp_servers      │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  3. 获取 MCP 连接                         │
│     pool.acquire_connection(             │
│         server_id="mcp_x",               │
│         task_id="task_001",              │
│         user_id="user_123"               │
│     )                                    │
│       ├── 检查用户并发（10/100）          │
│       ├── 创建/复用连接                   │
│       └── 返回 MCPConnection             │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  4. 获取工具                              │
│     connection.get_tools()               │
│     → [tool_a, tool_b, tool_c, ...]      │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  5. 工具过滤（TradingAgents 模块）        │
│     filter_tools_for_agent(              │
│         all_tools,                        │
│         agent_config,                    │
│         user_id                           │
│     )                                    │
│     → 根据智能体的 enabled_mcp_servers   │
│        过滤工具                           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  6. 创建 Agent                           │
│     agent = create_react_agent(           │
│         llm,                              │
│         tools=filtered_tools              │
│     )                                    │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  7. 任务执行（长连接保持）                │
│     LLM 决策调用工具                       │
│       ↓                                  │
│     tool.invoke()                        │
│       ↓                                  │
│     connection.session.call_tool()       │
│       ↓                                  │
│     MCP 服务器                            │
│       ↓                                  │
│     返回结果给 LLM                        │
│     （重复多次，保持同一连接）              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  8. 任务完成                              │
│     pool.mark_connection_complete()      │
│     → 启动 10 秒倒计时                    │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  9. 连接销毁                              │
│     10 秒后 → connection.destroy()        │
│     → 释放槽位                            │
└─────────────────────────────────────────┘
```

---

## 十一、模块间交互

```
┌─────────────────────────────────────────────────────────────┐
│                        前端                                  │
│  MCPServerManagementView.vue                                  │
│  AgentConfigView.vue                                          │
└─────────────────────────────────────────────────────────────┘
                    │ HTTP API
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                  MCP 模块                     │
├─────────────────────────────────────────────────────────────┤
│  api/routes.py          ← API 端点                            │
│  service/mcp_service.py  ← MCP 服务器 CRUD                     │
│  service/health_checker.py ← 健康检查                         │
│  pool/pool.py           ← 连接池管理                           │
│  pool/connection.py     ← 长连接管理                           │
│  core/adapter.py        ← MCP 适配器                           │
└─────────────────────────────────────────────────────────────┘
                    │ 提供长连接 + 工具
                    ↓
┌─────────────────────────────────────────────────────────────┐
│         TradingAgents 模块               │
├─────────────────────────────────────────────────────────────┤
│  tools/mcp_tool_filter.py ← MCP 工具过滤                       │
│  tools/registry.py      ← 工具注册表                          │
│  core/agent_engine.py    ← 使用工具创建 Agent                  │
└─────────────────────────────────────────────────────────────┘
                    │ LangChain Tools
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph Agent                             │
│  create_react_agent(llm, tools)                               │
└─────────────────────────────────────────────────────────────┘
                    │ LLM 调用
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                   LLM (Claude)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 十二、总结：方案要点

| 要点 | 说明 |
|------|------|
| **MCP 模块** | 独立模块，不放在 trading_agents 下 |
| **长连接** | 任务开始时建立，任务结束后销毁 |
| **并发限制** | 个人 100/用户，公共 10/用户 |
| **MCP 关闭** | 不影响进行中任务，新任务无法使用 |
| **工具过滤** | 在 TradingAgents 模块进行 |
| **健康检查** | 手动 + 自动（5分钟） |
| **API 路由** | 提供前端调用的接口 |
| **优雅关闭** | 完成 10 秒，失败 30 秒 |

---

## 附录：关键概念澄清

### 公共 MCP vs 个人 MCP

| 特性 | 公共 MCP | 个人 MCP |
|------|---------|---------|
| **配置者** | 管理员 | 普通用户 |
| **使用者** | 项目内所有用户 | 仅创建者自己 |
| **运行位置** | 本地服务器 | 本地服务器 |
| **对外服务** | ❌ 否 | ❌ 否 |
| **并发场景** | 多用户同时使用 | 单用户多任务并发 |
| **并发限制** | 每用户 10 | 每用户 100 |

### MCP 与 LLM 的连接方式

```
不是：每次工具调用重新连接 MCP
而是：任务开始时建立长连接 → 工具持有 session 引用 → LLM 通过引用调用
```

### 智能体配置 MCP 工具

```
MCP 长连接建立 → 返回所有工具 [tool_a, tool_b, tool_c]
    ↓
TradingAgents 模块过滤
    ├── 读取智能体配置 enabled_mcp_servers: ["mcp_x"]
    └── 只保留 mcp_x 提供的工具 [tool_a, tool_c]
    ↓
传给 LLM
```
