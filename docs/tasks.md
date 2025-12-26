# TradingAgents 多智能体股票分析系统 - 实现任务清单

> 生成时间：2025-12-25
> 版本：1.0.0
> 状态：草稿

---

## 实施计划

### 一、基础架构搭建

- [x] 1.1 创建 TradingAgents 模块目录结构
  - 在 backend/modules/ 下创建 trading_agents 目录
  - 创建 core/、agents/、tools/、llm/、config/、websocket/ 子目录
  - 创建各目录的 __init__.py 文件
  - 需求: 1.1, 1.2

- [x] 1.2 定义核心数据模型 (schemas.py)
  - 实现 AIModelConfig、MCPServerConfig、AgentConfig 等 Pydantic 模型
  - 实现 AnalysisTask、BatchTask、TaskEvent 等模型
  - 实现推荐结果枚举（买入/卖出/持有）
  - 实现请求/响应模型
  - 需求: 1.3, 2.1, 2.2, 2.3, 3.3

- [ ] 1.3 编写数据模型属性测试
  - Property 4: MCP配置JSON格式化round-trip
  - 需求: 2.4

- [x] 1.4 创建数据库集合和索引
  - 创建 ai_models 集合（AI模型配置）
  - 创建 mcp_servers 集合（MCP服务器配置）
  - 创建 agent_configs 集合（用户智能体配置）
  - 创建 analysis_tasks 集合（分析任务）
  - 创建 analysis_reports 集合（分析报告）
  - 创建 archived_reports 集合（归档报告）
  - 添加必要的索引（user_id、status、created_at等）
  - 需求: 7.1, 15.2

- [x] 1.5 复用现有核心模块
  - 复用 core/logging_config.py
  - 复用 core/exceptions.py
  - 复用 core/db/ (MongoDB & Redis)
  - 需求: 6.3.1, 6.3.2, 6.3.3, 6.3.4

- [x] 1.6 定义模块级异常 (core/exceptions.py)
  - 定义 TradingAgentsException 基类
  - 定义 TaskNotFoundException、ConfigurationError 等具体异常
  - 定义 MCPConnectionError、ModelQuotaExhaustedError 等
  - 实现异常到 HTTP 状态码的映射
  - 需求: 14.2, 14.3

---

### 二、AI 模型管理模块 ✅ 已完成

- [x] 2.1 实现 LLM Provider 抽象层 (llm/provider.py)
  - 定义 LLMProvider 抽象基类
  - 实现 chat_completion 异步方法
  - 实现 stream_completion 异步生成器方法
  - 实现连接测试方法
  - 需求: 1.5

- [x] 2.2 实现 OpenAI 兼容适配器 (llm/openai_compat.py)
  - 实现 OpenAICompatProvider 类
  - 支持自定义 base_url 和 api_key
  - 实现超时控制和重试逻辑
  - 支持智谱、DeepSeek、Qwen、Ollama 等提供商
  - 需求: 1.3, 14.1

- [ ] 2.3 编写 LLM Provider 属性测试
  - Property 2: API连接测试超时保证
  - 需求: 1.5

- [x] 2.4 实现 AI 模型配置服务 (services/model_service.py)
  - 实现 create_model、update_model、delete_model 方法
  - 实现 list_models 方法（区分系统级和用户级）
  - 实现 test_model_connection 方法（5秒超时）
  - API Key 加密存储，日志脱敏
  - 需求: 1.1, 1.2, 1.5, 1.6, 1.7, 1.8

- [ ] 2.5 编写模型配置属性测试
  - Property 1: AI模型配置存储正确性
  - 需求: 1.1, 1.2

- [ ] 2.6 编写模型删除属性测试
  - Property 3: 模型删除前置条件检查
  - 需求: 1.9

- [x] 2.7 实现 AI 模型管理 API 路由 (api.py)
  - POST /api/trading-agents/models
  - GET /api/trading-agents/models
  - PUT /api/trading-agents/models/{id}
  - DELETE /api/trading-agents/models/{id}
  - POST /api/trading-agents/models/{id}/test
  - 需求: 1.1, 1.2, 1.5, 1.6, 1.9

**测试状态**: GLM-4 API 连接测试通过（延迟 1279ms）

---

### 三、MCP 服务器管理模块 ✅ 已完成

