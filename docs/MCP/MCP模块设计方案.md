# MCP 模块完整文档

**版本**：v2.0
**创建日期**：2026-01-02
**最后更新**：2026-01-02
**状态**：已完成
**作者**：Claude AI

---

## 文档修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| v1.0 | 2025-12-xx | 初始设计方案 | Claude AI |
| v2.0 | 2026-01-02 | 融合实现细节，补充完整文档 | Claude AI |

---

## 目录

- [一、模块概述](#一模块概述)
- [二、模块目录结构](#二模块目录结构)
- [三、连接池设计](#三连接池设计)
- [四、连接生命周期](#四连接生命周期)
- [五、并发控制](#五并发控制)
- [六、MCP关闭的处理](#六mcp关闭的处理)
- [七、智能体MCP工具过滤](#七智能体mcp工具过滤)
- [八、健康检查](#八健康检查)
- [九、API端点设计](#九api端点设计)
- [十、配置管理](#十配置管理)
- [十一、数据模型](#十一数据模型)
- [十二、核心层实现](#十二核心层实现)
- [十三、服务层实现](#十三服务层实现)
- [十四、关键流程示例](#十四关键流程示例)
- [十五、模块间交互](#十五模块间交互)
- [十六、部署与运维](#十六部署与运维)
- [十七、故障排查](#十七故障排查)
- [十八、总结](#十八总结)

---

## 一、模块概述

### 1.1 模块定位

MCP (Model Context Protocol) 模块是一个**独立的数据源集成框架**，负责：

- 管理外部数据源（如股票数据、新闻、财务数据等）的MCP服务器配置
- 提供统一的连接池和并发控制
- 支持多种传输模式（stdio、SSE、HTTP、WebSocket）
- 实现自动健康检查和故障转移
- 为TradingAgents智能体提供工具调用接口

### 1.2 核心目标

| 目标 | 描述 |
|------|------|
| **统一管理** | 集中管理所有MCP服务器配置，支持系统级和用户级 |
| **高可用性** | 连接池复用、自动健康检查、故障隔离 |
| **性能优化** | 任务级长连接、并发控制、请求队列 |
| **灵活配置** | 支持YAML、数据库、环境变量三层配置优先级 |
| **标准兼容** | 基于LangChain官方MCP适配器，支持所有传输模式 |

### 1.3 技术栈

- **Python MCP SDK**: `mcp` 官方Python包
- **LangChain MCP Adapters**: `langchain-mcp-adapters` 官方适配器
- **数据库**: MongoDB（存储配置）
- **异步框架**: asyncio + FastAPI

### 1.4 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                    TradingAgents 智能体                   │
│                   (业务逻辑层)                            │
└─────────────────────────────────────────────────────────┘
                            ↑
                            │ 工具调用
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    MCP 工具过滤器                          │
│              (工具过滤 + 连接管理)                         │
└─────────────────────────────────────────────────────────┘
                            ↑
                            │ 获取连接
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   MCP 连接池                              │
│            (并发控制 + 连接复用 + 队列管理)                │
└─────────────────────────────────────────────────────────┘
                            ↑
                            │ 建立连接
                            ↓
┌─────────────────────────────────────────────────────────┐
│               LangChain MCP 适配器                        │
│         (官方 MultiServerMCPClient)                      │
└─────────────────────────────────────────────────────────┘
                            ↑
                            │ 传输协议
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  外部 MCP 服务器                          │
│        (股票数据、新闻、财务数据等数据源)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 二、模块目录结构

```
backend/modules/mcp/              # MCP 独立模块
│
├── __init__.py                   # 模块初始化
│
├── schemas.py                    # Pydantic数据模型
│
├── pool/                         # 连接池子模块
│   ├── __init__.py
│   ├── pool.py                   # MCPConnectionPool 主池管理器
│   ├── connection.py             # MCPConnection 长连接对象
│   └── queue.py                  # 请求队列管理
│
├── core/                         # 核心功能
│   ├── __init__.py
│   ├── adapter.py                # MCP 适配器（基于 langchain-mcp-adapters）
│   ├── session.py                # 会话管理
│   ├── interceptors.py           # 工具拦截器
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
└── config/                       # 配置管理
    ├── __init__.py
    ├── loader.py                 # 配置加载器
    ├── settings_models.py        # 设置数据模型
    ├── settings_service.py       # 设置服务
    └── default_config.yaml       # 默认配置文件


backend/modules/trading_agents/tools/  # TradingAgents 模块
│
├── mcp_tool_filter.py            # MCP 工具过滤（智能体配置相关）
├── registry.py                   # 工具注册表
└── ...


backend/modules/trading_agents/services/
│
└── mcp_patch.py                  # MCP兼容性补丁
```

---

## 三、连接池设计

### 3.1 MCPConnection（长连接对象）

**职责**：封装单个MCP服务器的长连接，管理连接状态和生命周期

**核心属性**：

```python
class MCPConnection:
    """任务级长连接对象"""

    # 唯一标识
    connection_id: str           # UUID
    server_id: str               # MCP 服务器 ID
    server_name: str             # MCP 服务器名称
    task_id: str                 # 任务 ID
    user_id: str                 # 用户 ID

    # 状态管理
    state: ConnectionState       # 连接状态
    _client: MultiServerMCPClient # langchain-mcp-adapters 客户端
    _tools: List[BaseTool]       # LangChain 工具列表

    # 时间戳
    created_at: datetime         # 创建时间
    last_used_at: datetime       # 最后使用时间

    # 清理管理
    _cleanup_timer: Optional[Task]  # 清理定时器
    _cleanup_lock: asyncio.Lock     # 清理锁
```

**状态枚举**：

```python
class ConnectionState(str, Enum):
    IDLE = "idle"                     # 空闲（未使用）
    CONNECTING = "connecting"         # 连接中
    ACTIVE = "active"                 # 活跃（长连接保持）
    CLOSING = "closing"               # 关闭中（任务完成后 10 秒）
    FAILED_CLEANUP = "failed_cleanup" # 失败清理中（30 秒）
    CLOSED = "closed"                 # 已关闭
```

**核心方法**：

```python
async def initialize() -> List[BaseTool]:
    """
    初始化连接，返回工具列表（官方标准实现）

    流程：
    1. 创建 MultiServerMCPClient
    2. 调用 client.get_tools() 加载工具
    3. 为工具添加 server_id 等属性
    4. 返回工具列表

    异常处理：
    - 连接失败 → 状态改为 FAILED_CLEANUP
    - 启动 30 秒清理倒计时
    """

async def mark_complete() -> None:
    """
    标记任务完成，启动延迟倒计时后销毁

    配置：complete_timeout = 10秒（可配置）
    流程：
    1. 状态改为 CLOSING
    2. 启动 10 秒定时器
    3. 定时器到期后调用 close()
    """

async def mark_failed() -> None:
    """
    标记任务失败，启动延迟倒计时后销毁

    配置：failed_timeout = 30秒（可配置）
    流程：
    1. 状态改为 FAILED_CLEANUP
    2. 启动 30 秒定时器
    3. 定时器到期后调用 close()
    """

async def close() -> None:
    """
    优雅关闭连接

    流程：
    1. 取消清理定时器
    2. 关闭客户端（如果支持）
    3. 清理工具列表
    4. 状态改为 CLOSED
    """

async def destroy() -> None:
    """
    强制销毁连接（立即关闭）

    用于：
    - 系统关闭时
    - 服务器删除时
    - 紧急情况
    """

@property
def tools() -> List[BaseTool]:
    """获取工具列表"""

@property
def is_active() -> bool:
    """是否处于活跃状态"""

@property
def is_usable() -> bool:
    """是否可用（可用于工具调用）"""
```

### 3.2 MCPConnectionPool（统一连接池）

**职责**：管理所有MCP服务器连接，实现并发控制和连接复用

**核心数据结构**：

```python
class MCPConnectionPool:
    """统一 MCP 连接池"""

    # 服务器配置注册表（从数据库加载）
    _servers: Dict[str, Dict[str, Any]]

    # 活跃连接
    _connections: Dict[str, MCPConnection]

    # 并发控制（每 server_id 独立）
    # 结构: _semaphores[server_id][user_id] = Semaphore
    _semaphores: Dict[str, Dict[str, asyncio.Semaphore]]

    # 请求队列（每 server_id 独立）
    _queues: Dict[str, asyncio.Queue]

    # 任务-连接映射
    _task_connections: Dict[str, str]  # task_id -> connection_id

    # 锁
    _server_lock: asyncio.Lock
    _connection_lock: asyncio.Lock

    # 并发参数配置（从配置文件加载）
    PERSONAL_MAX_CONCURRENCY = 100   # 个人 MCP：每个用户 100 并发
    PUBLIC_PER_USER_MAX = 10        # 公共 MCP：每个用户 10 并发
```

**核心方法**：

```python
async def register_server(server_config: MCPServerConfigResponse) -> None:
    """
    注册服务器到池子

    初始化：
    - 服务器配置
    - 用户级信号量
    - 请求队列
    """

async def unregister_server(server_id: str) -> None:
    """
    从池子注销服务器

    流程：
    1. 禁用服务器
    2. 清理资源
    """

async def disable_server(server_id: str) -> None:
    """
    禁用服务器（不影响进行中的任务）

    流程：
    1. 标记服务器为 disabled
    2. 遍历活跃连接，标记为关闭状态
    3. 不立即断开，让任务自然完成
    """

async def acquire_connection(
    server_id: str,
    task_id: str,
    user_id: str,
) -> MCPConnection:
    """
    获取或创建长连接

    流程：
    1. 检查服务器是否启用
    2. 获取用户级信号量
    3. 信号量可用 → 创建/复用连接
    4. 信号量不可用 → 进入队列等待
    5. 记录任务-连接映射
    6. 返回连接对象
    """

async def release_connection(connection_id: str) -> None:
    """
    释放连接（标记完成）

    流程：
    1. 查找连接对象
    2. 调用 connection.mark_complete()
    3. 清理任务-连接映射
    """

async def get_stats() -> Dict[str, Any]:
    """
    获取连接池统计信息

    返回：
    - 总服务器数
    - 活跃连接数
    - 等待请求数
    - 服务器配置信息
    """
```

### 3.3 请求队列（MCPRequestQueue）

**功能**：当并发限制达到上限时，新的请求进入队列等待

**队列配置**：
```python
# 个人服务器
queue_size: 200            # 最大容量
queue_timeout: 600          # 等待超时（秒）

# 公共服务器
queue_size: 50             # 最大容量
queue_timeout: 300          # 等待超时（秒）
```

**请求对象**：
```python
class MCPRequest:
    request_id: str           # 唯一ID (server_id:task_id:user_id)
    server_id: str            # 服务器ID
    task_id: str              # 任务ID
    user_id: str              # 用户ID
    callback: Callable        # 回调函数
    timeout: float            # 超时时间
    created_at: datetime      # 创建时间
    started_at: datetime      # 开始时间
    completed_at: datetime    # 完成时间

    @property
    def pending_time() -> float:    # 等待时长

    @property
    def processing_time() -> float: # 处理时长

    @property
    def total_time() -> float:      # 总时长
```

---

## 四、连接生命周期

### 4.1 状态机

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

### 4.2 时间线

**正常完成**：
```
T0:  创建任务 → acquire_connection()
T1:  连接建立 → 返回工具给 LLM → 任务执行...
Tx:  任务完成 → mark_complete() → 启动 10 秒倒计时
T10: 倒计时结束 → destroy()
```

**失败清理**：
```
T0:  创建任务 → acquire_connection()
T1:  连接建立 → 返回工具给 LLM → 任务执行...
Tx:  任务失败 → mark_failed() → 启动 30 秒倒计时
T30: 倒计时结束 → destroy()
```

**MCP 关闭**：
```
T0:  任务正在使用 MCP_X
T1:  管理员禁用 MCP_X → disable_server()
     → 标记服务器为 disabled
     → 已有连接继续运行
     → 新任务无法获取此连接
Tx:  任务完成 → 自然销毁
```

### 4.3 连接复用机制

**场景**：同一任务内多次工具调用

```
任务开始
  ↓
创建连接 (connection_id: abc123)
  ↓
LLM调用工具1 → 使用连接 abc123 → 返回结果
  ↓
LLM调用工具2 → 使用连接 abc123 → 返回结果 (复用)
  ↓
LLM调用工具3 → 使用连接 abc123 → 返回结果 (复用)
  ↓
任务完成 → mark_complete() → 10秒后销毁
```

**关键优势**：
- 减少连接建立开销
- 保持MCP会话状态（某些MCP服务器有状态）
- 提高工具调用性能

---

## 五、并发控制

### 5.1 并发限制

**双层并发限制**：

| 服务器类型 | 每用户最大并发 | 队列大小 | 适用场景 |
|-----------|--------------|---------|---------|
| **个人服务器** (is_system=False) | 100 | 200 | 用户个人MCP，单用户多任务 |
| **公共服务器** (is_system=True) | 10 | 50 | 管理员创建，所有用户共享 |

**配置加载**：
```python
# 从配置文件加载
PERSONAL_MAX_CONCURRENCY = get_pool_personal_max_concurrency()  # 100
PUBLIC_PER_USER_MAX = get_pool_public_per_user_max()           # 10

PERSONAL_QUEUE_SIZE = get_pool_personal_queue_size()          # 200
PUBLIC_QUEUE_SIZE = get_pool_public_queue_size()              # 50
```

### 5.2 信号量机制

**结构**：
```python
_semaphores: Dict[server_id, Dict[user_id, Semaphore]]

示例：
{
    "server_001": {
        "user_123": Semaphore(100),  # 个人服务器
        "user_456": Semaphore(100),
    },
    "server_002": {
        "user_123": Semaphore(10),   # 公共服务器
        "user_456": Semaphore(10),
    }
}
```

**工作流程**：
```
用户请求（120 个任务，用户 user_123，个人服务器）
      ↓
┌─────────────────┐
│  Semaphore(100) │ ← 只允许 100 个并发
└─────────────────┘
      ↓
┌───── 100 个执行中 ─────┐
└────────────────────────┘
      ↓
┌────── 20 个在队列 ──────┐ ← asyncio.Queue(maxsize=200)
└────────────────────────┘
      ↓
执行完成 → 释放信号量 → 从队列取下一个
```

### 5.3 队列模型

**队列操作**：
```python
# 入队（当信号量不可用时）
await queue.put(MCPRequest(...))

# 出队（阻塞，直到有可用槽位）
request = await queue.get()

# 队列统计
queue.qsize()     # 当前队列长度
queue.full()      # 是否已满
queue.empty()     # 是否为空
```

**超时处理**：
```python
# 个人服务器队列超时：600秒（10分钟）
# 公共服务器队列超时：300秒（5分钟）

# 超时后返回错误
if queue.pending_time > queue_timeout:
    raise TimeoutError("队列等待超时")
```

---

## 六、MCP关闭的处理

### 6.1 处理流程

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

### 6.2 禁用服务器的实现

```python
async def disable_server(server_id: str) -> None:
    """
    禁用服务器（不影响进行中的任务）
    """
    async with self._server_lock:
        if server_id not in self._servers:
            return

        # 标记为禁用
        self._servers[server_id]["enabled"] = False

        # 遍历活跃连接，标记为关闭状态
        # 注意：不立即断开，让任务自然完成
        connections_to_close = []
        for conn_id, conn in self._connections.items():
            if conn.server_id == server_id and conn.is_active:
                connections_to_close.append(conn)

        for conn in connections_to_close:
            logger.info(
                f"服务器 {server_id} 被禁用，"
                f"连接 {conn_id} 将在任务完成后关闭"
            )
            # 标记为关闭（但不强制断开）
            await conn.mark_complete()
```

### 6.3 连接获取时的检查

```python
async def acquire_connection(...) -> MCPConnection:
    # 检查服务器是否启用
    if not self._servers[server_id]["enabled"]:
        raise RuntimeError(
            f"服务器 {server_id} 已被禁用，无法获取新连接"
        )

    # 检查状态是否可用
    server_config = self._servers[server_id]["config"]
    if server_config.status != MCPServerStatusEnum.AVAILABLE:
        logger.warning(
            f"服务器 {server_id} 状态为 {server_config.status}，"
            f"尝试获取连接可能失败"
        )
        # 可以选择：
        # 1. 直接抛出异常
        # 2. 尝试重新连接
        # 3. 返回降级结果

    # 继续获取连接...
```

---

## 七、智能体MCP工具过滤

### 7.1 过滤位置

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

### 7.2 智能体配置

**配置结构**：
```python
class AgentConfig:
    slug: str                           # 智能体标识
    name: str                           # 智能体名称
    enabled_mcp_servers: List[MCPServerConfig]  # 启用的服务器

class MCPServerConfig:
    name: str                           # 服务器名称
    required: bool = False              # 是否必需（默认False）
```

**配置示例**：
```python
# 技术分析师配置
enabled_mcp_servers: [
    MCPServerConfig(name="FinanceMCP", required=True),    # 必需
    MCPServerConfig(name="NewsMCP", required=False),      # 可选
]

# 如果没有配置enabled_mcp_servers，默认使用所有可用的服务器
```

### 7.3 过滤逻辑

**步骤**：
```python
async def filter_tools_for_agent(
    agent_config: AgentConfig,
    user_id: str,
    task_id: str,
    all_tools: List[ToolDefinition],
) -> List[BaseTool]:
    """为智能体过滤 MCP 工具"""

    # 1. 获取用户可用的 MCP 服务器（已启用且可用状态）
    available_servers = await _get_available_servers(user_id)

    # 2. 解析智能体配置
    enabled_server_configs = agent_config.enabled_mcp_servers
    enabled_server_names = {config.name for config in enabled_server_configs}
    required_server_names = {
        config.name for config in enabled_server_configs
        if config.required
    }

    # 3. 默认行为：如果未配置，使用所有可用服务器
    if enabled_server_names:
        valid_server_names = enabled_server_names & available_servers.keys()
    else:
        valid_server_names = set(available_servers.keys())

    # 4. 检查必需服务器是否可用
    missing_required = required_server_names - valid_server_names
    if missing_required:
        raise RuntimeError(
            f"智能体 {agent_config.slug} 的必需 MCP 服务器不可用: {missing_required}"
        )

    # 5. 获取连接并转换为 LangChain 工具
    langchain_tools = []
    for server_name in valid_server_names:
        try:
            connection = await pool.acquire_connection(...)
            connection_tools = connection.tools

            # 过滤出属于此服务器的工具
            for tool in connection_tools:
                tool_def = _find_tool_definition(all_tools, tool.name)
                if tool_def and tool_def.mcp_server == server_name:
                    langchain_tools.append(tool)

        except Exception as e:
            is_required = server_name in required_server_names
            if is_required:
                raise RuntimeError(
                    f"智能体 {agent_config.slug} 的必需 MCP 服务器 '{server_name}' 连接失败: {e}"
                ) from e
            else:
                logger.warning(
                    f"智能体 {agent_config.slug} 的可选 MCP 服务器 '{server_name}' 连接失败（已跳过）: {e}"
                )
                continue

    return langchain_tools
```

### 7.4 容错机制

**必需服务器 vs 可选服务器**：

| 类型 | 失败行为 | 适用场景 |
|-----|---------|---------|
| **必需服务器** (required=True) | 抛出异常，任务终止 | 核心数据源，无法替代 |
| **可选服务器** (required=False) | 记录警告，继续执行 | 辅助数据源，可以降级 |

**示例**：
```python
# 技术分析师配置
enabled_mcp_servers: [
    MCPServerConfig(name="FinanceMCP", required=True),   # 必需：股票行情
    MCPServerConfig(name="NewsMCP", required=False),     # 可选：新闻数据
]

# FinanceMCP 连接失败 → 抛出异常，任务终止
# NewsMCP 连接失败 → 记录警告，继续执行（无新闻数据）
```

---

## 八、健康检查

### 8.1 手动触发

```
用户点击"测试连接"按钮
    ↓
前端调用: POST /api/mcp/servers/{id}/test
    ↓
后端: mcp_service.test_server_connection()
    ├── 创建临时连接
    ├── 尝试获取工具列表
    ├── 记录延迟（latency_ms）
    ├── 更新数据库状态
    └── 返回测试结果
    ↓
前端显示:
    ├── 成功：绿色 ✓ + 延迟时间
    └── 失败：红色 ✗ + 错误信息
```

**响应示例**：
```json
{
    "success": true,
    "message": "连接成功",
    "latency_ms": 150,
    "details": {
        "tools_count": 12,
        "server_version": "1.0.0"
    }
}
```

### 8.2 自动定时检查

**配置参数**：
```python
CHECK_INTERVAL = 300        # 检查间隔（秒）- 5分钟
CHECK_TIMEOUT = 30          # 单次检查超时（秒）
MAX_CONCURRENT_CHECKS = 5   # 最大并发检查数
STALE_THRESHOLD = 600       # 状态过期阈值（秒）- 10分钟
FAILURE_THRESHOLD = 3       # 连续失败次数阈值
```

**工作流程**：
```python
async def _check_loop(self):
    """健康检查循环"""
    while self._running:
        try:
            await self._run_health_check()
            await asyncio.sleep(self.CHECK_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"健康检查任务错误: {e}")
            await asyncio.sleep(60)

async def _run_health_check(self):
    """执行一次健康检查"""
    # 1. 获取所有启用的服务器
    servers = await get_all_enabled_servers()

    # 2. 并发检查（最多5个同时）
    semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_CHECKS)

    async def check_with_limit(server):
        async with semaphore:
            return await self._check_single_server(server)

    results = await asyncio.gather(
        *[check_with_limit(server) for server in servers],
        return_exceptions=True
    )

    # 3. 统计结果
    success_count = sum(1 for r in results if r is True)
    failure_count = sum(1 for r in results if r is False)

    logger.info(
        f"健康检查完成: 成功={success_count}, 失败={failure_count}"
    )
```

### 8.3 状态衰减机制

**追踪失败次数**：
```python
_failure_counts: dict[str, int] = {}

async def _check_single_server(self, server) -> bool:
    server_id = server.id

    try:
        # 尝试连接
        result = await test_server(server)

        if result.success:
            # 成功：重置失败计数
            _failure_counts[server_id] = 0
            await update_server_status(server_id, MCPServerStatusEnum.AVAILABLE)
            return True
        else:
            # 失败：增加失败计数
            _failure_counts[server_id] = _failure_counts.get(server_id, 0) + 1

            if _failure_counts[server_id] >= FAILURE_THRESHOLD:
                # 连续失败3次 → 标记为不可用
                await update_server_status(server_id, MCPServerStatusEnum.UNAVAILABLE)

            return False

    except Exception as e:
        logger.error(f"健康检查异常: {server_id}, error={e}")
        return False
```

### 8.4 健康检查与连接池的交互

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
│      ├── 如果 UNAVAILABLE，记录警告       │
│      └── 或尝试重新连接                   │
└─────────────────────────────────────────┘
```

---

## 九、API端点设计

### 9.1 MCP服务器管理（用户端点）

**权限**：所有认证用户

```http
# 创建服务器
POST /api/mcp/servers
Content-Type: application/json
Authorization: Bearer {token}

{
    "name": "股票数据服务",
    "transport": "streamable_http",
    "url": "http://finance-mcp.example.com/mcp",
    "headers": {"Authorization": "Bearer your-token"},
    "enabled": true,
    "is_system": false
}

# 列出服务器（分组返回）
GET /api/mcp/servers
Authorization: Bearer {token}

响应：
{
    "system": [...],   # 系统级服务器（所有用户可用）
    "user": [...]      # 用户个人服务器
}

# 获取单个服务器
GET /api/mcp/servers/{server_id}
Authorization: Bearer {token}

# 更新服务器
PUT /api/mcp/servers/{server_id}
Content-Type: application/json
Authorization: Bearer {token}

# 删除服务器
DELETE /api/mcp/servers/{server_id}
Authorization: Bearer {token}

# 测试连接
POST /api/mcp/servers/{server_id}/test
Authorization: Bearer {token}

响应：
{
    "success": true,
    "message": "连接成功",
    "latency_ms": 150
}

# 获取工具列表
GET /api/mcp/servers/{server_id}/tools
Authorization: Bearer {token}

响应：
{
    "tools": [
        {
            "name": "get_stock_data",
            "description": "获取股票行情数据",
            "server_id": "...",
            "server_name": "FinanceMCP"
        }
    ]
}
```

### 9.2 连接池管理（管理员端点）

**权限**：仅ADMIN/SUPER_ADMIN

```http
# 获取连接池统计
GET /api/mcp/pool/stats
Authorization: Bearer {admin_token}

响应：
{
    "pool": {
        "total_servers": 5,
        "active_connections": 12,
        "pending_requests": 3
    },
    "servers": {
        "server_id_1": {
            "name": "FinanceMCP",
            "is_system": true,
            "status": "available",
            "enabled": true
        }
    }
}

# 禁用服务器
POST /api/mcp/pool/servers/{server_id}/disable
Authorization: Bearer {admin_token}

响应：
{
    "message": "MCP服务器已禁用",
    "success": true
}
```

### 9.3 系统配置（管理员端点）

**权限**：仅ADMIN/SUPER_ADMIN

```http
# 获取系统配置
GET /api/mcp/settings
Authorization: Bearer {admin_token}

响应：
{
    "pool_personal_max_concurrency": 100,
    "pool_public_per_user_max": 10,
    "health_check_enabled": true,
    "health_check_interval": 300
}

# 更新系统配置
PUT /api/mcp/settings
Content-Type: application/json
Authorization: Bearer {admin_token}

{
    "pool_personal_max_concurrency": 200,
    "health_check_interval": 600
}

# 恢复默认配置
POST /api/mcp/settings/reset
Authorization: Bearer {admin_token}
```

### 9.4 向后兼容端点（已废弃）

保留旧路径以兼容前端：

```http
POST /api/trading-agents/mcp-servers        → POST /api/mcp/servers
GET  /api/trading-agents/mcp-servers        → GET  /api/mcp/servers
GET  /api/trading-agents/mcp-servers/{id}   → GET  /api/mcp/servers/{id}
PUT  /api/trading-agents/mcp-servers/{id}   → PUT  /api/mcp/servers/{id}
DELETE /api/trading-agents/mcp-servers/{id} → DELETE /api/mcp/servers/{id}
POST /api/trading-agents/mcp-servers/{id}/test → POST /api/mcp/servers/{id}/test
GET /api/trading-agents/mcp-servers/{id}/tools → GET /api/mcp/servers/{id}/tools
```

---

## 十、配置管理

### 10.1 三层配置优先级

```
1. 数据库配置（优先级最高）
   └─ 用户通过前端修改的配置
   └─ 存储在 MongoDB mcp_settings 集合
   └─ 格式：下划线命名（pool_personal_max_concurrency）

2. YAML默认配置
   └─ default_config.yaml 文件
   └─ 提供合理的默认值
   └─ 格式：嵌套结构（pool.personal.max_concurrency）

3. 环境变量覆盖
   └─ 运行时动态设置
   └─ 格式：MCP_POOL__PERSONAL__MAX_CONCURRENCY=100
```

### 10.2 配置加载流程

```python
def load_config():
    # 1. 加载YAML默认配置
    config = load_yaml_config()

    # 2. 覆盖数据库配置
    db_config = load_db_config_sync()
    config = deep_merge(config, db_config)

    # 3. 覆盖环境变量
    env_config = load_env_config()
    config = deep_merge(config, env_config)

    return config
```

### 10.3 默认配置文件

**位置**：`backend/modules/mcp/config/default_config.yaml`

```yaml
# =============================================================================
# 连接池配置
# =============================================================================
pool:
  # 个人 MCP 并发限制
  personal:
    max_concurrency: 100       # 每用户最大并发连接数
    queue_size: 200            # 请求队列最大容量
    queue_timeout: 600         # 队列等待超时时间（秒）

  # 公共 MCP 并发限制
  public:
    per_user_max: 10           # 每用户最大并发连接数
    queue_size: 50             # 请求队列最大容量
    queue_timeout: 300         # 队列等待超时时间（秒）

# =============================================================================
# 连接生命周期配置
# =============================================================================
connection:
  complete_timeout: 10         # 任务完成后等待时间（秒），之后销毁连接
  failed_timeout: 30           # 任务失败后等待时间（秒），之后销毁连接
  idle_timeout: 600            # 空闲超时时间（秒），超时后销毁连接

  # 连接参数
  connect_timeout: 30          # 连接建立超时时间（秒）
  read_timeout: 120            # 读取数据超时时间（秒）
  keepalive_interval: 30       # 保活间隔时间（秒）

# =============================================================================
# 健康检查配置
# =============================================================================
health_check:
  enabled: true                # 是否启用自动健康检查
  interval: 300                # 检查间隔时间（秒）- 5分钟
  timeout: 30                  # 单次检查超时时间（秒）
  retry_attempts: 3            # 失败重试次数
  max_concurrent_checks: 5     # 最大并发检查数

  # 状态衰减配置
  stale_threshold: 600         # 状态过期阈值（秒）- 10分钟
  failure_threshold: 3         # 连续失败次数阈值

# =============================================================================
# 清理任务配置
# =============================================================================
cleanup:
  enabled: true                # 是否启用自动清理
  interval: 60                 # 清理任务执行间隔（秒）
  batch_size: 10               # 每次清理的最大连接数

# =============================================================================
# 会话管理配置
# =============================================================================
session:
  session_timeout: 600         # 会话超时时间（秒）
  idle_timeout: 300            # 空闲超时时间（秒）
```

### 10.4 环境变量配置

**命名规则**：`MCP_<SECTION>__<KEY>`

**示例**：
```bash
# 连接池配置
export MCP_POOL__PERSONAL__MAX_CONCURRENCY=200
export MCP_POOL__PUBLIC__PER_USER_MAX=20

# 健康检查配置
export MCP_HEALTH_CHECK__ENABLED=false
export MCP_HEALTH_CHECK__INTERVAL=600

# 连接生命周期
export MCP_CONNECTION__COMPLETE_TIMEOUT=30
export MCP_CONNECTION__FAILED_TIMEOUT=60
```

### 10.5 数据库配置

**集合**：`mcp_settings`

**文档结构**：
```python
{
    "_id": "system",                       # 固定ID
    "pool_personal_max_concurrency": 100,  # 下划线命名
    "pool_public_per_user_max": 10,
    "pool_personal_queue_size": 200,
    "pool_public_queue_size": 50,
    "connection_complete_timeout": 10,
    "connection_failed_timeout": 30,
    "health_check_enabled": true,
    "health_check_interval": 300,
    # ... 其他配置
}
```

**配置服务**：
```python
# 获取配置
db_settings = await get_system_settings()

# 更新配置
await update_system_settings({
    "pool_personal_max_concurrency": 200
})

# 恢复默认
await reset_to_defaults()

# 重新加载（清除缓存）
reload_mcp_config()
```

### 10.6 配置访问接口

**提供了一组便捷函数**：
```python
# 连接池配置
get_pool_personal_max_concurrency()    # → 100
get_pool_public_per_user_max()          # → 10
get_pool_personal_queue_size()          # → 200
get_pool_public_queue_size()            # → 50

# 连接生命周期
get_connection_complete_timeout()       # → 10秒
get_connection_failed_timeout()         # → 30秒

# 健康检查
get_health_check_enabled()              # → true
get_health_check_interval()             # → 300秒
get_health_check_timeout()              # → 30秒
get_health_check_max_concurrent_checks() # → 5
```

---

## 十一、数据模型

### 11.1 MCP服务器配置模型

#### 11.1.1 数据库结构

```python
{
    "_id": ObjectId,                    # MongoDB ObjectId
    "name": str,                        # 服务器名称
    "transport": str,                   # 传输模式
    # stdio模式配置
    "command": str | None,              # 启动命令
    "args": List[str],                  # 命令参数
    "env": Dict[str, str],              # 环境变量
    # HTTP/SSE/WebSocket模式配置
    "url": str | None,                  # 服务器URL
    "headers": Dict[str, str],          # HTTP请求头
    # 认证配置（兼容旧版本）
    "auth_type": str,                   # 认证类型
    "auth_token": str | None,           # 认证令牌
    # 通用配置
    "auto_approve": List[str],          # 自动批准的工具列表
    "enabled": bool,                    # 是否启用
    "is_system": bool,                  # 是否为系统级服务
    "owner_id": str | None,             # 所有者ID（系统级为None）
    # 状态信息
    "status": str,                      # 服务器状态
    "last_check_at": datetime | None,   # 最后检查时间
    # 时间戳
    "created_at": datetime,             # 创建时间
    "updated_at": datetime,             # 更新时间
}
```

#### 11.1.2 Pydantic模型

**创建请求**：
```python
class MCPServerConfigCreate(BaseModel):
    name: str                           # 服务器名称（1-100字符）
    transport: TransportModeEnum        # 传输模式
    command: Optional[str]               # stdio命令
    args: List[str]                      # 命令参数
    env: Dict[str, str]                 # 环境变量
    url: Optional[str]                   # HTTP URL
    headers: Dict[str, str]              # HTTP头
    auth_type: AuthTypeEnum              # 认证类型
    auth_token: Optional[str]            # 认证令牌
    auto_approve: List[str]              # 自动批准工具
    enabled: bool = True                 # 是否启用
    is_system: bool = False              # 是否为系统级
```

**响应模型**：
```python
class MCPServerConfigResponse(BaseModel):
    id: str                             # 服务器ID
    name: str                            # 服务器名称
    transport: TransportModeEnum         # 传输模式
    command: Optional[str]               # stdio命令
    args: List[str]                      # 命令参数
    env: Dict[str, str]                  # 环境变量
    url: Optional[str]                   # HTTP URL
    headers: Dict[str, str]              # HTTP头
    auth_type: AuthTypeEnum              # 认证类型
    auth_token: Optional[str]            # 认证令牌
    auto_approve: List[str]              # 自动批准工具
    enabled: bool                        # 是否启用
    is_system: bool                      # 是否为系统级
    owner_id: Optional[str]              # 所有者ID
    status: MCPServerStatusEnum          # 服务器状态
    last_check_at: Optional[datetime]    # 最后检查时间
    created_at: datetime                 # 创建时间
    updated_at: datetime                 # 更新时间
```

### 11.2 枚举类型

```python
class MCPServerStatusEnum(str, Enum):
    """MCP服务器状态枚举"""
    AVAILABLE = "available"              # 可用
    UNAVAILABLE = "unavailable"          # 不可用
    UNKNOWN = "unknown"                  # 未知

class TransportModeEnum(str, Enum):
    """MCP传输模式枚举"""
    STDIO = "stdio"                      # 标准输入输出
    SSE = "sse"                          # Server-Sent Events
    HTTP = "http"                        # HTTP
    STREAMABLE_HTTP = "streamable_http"  # Streamable HTTP（推荐）
    WEBSOCKET = "websocket"              # WebSocket

class AuthTypeEnum(str, Enum):
    """MCP认证类型枚举"""
    NONE = "none"                        # 无认证
    BEARER = "bearer"                    # Bearer Token
    BASIC = "basic"                      # Basic Auth
```

### 11.3 其他数据模型

```python
class ConnectionTestResponse(BaseModel):
    """连接测试响应"""
    success: bool                        # 测试是否成功
    message: str                         # 消息
    latency_ms: Optional[int]            # 延迟（毫秒）
    details: Optional[Dict[str, Any]]    # 详细信息

class MCPToolInfo(BaseModel):
    """MCP工具信息"""
    name: str                            # 工具名称
    description: str                     # 工具描述
    server_id: str                       # 服务器ID
    server_name: str                     # 服务器名称
```

---

## 十二、核心层实现

### 12.1 MCP适配器（core/adapter.py）

**职责**：基于LangChain官方标准，构建MCP客户端连接

**核心函数**：

```python
# 连接配置构建器（官方标准）
build_stdio_connection(command, args, env)
    → Dict[str, Any]  # stdio模式

build_sse_connection(url, headers)
    → Dict[str, Any]  # SSE模式

build_streamable_http_connection(url, headers)
    → Dict[str, Any]  # HTTP模式（推荐）

build_websocket_connection(url)
    → Dict[str, Any]  # WebSocket模式

# 客户端创建（官方标准）
create_mcp_client(server_configs)
    → MultiServerMCPClient

get_mcp_tools(server_name, connection_config)
    → List[BaseTool]  # 获取工具列表

get_mcp_tools_multi_server(server_configs)
    → Dict[str, List[BaseTool]]  # 多服务器工具
```

**认证头构建**：
```python
def build_auth_headers(headers, auth_type, auth_token):
    """
    构建认证头（官方标准）

    支持两种配置方式：
    1. 直接配置 headers 字段（优先级更高）
    2. 使用 auth_type + auth_token 组合

    认证类型：
    - bearer: Bearer Token 认证
    - basic: Base64编码的用户名:密码
    - none: 无认证
    """
    if headers:
        return headers

    if auth_type == "bearer":
        return {"Authorization": f"Bearer {auth_token}"}
    elif auth_type == "basic":
        encoded = base64.b64encode(auth_token.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    return None
```

**传输模式映射**：
```python
def map_transport_mode(transport: str) -> str:
    """
    映射传输模式到官方框架格式

    映射规则：
    - stdio → stdio
    - sse → sse
    - http → streamable_http (推荐)
    - streamable_http → streamable_http
    - websocket → websocket
    """
    mapping = {
        "stdio": "stdio",
        "sse": "sse",
        "http": "streamable_http",
        "streamable_http": "streamable_http",
        "websocket": "websocket",
    }
    return mapping.get(transport.lower())
```

### 12.2 会话管理（core/session.py）

**职责**：基于官方推荐的Session上下文管理器模式

**核心组件**：

```python
@asynccontextmanager
async def mcp_session_context(client, server_name):
    """
    MCP Session 上下文管理器（官方标准实现）

    使用官方的 client.session() 上下文管理器，提供：
    - 自动资源清理
    - 状态持久化
    - 多工具调用间保持状态

    示例：
        async with mcp_session_context(client, "finance") as session:
            tools = await load_mcp_tools(session)
            result1 = await session.call_tool("get_stock", {...})
            result2 = await session.call_tool("get_price", {...})
    """
    async with client.session(server_name) as session:
        yield session

# 有状态工具加载（官方标准方式）
async def load_tools_with_session(client, server_name):
    """使用有状态会话加载 MCP 工具"""
    async with mcp_session_context(client, server_name) as session:
        tools = await load_mcp_tools(session)
        return tools

# 有状态资源加载（官方标准方式）
async def load_resources_with_session(client, server_name, uris=None):
    """使用有状态会话加载 MCP 资源"""
    async with mcp_session_context(client, server_name) as session:
        if uris:
            resources = await load_mcp_resources(session, uris=uris)
        else:
            resources = await load_mcp_resources(session)
        return resources

# 有状态Prompt加载（官方标准方式）
async def load_prompt_with_session(client, server_name, prompt_name, arguments=None):
    """使用有状态会话加载 MCP Prompt"""
    async with mcp_session_context(client, server_name) as session:
        if arguments:
            messages = await load_mcp_prompt(session, prompt_name, arguments=arguments)
        else:
            messages = await load_mcp_prompt(session, prompt_name)
        return messages
```

**会话管理器**：
```python
class MCPSessionManager:
    """MCP 会话管理器"""

    async def start_cleanup_task():
        """启动会话清理后台任务"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task():
        """停止会话清理后台任务"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()

    async def _cleanup_loop(self):
        """会话清理循环"""
        while self._running:
            await self._cleanup_expired_sessions()
            await asyncio.sleep(300)  # 每5分钟清理一次
```

### 12.3 工具拦截器（core/interceptors.py）

**职责**：提供AOP（面向切面编程）风格的工具调用拦截

**内置拦截器**：

```python
# 1. 日志拦截器
async def logging_interceptor(request, handler):
    """记录所有 MCP 工具调用"""
    start_time = datetime.now()
    logger.info(f"调用工具: tool={tool_name}, args={args}")

    result = await handler(request)

    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"工具成功: duration={duration:.2f}s")
    return result

# 2. 重试拦截器
async def retry_interceptor(request, handler, max_retries=3, delay=1.0, backoff_factor=2.0):
    """自动重试失败的工具调用"""
    for attempt in range(max_retries):
        try:
            return await handler(request)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = delay * (backoff_factor ** attempt)
                await asyncio.sleep(wait_time)
            else:
                raise

# 3. 超时拦截器
async def timeout_interceptor(request, handler, timeout=30.0):
    """为工具调用设置超时"""
    return await asyncio.wait_for(handler(request), timeout=timeout)

# 4. 认证检查拦截器
async def require_authentication_interceptor(request, handler, sensitive_tools, user_id):
    """敏感工具需要认证"""
    if tool_name in sensitive_tools and not user_id:
        raise PermissionError("工具需要认证")
    return await handler(request)

# 5. 用户上下文注入拦截器
async def inject_user_context_interceptor(request, handler, user_id, user_context):
    """注入用户信息到工具参数"""
    if user_id:
        request.args['user_id'] = user_id
    if user_context:
        request.args.update(user_context)
    return await handler(request)

# 6. 降级拦截器
async def fallback_interceptor(request, handler, fallback_result, fallback_on_errors):
    """工具调用失败时返回降级结果"""
    try:
        return await handler(request)
    except tuple(fallback_on_errors or [Exception]):
        return fallback_result
```

**拦截器构建器**：
```python
class InterceptorBuilder:
    """Interceptor 构建器 - 方便组合多个拦截器"""

    def add_logging(self) -> "InterceptorBuilder":
        """添加日志拦截器"""

    def add_retry(self, max_retries=3, delay=1.0, backoff_factor=2.0) -> "InterceptorBuilder":
        """添加重试拦截器"""

    def add_timeout(self, timeout=30.0) -> "InterceptorBuilder":
        """添加超时拦截器"""

    def add_user_context_injection(self, user_id, user_context) -> "InterceptorBuilder":
        """添加用户上下文注入拦截器"""

    def add_authentication_check(self, sensitive_tools, user_id) -> "InterceptorBuilder":
        """添加认证检查拦截器"""

    def add_fallback(self, fallback_result, fallback_on_errors) -> "InterceptorBuilder":
        """添加降级拦截器"""

    def add_custom(self, interceptor) -> "InterceptorBuilder":
        """添加自定义拦截器"""

    def build(self) -> List[Callable]:
        """构建拦截器列表（按添加顺序）"""
```

**预定义配置**：
```python
get_default_interceptors()
    → 开发环境：日志 + 超时(30s)

get_production_interceptors(max_retries=3, timeout=60.0)
    → 生产环境：日志 + 重试(3次) + 超时(60s)

get_secure_interceptors(sensitive_tools, user_id, max_retries=3, timeout=30.0)
    → 安全增强：日志 + 重试 + 认证 + 用户上下文 + 超时
```

### 12.4 异常定义（core/exceptions.py）

```python
class MCPError(Exception):
    """MCP 基础异常"""

class MCPConnectionError(MCPError):
    """MCP 连接错误"""

class MCPTimeoutError(MCPError):
    """MCP 超时错误"""

class MCPProtocolError(MCPError):
    """MCP 协议错误"""

class MCPUnavailableError(MCPError):
    """MCP 服务器不可用错误"""

class MCPToolError(MCPError):
    """MCP 工具调用错误"""

class MCPAuthenticationError(MCPError):
    """MCP 认证错误"""

class MCPConfigurationError(MCPError):
    """MCP 配置错误"""
```

---

## 十三、服务层实现

### 13.1 MCP服务（service/mcp_service.py）

**职责**：提供MCP服务器的CRUD操作和连接测试功能

**核心方法**：

```python
# CRUD操作
async def create_server(user_id, request, is_admin)
    → MCPServerConfigResponse
    # 权限检查：只有管理员可以创建系统级服务
    # 验证环境变量格式
    # 创建后立即进行状态检测（异步后台任务）

async def get_server(server_id, user_id, is_admin)
    → Optional[MCPServerConfigResponse]
    # 权限检查：系统级配置所有用户可读
    # 用户配置只有创建者可读

async def list_servers(user_id, is_admin)
    → Dict[str, List[MCPServerConfigResponse]]
    # 返回：{"system": [...], "user": [...]}

async def update_server(server_id, user_id, request, is_admin)
    → MCPServerConfigResponse

async def delete_server(server_id, user_id, is_admin)
    → bool

# 连接测试
async def test_server_connection(server_id, user_id, is_admin)
    → ConnectionTestResponse
    ├── 创建临时连接
    ├── 尝试获取工具列表
    ├── 记录延迟（latency_ms）
    ├── 更新数据库状态
    └── 返回测试结果

# 工具查询
async def get_server_tools(server_id, user_id, is_admin)
    → List[dict]
```

**权限检查**：
```python
# 创建时的权限检查
if request.is_system and not is_admin:
    raise PermissionError("只有管理员可以创建公共服务")

# 查询时的权限过滤
if is_admin:
    # 管理员查看所有服务器
    all_servers = ...
else:
    # 普通用户查看系统级服务器（只读）和自己的服务器
    system_servers = ...  # 只读
    user_servers = ...    # 自己创建的
```

### 13.2 健康检查器（service/health_checker.py）

**职责**：后台任务，定期自动检测所有启用MCP服务器的状态

**配置参数**：
```python
CHECK_INTERVAL = 300       # 检查间隔（秒）- 5分钟
CHECK_TIMEOUT = 30         # 单次检查超时（秒）
MAX_CONCURRENT_CHECKS = 5  # 最大并发检查数
STALE_THRESHOLD = 600      # 状态过期阈值（秒）- 10分钟
FAILURE_THRESHOLD = 3      # 连续失败次数阈值
```

**工作流程**：
```
1. 每5分钟触发一次健康检查
   ↓
2. 查询所有启用的MCP服务器
   ↓
3. 并发检查（最多5个同时）
   ├─ 调用 test_server_connection()
   ├─ 测量延迟
   └─ 更新数据库状态
   ↓
4. 状态衰减策略
   ├─ 连续失败3次 → 标记为UNAVAILABLE
   └─ 成功1次 → 标记为AVAILABLE
   ↓
5. 统计结果并记录日志
```

**状态衰减机制**：
```python
# 追踪连续失败次数
_failure_counts: dict[str, int] = {}

# 检查逻辑
if connection_success:
    _failure_counts[server_id] = 0
    status = MCPServerStatusEnum.AVAILABLE
else:
    _failure_counts[server_id] += 1
    if _failure_counts[server_id] >= FAILURE_THRESHOLD:
        status = MCPServerStatusEnum.UNAVAILABLE
```

---

## 十四、关键流程示例

### 14.1 任务使用MCP的完整流程

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
│     connection.initialize()              │
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
│     连接 session.call_tool()              │
│       ↓                                  │
│     MCP 服务器                            │
│       ↓                                  │
│     返回结果给 LLM                        │
│     （重复多次，保持同一连接）              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  8. 任务完成                              │
│     connection.mark_complete()            │
│     → 启动 10 秒倒计时                    │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  9. 连接销毁                              │
│     10 秒后 → connection.close()           │
│     → 释放槽位                            │
└─────────────────────────────────────────┘
```

### 14.2 连接复用示例

**场景**：同一任务内多次工具调用

```
任务开始
  ↓
创建连接 (connection_id: abc123)
  ↓
调用工具1: get_stock_data
  ├─ 使用连接 abc123
  ├─ session.call_tool("get_stock_data", {...})
  └─ 返回结果
  ↓
调用工具2: get_company_info
  ├─ 使用连接 abc123 (复用)
  ├─ session.call_tool("get_company_info", {...})
  └─ 返回结果
  ↓
调用工具3: get_financials
  ├─ 使用连接 abc123 (复用)
  ├─ session.call_tool("get_financials", {...})
  └─ 返回结果
  ↓
任务完成 → mark_complete() → 10秒后销毁
```

### 14.3 并发控制示例

**场景**：用户同时启动多个任务

```
用户启动120个分析任务
  ↓
连接池处理：
├─ 100个任务获取信号量成功 → 立即执行
└─ 20个任务进入队列等待
  ↓
第1个任务完成 → 释放信号量
  ↓
队列中的第101个任务获取信号量 → 开始执行
  ↓
...循环往复
```

---

## 十五、模块间交互

### 15.1 模块依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                        前端                                  │
│  - MCPServerManagementView.vue (MCP服务器管理)                   │
│  - AgentConfigView.vue (智能体配置)                             │
│  - AnalysisDetailView.vue (任务详情)                            │
└─────────────────────────────────────────────────────────────┘
                    │ HTTP API
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                  MCP 模块                                     │
├─────────────────────────────────────────────────────────────┤
│  api/routes.py          ← API 端点                            │
│  service/mcp_service.py  ← MCP 服务器 CRUD                     │
│  service/health_checker.py ← 健康检查                         │
│  pool/pool.py           ← 连接池管理                           │
│  pool/connection.py     ← 长连接管理                           │
│  core/adapter.py        ← MCP 适配器                           │
│  core/session.py        ← 会话管理                             │
│  core/interceptors.py   ← 工具拦截器                           │
│  config/loader.py       ← 配置管理                             │
└─────────────────────────────────────────────────────────────┘
                    │ 提供长连接 + 工具
                    ↓
┌─────────────────────────────────────────────────────────────┐
│         TradingAgents 模块                                    │
├─────────────────────────────────────────────────────────────┤
│  tools/mcp_tool_filter.py ← MCP 工具过滤                       │
│  tools/registry.py      ← 工具注册表                          │
│  core/agent_engine.py    ← 使用工具创建 Agent                  │
│  services/mcp_patch.py   ← MCP兼容性补丁                       │
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
│                   LLM (Claude/GPT)                            │
└─────────────────────────────────────────────────────────────┘
```

### 15.2 数据流向

```
用户操作
  ↓
前端 HTTP 请求
  ↓
MCP API (api/routes.py)
  ↓
MCP Service (service/mcp_service.py)
  ├─ 数据库操作（MongoDB）
  └─ 连接池操作（pool/pool.py）
  ↓
连接池 (pool/pool.py)
  ├─ 创建连接（pool/connection.py）
  ├─ 并发控制（Semaphore）
  └─ 队列管理（queue.py）
  ↓
MCP 适配器 (core/adapter.py)
  ├─ 构建连接配置
  └─ 创建 LangChain MCP 客户端
  ↓
外部 MCP 服务器
  ├─ stdio (本地进程)
  ├─ SSE (Server-Sent Events)
  ├─ HTTP (Streamable HTTP)
  └─ WebSocket
  ↓
返回工具列表
  ↓
工具过滤器 (trading_agents/tools/mcp_tool_filter.py)
  ├─ 根据智能体配置过滤
  ├─ 处理必需/可选服务器
  └─ 返回过滤后的工具
  ↓
创建 Agent (trading_agents/core/agent_engine.py)
  ├─ create_react_agent()
  ├─ 绑定 LLM
  └─ 绑定工具
  ↓
任务执行
  ├─ LLM 决策调用工具
  ├─ 工具调用 MCP 服务器
  └─ 返回结果给 LLM
  ↓
任务完成
  ├─ 标记连接完成
  └─ 10秒后销毁连接
```

---

## 十六、部署与运维

### 16.1 应用启动流程

```python
# backend/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段
    logger.info("正在启动...")

    # 1. 应用MCP补丁（修复自定义错误格式问题）
    from modules.trading_agents.services.mcp_patch import apply_mcp_patches
    try:
        apply_mcp_patches()
        logger.info("✅ MCP 补丁已应用")
    except Exception as e:
        logger.warning(f"⚠️ MCP 补丁应用失败: {e}")

    # 2. 启动MCP健康检查器
    from modules.mcp.service.health_checker import get_mcp_health_checker
    try:
        health_checker = get_mcp_health_checker()
        await health_checker.start()
        logger.info("✅ MCP 健康检查器已启动")
    except Exception as e:
        logger.warning(f"⚠️ MCP 健康检查器启动失败: {e}")

    # 3. 启动MCP会话管理器
    from modules.mcp.core.session import get_mcp_session_manager
    try:
        session_manager = get_mcp_session_manager()
        await session_manager.start_cleanup_task()
        logger.info("✅ MCP 会话管理器已启动")
    except Exception as e:
        logger.warning(f"⚠️ MCP 会话管理器启动失败: {e}")

    logger.info("应用启动完成")

    yield

    # 关闭阶段
    logger.info("正在关闭...")

    # 1. 停止MCP健康检查器
    try:
        await health_checker.stop()
        logger.info("✅ MCP 健康检查器已停止")
    except Exception as e:
        logger.warning(f"⚠️ MCP 健康检查器停止失败: {e}")

    # 2. 停止MCP会话管理器
    try:
        await session_manager.stop_cleanup_task()
        logger.info("✅ MCP 会话管理器已停止")
    except Exception as e:
        logger.warning(f"⚠️ MCP 会话管理器停止失败: {e}")

    logger.info("应用已关闭")
```

### 16.2 监控指标

**连接池指标**：
- 总服务器数
- 活跃连接数
- 等待请求数
- 队列长度

**健康检查指标**：
- 检查成功率
- 平均延迟
- 失败服务器列表

**性能指标**：
- 连接建立时间
- 工具调用延迟
- 连接复用率

### 16.3 日志规范

**关键日志点**：
```python
# 连接创建
logger.info(
    f"[MCPConnection] 创建连接对象: "
    f"connection_id={connection_id}, "
    f"server_id={server_id}, "
    f"task_id={task_id}"
)

# 连接成功
logger.info(
    f"[MCPConnection] 连接成功: {connection_id}, "
    f"获取到 {len(tools)} 个工具"
)

# 工具调用
logger.info(
    f"[MCP Interceptor] 调用工具: "
    f"server={server}, tool={tool}, "
    f"args={args}"
)

# 健康检查
logger.info(
    f"健康检查完成: "
    f"成功={success_count}, "
    f"失败={failure_count}"
)

# 并发控制
logger.debug(
    f"[MCPConnectionPool] 用户并发: "
    f"server={server_id}, user={user_id}, "
    f"active={active_count}/{max_concurrency}"
)
```

### 16.4 故障恢复

**场景1：MCP服务器临时不可用**
- 健康检查器标记为UNAVAILABLE
- 新任务不再获取该服务器的连接
- 已有连接继续运行直到自然结束

**场景2：连接池耗尽**
- 新请求进入队列等待
- 队列满时返回错误
- 建议增加并发限制或扩容

**场景3：健康检查失败**
- 记录错误日志
- 不影响其他服务器
- 下次检查周期重试

---

## 十七、故障排查

### 17.1 常见问题

#### 问题1：连接超时

**现象**：工具调用超时

**排查步骤**：
1. 检查MCP服务器是否正常运行
2. 检查网络连接是否通畅
3. 检查配置的timeout是否合理
4. 查看日志中的具体错误信息

**解决方案**：
- 增加超时时间配置
- 检查防火墙规则
- 验证URL和认证信息

#### 问题2：并发限制导致排队

**现象**：请求处理缓慢，队列积压

**排查步骤**：
1. 查看连接池统计信息
2. 检查并发限制配置
3. 分析任务执行时长

**解决方案**：
- 增加并发限制配置
- 优化工具调用性能
- 增加队列大小

#### 问题3：工具调用失败

**现象**：特定工具调用返回错误

**排查步骤**：
1. 检查工具参数是否正确
2. 查看MCP服务器日志
3. 验证工具是否在auto_approve列表中

**解决方案**：
- 检查工具参数格式
- 添加工具到auto_approve列表
- 联系MCP服务器提供方

### 17.2 调试技巧

#### 启用详细日志

```python
# backend/core/logging_config.py
LOG_LEVEL = "DEBUG"  # 生产环境使用INFO
```

#### 查看连接池状态

```bash
curl -H "Authorization: Bearer {admin_token}" \
  http://localhost:8000/api/mcp/pool/stats
```

#### 手动测试MCP服务器

```python
# 使用Python REPL
from modules.mcp.service.mcp_service import get_mcp_service
service = get_mcp_service()
result = await service.test_server_connection(server_id, user_id, is_admin=True)
print(result)
```

### 17.3 性能优化建议

**优化并发配置**：
- 根据MCP服务器性能调整并发限制
- 监控队列长度，避免积压
- 平衡个人服务器和公共服务器的限制

**优化连接生命周期**：
- 合理设置complete_timeout（默认10秒）
- 根据任务执行时长调整failed_timeout（默认30秒）
- 监控连接复用率

**优化健康检查**：
- 根据服务器稳定性调整检查间隔
- 避免过于频繁的检查影响性能
- 合理设置超时时间

---

## 十八、总结

### 18.1 方案要点

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

### 18.2 关键特性

1. **任务级长连接管理**：任务完成后延迟10秒销毁，失败后延迟30秒销毁
2. **双层并发控制**：个人服务器（100并发）vs 公共服务器（每用户10并发）
3. **三层配置优先级**：数据库 > YAML > 环境变量
4. **自动健康检查**：每5分钟检查一次，状态衰减机制
5. **官方标准兼容**：基于LangChain MCP Adapters，支持所有传输模式
6. **灵活的工具过滤**：支持必需/可选服务器配置

### 18.3 附录：关键概念澄清

#### 公共 MCP vs 个人 MCP

| 特性 | 公共 MCP | 个人 MCP |
|------|---------|---------|
| **配置者** | 管理员 | 普通用户 |
| **使用者** | 项目内所有用户 | 仅创建者自己 |
| **运行位置** | 本地服务器 | 本地服务器 |
| **对外服务** | ❌ 否 | ❌ 否 |
| **并发场景** | 多用户同时使用 | 单用户多任务并发 |
| **并发限制** | 每用户 10 | 每用户 100 |

#### MCP 与 LLM 的连接方式

```
不是：每次工具调用重新连接 MCP
而是：任务开始时建立长连接 → 工具持有 session 引用 → LLM 通过引用调用
```

#### 智能体配置 MCP 工具

```
MCP 长连接建立 → 返回所有工具 [tool_a, tool_b, tool_c]
    ↓
TradingAgents 模块过滤
    ├── 读取智能体配置 enabled_mcp_servers: ["mcp_x"]
    └── 只保留 mcp_x 提供的工具 [tool_a, tool_c]
    ↓
传给 LLM
```

---

**文档结束**