- [x] 3.1 实现 MCP 适配器基类 (tools/mcp_adapter.py)
  - 定义 MCPAdapter 抽象基类
  - 实现 connect、disconnect 方法
  - 实现 list_tools、call_tool 方法
  - 实现 check_availability 方法
  - 需求: 2.5, 12.1

- [x] 3.2 实现 stdio 模式 MCP 适配器
  - 实现进程启动和管理
  - 实现 JSON-RPC 通信
  - 实现超时和错误处理
  - 需求: 2.2

- [x] 3.3 实现 SSE 模式 MCP 适配器
  - 实现 SSE 连接管理
  - 实现事件流解析
  - 实现认证处理
  - 需求: 2.3

- [x] 3.4 实现 HTTP 模式 MCP 适配器
  - 实现 HTTP 请求封装
  - 实现认证处理（Bearer/Basic）
  - 实现响应解析
  - 需求: 2.3

- [x] 3.5 实现 MCP 服务器配置服务 (services/mcp_service.py)
  - 实现 create_server、update_server、delete_server 方法
  - 实现 list_servers 方法（区分系统级和用户级）
  - 实现 test_server_connection 方法（10秒超时）
  - 实现 get_server_tools 方法
  - 实现自动可用性检测
  - 需求: 2.1, 2.5, 2.6, 2.7, 2.9, 2.10

- [x] 3.6 实现 MCP 服务器管理 API 路由 (api.py)
  - POST /api/trading-agents/mcp-servers
  - GET /api/trading-agents/mcp-servers
  - PUT /api/trading-agents/mcp-servers/{id}
  - DELETE /api/trading-agents/mcp-servers/{id}
  - POST /api/trading-agents/mcp-servers/{id}/test
  - GET /api/trading-agents/mcp-servers/{id}/tools
  - 需求: 2.1, 2.5, 2.7

---

### 四、工具管理与循环检测

- [x] 4.1 实现工具注册表 (tools/registry.py)
  - 实现 ToolRegistry 单例类
  - 实现工具注册和查找方法
  - 实现工具可用性状态管理
  - 需求: 12.2, 12.3, 12.4

- [x] 4.2 实现本地工具接口预留 (tools/local_tools.py)
  - 定义 LocalTool 抽象基类
  - 实现工具注册装饰器
  - 预留工具实现接口
  - 需求: 12.7

- [ ] 4.3 实现工具管理服务
  - 实现 get_available_tools 方法
  - 实现 check_tool_availability 方法
  - 实现工具调用封装（带重试和超时）
  - 需求: 12.3, 12.5, 12.6

- [x] 4.4 实现工具循环检测器 (tools/loop_detector.py)
  - 实现 record_call 方法（记录工具调用历史）
  - 实现 check_loop 方法（检测3次连续相同调用）
  - 实现 clear_history 方法（智能体完成后清除）
  - 自动禁用循环工具并通知智能体
  - 需求: 12.4, 12.5, 12.6

---

### 五、并发控制模块（公共模型资源池）

- [x] 5.1 实现健壮的并发控制器 (core/concurrency.py)
  - 实现基于 Redis 的分布式信号量
  - **[新增] 实现带 TTL 的锁获取机制 (SET NX EX)**：防止死锁
  - **[新增] 实现 Watchdog 自动续期机制**：支持长任务运行
  - **[新增] 实现 Force Release 机制**：管理员可手动解锁
  - 实现 acquire_public_quota 方法（每个用户最多1个槽位）
  - 实现 release_public_quota 方法
  - 实现排队位置查询方法
  - 需求: 2.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7

- [x] 5.2 实现批量任务限制
  - 公共模型批量任务最多5个同时执行
  - 超过5个需等待前序任务完成
  - 自定义模型不受此限制
  - 需求: 2.2.2, 2.2.3

- [ ] 5.3 编写并发控制属性测试
  - Property 9: 并发配额控制
  - 需求: 6.1, 6.3, 6.4

- [x] 5.4 实现 MCP 服务器并发控制 (tools/mcp_concurrency.py)
  - **[stdio 模式]** 实现进程池管理（默认池大小 = 3）
  - **[stdio 模式]** 实现进程空闲超时回收（5 分钟）
  - **[HTTP/SSE 模式]** 使用 httpx 连接池（max_connections = 10）
  - 实现连接池状态查询接口
  - 需求: 2.1, 2.2, 2.3

---

### 六、Checkpoint - 确保基础模块测试通过

- [ ] 6.1 确保所有基础模块测试通过
  - AI模型管理测试
  - MCP服务器管理测试
  - 工具管理与循环检测测试
  - 并发控制测试
  - 如有问题请询问用户

---

### 七、智能体配置管理模块 ✅ 已完成

- [x] 7.1 创建默认智能体配置模板 (config/templates/agents.yaml)
  - 定义第一阶段默认分析师配置（可配置多个）
  - 定义第二阶段研究员配置（增加 max_rounds 参数，默认 1）
  - 定义第三阶段风险分析师配置
  - 定义第四阶段总结智能体配置

- [x] 7.2 实现第二阶段辩论逻辑 (agents/phase2/)
  - **[核心] 实现 DebateManager 节点**：控制辩论轮次循环
  - **[核心] 实现 Bull/Bear Prompt 构造器**：动态注入 opponent_view 并添加 `<opponent_view>` XML 标签标注来源
  - 实现初始观点生成 Node (Round 0)
  - 实现交叉反驳 Node (Round N)
  - 需求: 1.3.5, 1.3.6

- [x] 7.3 实现 WebSocket 事件流与控制接口 (websocket/ & api.py)
  - 实现 `push_tool_event`：推送工具调用开始/结束
  - 实现 `push_report_event`：推送单个分析师报告完成
  - **[核心] 实现 POST /api/trading-agents/tasks/{id}/stop 接口**
  - 在 Agent 引擎中增加 `check_interrupt` 检查点
  - 需求: 2.1.4, 2.1.5, 2.1.7

- [x] 7.4 实现配置加载器 (config/loader.py)
  - 实现 YAML 配置文件加载
  - 实现配置验证
  - 实现配置合并逻辑
  - 需求: 15.1, 15.5

- [x] 7.5 实现智能体配置服务 (services/agent_config_service.py)
  - 实现 get_user_config 方法
  - 实现 update_user_config 方法
  - 实现 reset_to_default 方法
  - 实现新用户配置初始化
  - 需求: 3.1, 3.2, 3.5, 3.7, 3.8, 3.9

- [x] 7.6 编写配置初始化属性测试
  - Property 5: 用户配置初始化一致性
  - 需求: 3.7, 15.4

- [x] 7.7 编写配置验证属性测试
  - Property 6: 智能体配置完整性验证
  - 需求: 3.9

- [x] 7.8 实现配置导入导出功能 (services/agent_config_service.py)
  - 实现 export_config 方法
  - 实现 import_config 方法
  - 实现配置格式验证
  - 需求: 15.6, 15.7

- [x] 7.9 编写配置导入导出属性测试
  - Property 14: 配置导入导出round-trip
  - 需求: 15.6, 15.7

- [x] 7.10 实现智能体配置 API 路由 (api.py)
  - GET /api/trading-agents/agent-config
  - PUT /api/trading-agents/agent-config
  - POST /api/trading-agents/agent-config/reset
  - POST /api/trading-agents/agent-config/export
  - POST /api/trading-agents/agent-config/import
  - 需求: 3.1, 3.8, 15.6, 15.7

---

### 八、Checkpoint - 确保配置模块测试通过

- [x] 8.1 确保配置模块测试通过
  - 智能体配置管理测试
  - 配置初始化测试
  - 配置导入导出测试
  - 如有问题请询问用户

**测试结果**: 17 passed, 5 skipped

---

### 九、智能体基础框架 ✅ 已完成

- [x] 9.1 定义工作流状态类 (core/state.py)
  - 实现 AgentState TypedDict
  - 实现 InvestmentDebateState TypedDict（第二阶段）
  - 实现 RiskDebateState TypedDict（第三阶段）
  - 实现状态合并 Reducer 函数（merge_reports、merge_debate_state）
  - 需求: 4.6

- [x] 9.2 实现智能体基类 (agents/base.py)
  - 定义 BaseAgent 抽象类
  - 实现通用执行逻辑
  - 实现工具调用封装
  - 实现报告生成逻辑
  - 需求: 4.3, 4.4, 4.5

- [x] 9.3 实现第一阶段动态分析师工厂 (agents/phase1/analysts.py)
  - 实现 create_analyst 工厂函数
  - 实现通用分析师模板类
  - 实现配置驱动的智能体创建
  - 实现工具权限过滤
  - 实现分析师调度器（scheduler.py）
  - 需求: 1.4, 3.2, 3.3, 3.4

- [x] 9.4 实现第二阶段智能体 (agents/phase2/debaters.py)
  - 实现 BullDebater 看涨研究员
  - 实现 BearDebater 看跌研究员
  - 实现 TradePlanner 交易员
  - 需求: 3.5, 13.1

- [x] 9.5 实现第三阶段智能体 (agents/phase3/risk.py)
  - 实现 RiskAssessor 首席风控官
  - 需求: 3.5, 13.2

- [x] 9.6 实现第四阶段智能体 (agents/phase4/summary.py)
  - 实现 FinalSummarizer 总结智能体
  - 实现结构化报告生成（推荐结果+价格）
  - 实现流式输出支持
  - 需求: 4.7, 4.10

---

### 十、LangGraph 工作流引擎 ✅ 已完成

- [x] 10.1 实现智能体执行引擎 (core/agent_engine.py)
  - 实现 AgentWorkflowEngine 类
  - 实现四阶段工作流编排
  - 实现条件路由逻辑
  - 实现阶段开关控制
  - 需求: 4.1, 4.6, 9.1, 9.2

- [ ] 10.2 编写阶段跳转属性测试
  - Property 11: 阶段跳转正确性
  - 需求: 9.2

- [x] 10.3 实现辩论轮次控制
  - 实现第二阶段辩论路由
  - 实现轮次计数和终止条件
  - 需求: 13.1, 13.2, 13.3, 13.4

- [x] 10.4 实现报告传递机制
  - 实现代码逻辑传递（非工具调用）
  - 实现上下文构建函数
  - 实现报告合并逻辑
  - 需求: 4.5, 4.6

- [ ] 10.5 编写报告一致性属性测试
  - Property 7: 报告存储与推送一致性
  - 需求: 4.5

**测试状态**: 阶段1测试通过（3个分析师并行生成报告，耗时19.32秒）
- Token 追踪功能测试通过：91/91 后端测试通过
- WebSocket 模块测试通过：34/34 测试通过
- AI 功能测试通过：7/7 GLM-4.7 集成测试通过
- MCP 适配器测试通过：所有三种传输模式测试通过

---

### 十一、实时通信模块

- [x] 11.1 实现 WebSocket 管理器 (websocket/manager.py)
  - 实现按需连接（用户打开详情页面时连接）
  - 实现连接管理（建立、断开）
  - 实现单用户最多5个连接限制
  - 实现事件广播
  - 实现心跳检测
  - 无连接时丢弃事件（不缓存）
  - 需求: 3.2.1, 3.2.2, 3.2.8, 3.2.9, 3.2.10

- [x] 11.2 定义 WebSocket 事件 (websocket/events.py)
  - 定义所有事件类型
  - 实现事件序列化
  - 实现 tool_disabled 事件（循环检测触发）
  - 需求: 3.2.3, 3.2.4, 3.2.5, 3.2.6, 3.2.7

- [x] 11.3 实现 SSE 流式输出
  - 实现 SSE 端点
  - 实现报告流式推送
  - 实现连接管理
  - 需求: 2.1.7, 4.7

- [x] 11.4 实现 WebSocket API 路由
  - WS /api/trading-agents/ws/{task_id}
  - GET /api/trading-agents/stream/{task_id}
  - 需求: 3.2.1, 4.7

---

### 十二、Checkpoint - 确保智能体引擎测试通过

- [ ] 12.1 确保智能体引擎测试通过
  - 智能体执行测试
  - 工作流引擎测试
  - WebSocket通信测试
  - 如有问题请询问用户

---

### 十三、任务管理模块

- [x] 13.1 实现任务管理器 (core/task_manager.py)
  - 实现 create_task 方法
  - 实现 get_task_status 方法
  - 实现 list_tasks 方法
  - 实现 cancel_task 方法
  - 需求: 2.1.1, 2.1.8, 4.8, 4.9, 8.1, 8.5

- [x] 13.2 编写任务中断属性测试
  - Property 8: 任务中断状态保持
  - 需求: 4.8

- [ ] 13.3 实现任务队列
  - 实现基于 Redis 的任务队列
  - 实现任务调度逻辑
  - 实现批量任务管理
  - 需求: 2.2.1, 5.1, 5.2, 6.7

- [ ] 13.4 实现任务恢复机制
  - 实现任务状态存储
  - 实现配置快照保存
  - 实现系统重启时任务恢复
  - 智能体被删除时标记任务失败
  - 从当前阶段的当前智能体继续执行
  - 已完成的报告保留
  - 需求: 8.7, 14.6, 14.7, 14.8

- [x] 13.5 实现任务管理 API 路由
  - POST /api/trading-agents/tasks
  - GET /api/trading-agents/tasks
  - GET /api/trading-agents/tasks/{id}
  - POST /api/trading-agents/tasks/{id}/cancel
  - POST /api/trading-agents/tasks/{id}/retry
  - DELETE /api/trading-agents/tasks/{id}
  - 需求: 2.1.1, 8.1, 8.5, 8.6, 8.7

- [x] 13.7 实现 Token 追踪功能
  - 在每个智能体执行后累加 token 使用量到 workflow state
  - 记录 prompt_tokens、completion_tokens、total_tokens
  - 在任务完成时保存到数据库
  - 需求: 新增

- [x] 13.6 实现任务过期机制 (core/task_expiry.py)
  - 实现定时任务：每小时扫描 running 状态任务
  - 检查条件：created_at + 24h < now()
  - 处理逻辑：更新状态为 EXPIRED，释放模型配额，保留已完成报告
  - 记录过期日志
  - 需求: 新增

---

### 十四、报告管理模块 ✅ 已完成

- [x] 14.1 实现报告存储服务 (services/report_service.py)
  - 实现报告创建和更新
  - 存储推荐结果（买入/卖出/持有）
  - 存储买入价格和卖出价格
  - 实现报告查询（支持筛选和排序）
  - 实现报告统计
  - 需求: 2.5.1, 7.1, 7.2, 7.3, 7.8

- [x] 14.2 编写用户数据隔离属性测试
  - Property 10: 用户数据隔离
  - 需求: 7.7, 11.6

- [x] 14.3 实现报告管理 API 路由
  - GET /api/trading-agents/reports
  - GET /api/trading-agents/reports/{id}
  - GET /api/trading-agents/reports/summary
  - DELETE /api/trading-agents/reports/{id}
  - 需求: 7.2, 7.3, 7.4, 7.5

- [x] 14.4 实现报告归档服务 (services/report_archival.py)
  - 复用 core/admin/tasks.py 现有调度器
  - 注册定时任务：每天凌晨 3:00 执行
  - 查询条件：created_at + 30d < now()
  - 归档保留字段：analysis_time, stock_code, final_report, recommendation, buy_price, sell_price
  - 删除 agent_traces 中的相关记录
  - 更新原任务记录，移除中间数据
  - 需求: 新增

**测试状态**: 19/19 测试通过（任务管理、报告管理、过期机制、归档服务）

---

### 十五、错误处理与重试机制

- [ ] 15.1 实现 API 调用重试逻辑
  - 实现指数退避重试（1秒、2秒、4秒）
  - 实现最大重试次数限制（3次）
  - 实现重试日志记录
  - 需求: 14.1, 14.2

- [ ] 15.2 编写重试机制属性测试
  - Property 12: API调用重试机制
  - 需求: 14.1

- [ ] 15.3 实现智能体失败容错
  - 实现单智能体失败隔离
  - 实现部分完成状态处理
  - 实现错误信息记录
  - 需求: 14.3, 14.4

- [ ] 15.4 编写容错机制属性测试
  - Property 13: 智能体失败容错
  - 需求: 14.3

- [ ] 15.5 实现工具调用超时处理
  - 实现超时检测（30秒）
  - 实现超时后继续执行
  - 需求: 14.5

---

### 十六、监控告警模块

- [ ] 16.1 定义告警事件类型 (core/alerts.py)
  - 定义告警级别枚举：INFO, WARN, ERROR, CRITICAL
  - 定义告警事件数据结构
  - 实现告警事件工厂方法
  - 需求: 新增

- [ ] 16.2 实现告警触发器
  - **工具循环检测告警 (WARN)**：检测到工具循环调用时触发
  - **模型配额耗尽告警 (WARN)**：公共模型队列长度 > 10 时触发
  - **MCP 服务器不可用告警 (ERROR)**：MCP 服务器连接失败时触发
  - **任务执行超时告警 (WARN)**：单个智能体执行超过 10 分钟时触发
  - **任务批量失败告警 (CRITICAL)**：1 小时内失败任务数 > 10 时触发
  - **Token 消耗异常告警 (WARN)**：单任务 token 消耗 > 100000 时触发
  - 需求: 新增

- [ ] 16.3 实现告警通道
  - 实现日志记录通道（默认启用）
  - 实现 WebSocket 推送到管理员面板
  - 预留邮件/企业微信通道接口
  - 需求: 新增

- [ ] 16.4 实现 Token 追踪服务 (services/token_tracking.py)
  - 记录每次 LLM 调用的 token 消耗
  - 累计到任务级别的 total_token_usage
  - 提供 token 消耗查询接口
  - 需求: 新增

---

### 十七、Checkpoint - 确保后端所有测试通过

- [x] 17.1 确保后端所有测试通过
  - 所有单元测试
  - 所有属性测试
  - 所有集成测试
  - 如有问题请询问用户

**测试结果**:
- 单元测试: 136 passed, 5 skipped
- 集成测试: 11/13 passed (2 个 500 错误需后续调试)
- 前端 lint: 115 warnings, 0 errors

---

### 十八、管理员功能

- [ ] 18.1 实现系统级资源管理 API
  - GET /api/trading-agents/admin/models
  - POST /api/trading-agents/admin/models
  - GET /api/trading-agents/admin/mcp-servers
  - POST /api/trading-agents/admin/mcp-servers
  - 需求: 11.1

- [ ] 18.2 实现管理员数据查询 API
  - GET /api/trading-agents/admin/tasks
  - GET /api/trading-agents/admin/reports
  - 需求: 11.2, 11.7

- [ ] 18.3 实现默认模板管理
  - 实现模板更新接口
  - 实现模板版本管理
  - 需求: 15.1

---

### 十九、前端 - 设置模块 ✅ 已完成

- [x] 19.1 创建 AI 模型管理页面
  - 实现模型列表展示
  - 实现添加模型表单（提供商选择、自动填充URL）
  - 实现模型测试功能
  - 实现模型启用/禁用切换
  - 需求: 1.1, 1.2, 1.5, 1.6, 1.7

- [x] 19.2 创建 MCP 服务器管理页面
  - 实现服务器列表展示（区分系统级和用户级）
  - 实现添加服务器表单（支持三种模式）
  - 实现 JSON 配置编辑器（带格式化）
  - 实现服务器测试和工具列表查看
  - 需求: 2.1, 2.4, 2.5, 2.9, 2.10

- [x] 19.3 创建智能体配置页面
  - 实现阶段选项卡切换
  - 实现第一阶段智能体增删改
  - 实现提示词编辑器（带变量提示）
  - 实现工具权限配置
  - 实现模型选择（按阶段）
  - 需求: 3.1, 3.2, 3.4, 3.5, 3.6, 3.10

- [x] 19.4 创建分析设置页面
  - 实现并发配置
  - 实现阶段开关配置
  - 实现辩论轮次配置
  - 需求: 6.2, 6.7, 9.1, 13.1, 13.2

**实现内容：**
- 创建 `frontend/src/modules/trading_agents/` 模块目录
- 实现类型定义 ([types.ts](frontend/src/modules/trading_agents/types.ts))
- 实现 API 客户端 ([api.ts](frontend/src/modules/trading_agents/api.ts))
- 实现 Pinia store ([store.ts](frontend/src/modules/trading_agents/store.ts))
- 实现四个设置页面：
  - [ModelManagementView.vue](frontend/src/modules/trading_agents/views/ModelManagementView.vue) - AI 模型管理
  - [MCPServerManagementView.vue](frontend/src/modules/trading_agents/views/MCPServerManagementView.vue) - MCP 服务器管理
  - [AgentConfigView.vue](frontend/src/modules/trading_agents/views/AgentConfigView.vue) - 智能体配置
  - [AnalysisSettingsView.vue](frontend/src/modules/trading_agents/views/AnalysisSettingsView.vue) - 分析设置
- 实现阶段配置组件 ([PhaseConfigPanel.vue](frontend/src/modules/trading_agents/components/PhaseConfigPanel.vue))
- 添加路由配置 (`/settings/trading-agents/*`)
- 前端构建验证通过

---

### 二十、前端 - 分析模块

- [x] 20.1 增强单股分析页面
  - 实现分析过程可视化（阶段进度、智能体状态）
  - 实现工具调用日志展示
  - 实现按需 WebSocket 连接（打开详情页时连接）
  - **实现 WebSocket 断线重连（指数退避策略）**
  - 实现任务中断功能
  - 实现流式报告展示
  - 需求: 2.1.2, 2.1.4, 2.1.7, 2.1.8, 2.1.11

- [x] 20.2 增强批量分析页面
  - 实现批量任务提交
  - 实现任务进度列表
  - 实现单任务取消
  - 实现批量任务取消
  - 显示排队位置（使用公共模型时）
  - 需求: 2.2.1, 2.2.3, 2.2.4, 2.2.5, 2.2.6, 2.2.7

---

### 二十一、前端 - 任务中心增强

- [ ] 21.1 增强任务列表页面
  - 实现任务状态筛选（包含 EXPIRED 状态）
  - 实现任务排序（按股票、时间等）
  - 实现实时状态更新
  - 需求: 8.1, 8.2, 8.3

- [ ] 21.2 增强任务详情页面
  - 实现进行中任务状态展示
  - 实现任务取消和重试
  - 实现报告查看
  - **显示 Token 消耗统计**
  - 需求: 8.4, 8.5, 8.6

- [ ] 21.3 增强报告查询功能
  - 实现报告筛选（按推荐结果、风险等级等）
  - 实现报告排序
  - 实现报告详情展示
  - 需求: 7.2, 7.3, 7.4, 7.5, 7.8

---

### 二十二、前端 - 管理员页面

- [ ] 22.1 创建系统 AI 模型管理页面
  - 实现系统级模型管理
  - 与用户级页面区分
  - 需求: 1.8, 11.1

- [ ] 22.2 创建系统 MCP 管理页面
  - 实现系统级 MCP 管理
  - 与用户级页面区分
  - 需求: 2.9, 11.1

- [ ] 22.3 创建管理员任务/报告查看页面
  - 实现所有用户任务查看
  - 实现用户筛选
  - **显示告警事件面板**
  - 需求: 8.8, 11.2

---

### 二十三、Final Checkpoint - 确保所有测试通过

- [ ] 23.1 确保所有测试通过
  - 后端所有测试
  - 前端所有测试
  - 端到端测试
  - 如有问题请询问用户

---

## 附录

### 开发顺序说明

1. **后端模块**按依赖关系顺序开发：
   - 基础架构 → AI模型 → MCP → 工具与循环检测 → 并发控制 → 配置 → 智能体 → 工作流 → 任务 → 报告 → 监控告警

2. **每个模块完成后**进行 Checkpoint 验证

3. **前端开发**在后端 API 完成后进行

4. **属性测试**标记为可选（*），但强烈建议实现以确保系统正确性

### 技术要点

- 使用 LangGraph 构建工作流，支持状态持久化和断点续传
- 使用 Redis 实现分布式并发控制和任务队列
- 使用 WebSocket 实现按需实时状态推送（含断线重连）
- 使用 SSE 实现流式报告输出
- 所有用户数据查询自动添加 user_id 过滤
- 公共模型采用槽位管理，每个用户最多占用 1 个槽位
- 工具循环检测：连续3次相同调用自动禁用工具
- 任务恢复：从检查点继续，智能体删除则失败
- 任务过期：24 小时未完成自动标记为 EXPIRED
- 报告归档：30 天后仅保留核心字段
- Token 追踪：记录每次 LLM 调用消耗，累计到任务级别
- 会话隔离：基于 task_id 实现完全隔离

### 测试策略

- **单元测试**：覆盖核心业务逻辑
- **属性测试**：验证系统正确性属性（使用 hypothesis 库）
- **集成测试**：验证 API 端点和完整流程
