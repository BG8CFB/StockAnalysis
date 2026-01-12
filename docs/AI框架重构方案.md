# AI 框架重构方案 - LangChain 统一架构

> 文档版本: v4.0
> 创建日期: 2026-01-12
> 状态: 实施中

---

## 一、背景与目标

### 1.1 现状分析

当前项目 AI 框架基于自定义 OpenAI 兼容层，已实现基础的思考能力支持。经过评估，决定**全面采用 LangChain 框架**作为统一的 AI 调用层。

**选择 LangChain 的理由**：
1. **广泛的模型支持** - 通过 OpenAI 兼容接口支持智谱、DeepSeek、千问、Claude 等所有主流模型
2. **丰富的生态** - 内置 Agent、工具调用、记忆管理等高级功能
3. **成熟稳定** - 行业标准框架，社区活跃
4. **简化维护** - 无需为每个模型单独适配

### 1.2 重构目标

1. **统一网关架构** - 基于 LangChain 的统一 AI 调用接口
2. **GLM-4.7 思考能力支持** - 通过 model_kwargs 传递 thinking 参数
3. **流式输出支持** - 实时传输，前端逐字显示
4. **并发控制** - 在 AI 模块内实现用户级和系统级并发限制
5. **简洁的目录结构** - 按业务逻辑组织代码

### 1.3 技术选型

| 组件 | 技术选择 | 说明 |
|------|----------|------|
| **核心框架** | LangChain | 统一 AI 调用层 |
| **ChatModel** | langchain-openai (ChatOpenAI) | 支持 OpenAI 兼容接口 |
| **流式输出** | LangChain astream | 原生异步流式支持 |
| **并发控制** | asyncio.Semaphore | 异步信号量实现 |
| **配置管理** | Pydantic Settings | 类型安全的配置 |

---

## 二、架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            业务调用层                                   │
│  (TradingAgents、AskStock、未来其他模块...)                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI 统一网关层                                     │
│                        core/ai/                                         │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    AIService (统一服务)                           │  │
│  │                                                                  │  │
│  │  - chat_completion()    聊天补全                                  │  │
│  │  - stream_completion()   流式输出                                  │  │
│  │  - create_agent()        创建智能体                                │  │
│  │  - validate_connection() 连接验证                                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                  ConcurrencyManager (并发管理)                    │  │
│  │                                                                  │  │
│  │  - 用户级并发限制                                                 │  │
│  │  - 系统级并发限制                                                 │  │
│  │  - 请求队列管理                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        LangChain 适配层                                  │
│                        core/ai/langchain/                               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                  LangChainAdapter                                │  │
│  │                                                                  │  │
│  │  - create_chat_model()  创建 ChatModel                            │  │
│  │  - adapt_thinking_params()  适配思考参数                          │  │
│  │  - format_messages()  格式化消息                                  │  │
│  │  - bind_tools()  绑定工具                                         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        LangChain 框架                                    │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  ChatOpenAI  │  │    Agent     │  │   Tools      │                  │
│  │              │  │   Framework  │  │              │                  │
│  │ - 智谱 GLM   │  │              │  │ - MCP Tools  │                  │
│  │ - Claude     │  │              │  │ - Custom     │                  │
│  │ - DeepSeek   │  │              │  │              │                  │
│  │ - Qwen       │  │              │  │              │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构设计

```
backend/core/ai/
├── __init__.py                     # 模块入口
├── api.py                          # AI 模型管理 API 路由
├── exceptions.py                   # 异常定义
│
├── service.py                      # AI 统一服务（新增）
│   ├── AIService                   # 主要服务类
│   ├── ConcurrencyManager          # 并发管理器
│   └── ConnectionManager           # 连接管理器
│
├── langchain/                      # LangChain 适配层（新增）
│   ├── __init__.py
│   ├── adapter.py                  # LangChain 适配器
│   ├── models.py                   # 模型创建
│   ├── thinking.py                 # 思考能力适配
│   ├── tools.py                    # 工具绑定
│   └── streaming.py                # 流式输出处理
│
├── model/                          # 模型配置管理
│   ├── __init__.py
│   ├── service.py                  # 模型配置服务
│   └── schemas.py                  # 模型配置 Schema
│
└── config/                         # 配置
    └── defaults.py                 # 默认配置
```

---

## 三、核心组件设计

### 3.1 统一数据结构

```python
# core/ai/types.py (新增)

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncIterator

@dataclass
class AIMessage:
    """统一消息格式"""
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    def to_langchain(self):
        """转换为 LangChain 消息格式"""
        from langchain_core.messages import (
            SystemMessage, HumanMessage, AIMessage, ToolMessage
        )
        if self.role == "system":
            return SystemMessage(content=self.content)
        elif self.role == "user":
            return HumanMessage(content=self.content)
        elif self.role == "assistant":
            return AIMessage(content=self.content)
        elif self.role == "tool":
            return ToolMessage(
                content=self.content,
                tool_call_id=self.tool_call_id or ""
            )

@dataclass
class AITool:
    """统一工具格式"""
    name: str
    description: str
    parameters: Dict[str, Any]

@dataclass
class AIResponse:
    """统一响应格式"""
    content: str
    reasoning_content: Optional[str] = None  # 思考内容
    thinking_tokens: Optional[int] = None    # 思考 token 数
    usage: Optional[Dict[str, int]] = None
    tool_calls: Optional[List[Dict]] = None
    raw_response: Optional[Dict] = None

@dataclass
class AIStreamChunk:
    """流式响应块"""
    content: str
    reasoning_content: Optional[str] = None
    is_complete: bool = False
```

### 3.2 LangChain 适配器

```python
# core/ai/langchain/adapter.py (新增)

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class LangChainAdapter:
    """LangChain 适配器

    负责创建和配置 LangChain ChatModel 实例。
    支持所有 OpenAI 兼容的模型。
    """

    # 默认 API 端点
    DEFAULT_BASE_URLS = {
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        "zhipu_coding": "https://open.bigmodel.cn/api/coding/paas/v4",
        "deepseek": "https://api.deepseek.com",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "moonshot": "https://api.moonshot.cn/v1",
    }

    @classmethod
    def create_chat_model(
        cls,
        model_id: str,
        api_key: str,
        platform: str,
        api_base_url: Optional[str] = None,
        temperature: float = 0.5,
        timeout_seconds: int = 60,
        thinking_enabled: bool = False,
        thinking_mode: Optional[str] = None,
        **kwargs
    ) -> ChatOpenAI:
        """
        创建 LangChain ChatModel 实例

        Args:
            model_id: 模型 ID (如 glm-4.7)
            api_key: API 密钥
            platform: 平台名称 (zhipu, openai, etc.)
            api_base_url: 自定义 API 端点
            temperature: 温度参数
            timeout_seconds: 超时时间
            thinking_enabled: 是否启用思考能力
            thinking_mode: 思考模式 (preserved/clear_on_new)
            **kwargs: 其他参数

        Returns:
            ChatOpenAI 实例
        """
        # 确定 API 端点
        base_url = api_base_url or cls.DEFAULT_BASE_URLS.get(platform)

        # 构建模型参数
        model_kwargs = {}

        # 添加思考参数（GLM-4.7）
        if thinking_enabled and "glm-4.7" in model_id.lower():
            clear_thinking = thinking_mode == "clear_on_new"
            model_kwargs["thinking"] = {
                "type": "enabled",
                "clear_thinking": clear_thinking,
            }
            logger.debug(f"GLM-4.7 思考模式: clear_thinking={clear_thinking}")

        # 创建 ChatOpenAI 实例
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            timeout=timeout_seconds,
            model_kwargs=model_kwargs if model_kwargs else None,
            **kwargs
        )
```

### 3.3 AI 统一服务

```python
# core/ai/service.py (新增)

import logging
from typing import List, Optional, AsyncIterator, Dict, Any
from langchain_core.language_model import BaseChatModel

from .types import AIMessage, AIResponse, AIStreamChunk, AITool
from .langchain.adapter import LangChainAdapter
from .model.service import AIModelConfigService
from .concurrency import ConcurrencyManager

logger = logging.getLogger(__name__)

class AIService:
    """AI 统一服务

    提供统一的 AI 调用接口，内部使用 LangChain 实现。
    """

    def __init__(self):
        self.config_service = AIModelConfigService()
        self.concurrency_manager = ConcurrencyManager()
        self._model_cache: Dict[str, BaseChatModel] = {}

    async def chat_completion(
        self,
        user_id: str,
        messages: List[AIMessage],
        model_id: Optional[str] = None,
        tools: Optional[List[AITool]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """
        聊天补全

        Args:
            user_id: 用户 ID
            messages: 消息列表
            model_id: 模型 ID（可选，从配置获取）
            tools: 工具列表（可选）
            temperature: 温度参数（可选）
            max_tokens: 最大 token 数（可选）
            **kwargs: 其他参数

        Returns:
            AIResponse 响应对象
        """
        # 获取模型配置
        config = await self._get_model_config(user_id, model_id)

        # 获取并发令牌
        async with self.concurrency_manager.acquire(config, user_id):
            # 创建或获取 ChatModel
            chat_model = await self._get_or_create_model(config)

            # 转换消息格式
            lc_messages = [msg.to_langchain() for msg in messages]

            # 构建调用参数
            invoke_kwargs = {"messages": lc_messages}

            # 添加工具（如果有）
            if tools:
                invoke_kwargs["tools"] = [
                    {"type": "function", "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }}
                    for tool in tools
                ]

            # 添加温度参数
            if temperature is not None:
                invoke_kwargs["temperature"] = temperature

            # 添加 max_tokens
            if max_tokens is not None:
                invoke_kwargs["max_tokens"] = max_tokens

            # 调用模型
            response = await chat_model.ainvoke(**invoke_kwargs)

            # 解析响应
            return self._parse_response(response, config)

    async def stream_completion(
        self,
        user_id: str,
        messages: List[AIMessage],
        model_id: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[AIStreamChunk]:
        """
        流式聊天补全

        Args:
            user_id: 用户 ID
            messages: 消息列表
            model_id: 模型 ID（可选）
            **kwargs: 其他参数

        Yields:
            AIStreamChunk 流式响应块
        """
        # 获取模型配置
        config = await self._get_model_config(user_id, model_id)

        # 获取并发令牌
        async with self.concurrency_manager.acquire(config, user_id):
            # 创建或获取 ChatModel
            chat_model = await self._get_or_create_model(config)

            # 转换消息格式
            lc_messages = [msg.to_langchain() for msg in messages]

            # 流式调用
            async for chunk in chat_model.astream(lc_messages):
                yield AIStreamChunk(
                    content=chunk.content or "",
                    is_complete=False,
                )

            # 发送完成标记
            yield AIStreamChunk(content="", is_complete=True)

    async def validate_connection(
        self,
        user_id: str,
        model_id: Optional[str] = None
    ) -> bool:
        """
        验证连接

        Args:
            user_id: 用户 ID
            model_id: 模型 ID（可选）

        Returns:
            连接是否成功
        """
        try:
            messages = [AIMessage(role="user", content="test")]
            await self.chat_completion(user_id, messages, model_id, max_tokens=1)
            return True
        except Exception as e:
            logger.warning(f"连接验证失败: {e}")
            return False

    async def _get_model_config(self, user_id: str, model_id: Optional[str]) -> Dict:
        """获取模型配置"""
        if model_id:
            config = await self.config_service.get_by_model_id(user_id, model_id)
            if config:
                return config

        # 获取用户默认配置
        config = await self.config_service.get_user_default(user_id)
        if config:
            return config

        # 获取系统默认配置
        return await self.config_service.get_system_default()

    async def _get_or_create_model(self, config: Dict) -> BaseChatModel:
        """获取或创建 ChatModel 实例"""
        cache_key = f"{config['platform']}:{config['model_id']}:{config.get('api_key', '')[:8]}"

        if cache_key not in self._model_cache:
            self._model_cache[cache_key] = LangChainAdapter.create_chat_model(
                model_id=config["model_id"],
                api_key=config.get("api_key", ""),
                platform=config["platform"],
                api_base_url=config.get("api_base_url"),
                temperature=config.get("temperature", 0.5),
                timeout_seconds=config.get("timeout_seconds", 60),
                thinking_enabled=config.get("thinking_enabled", False),
                thinking_mode=config.get("thinking_mode"),
            )

        return self._model_cache[cache_key]

    def _parse_response(self, response: Any, config: Dict) -> AIResponse:
        """解析 LangChain 响应"""
        # 获取内容
        content = response.content or ""

        # 解析思考内容（GLM-4.7）
        reasoning_content = None
        thinking_tokens = None

        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if "reasoning_content" in metadata:
                reasoning_content = metadata["reasoning_content"]

        # 解析工具调用
        tool_calls = None
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = [
                {
                    "id": tc.id or "",
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.args,
                    },
                }
                for tc in response.tool_calls
            ]

        # 解析 usage
        usage = None
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata

        return AIResponse(
            content=content,
            reasoning_content=reasoning_content,
            thinking_tokens=thinking_tokens,
            usage=usage,
            tool_calls=tool_calls,
            raw_response=getattr(response, "response_metadata", None),
        )


# 全局单例
_ai_service: Optional[AIService] = None

def get_ai_service() -> AIService:
    """获取 AI 服务单例"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
```

### 3.4 并发管理器

```python
# core/ai/concurrency.py (新增)

import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_user_concurrent: int = 3      # 每用户最大并发数
    max_system_concurrent: int = 50   # 系统总并发数
    queue_timeout: int = 30           # 队列超时（秒）

class ConcurrencyManager:
    """并发管理器

    控制用户级和系统级的并发请求数。
    """

    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        self.config = config or ConcurrencyConfig()
        self._user_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._system_semaphore = asyncio.Semaphore(self.config.max_system_concurrent)
        self._lock = asyncio.Lock()

    async def acquire(self, model_config: Dict, user_id: str):
        """获取并发令牌（上下文管理器）"""
        return await self._acquire_lock(user_id)

    async def _acquire_lock(self, user_id: str):
        """内部锁获取实现"""
        # 获取用户级信号量
        async with self._lock:
            if user_id not in self._user_semaphores:
                self._user_semaphores[user_id] = asyncio.Semaphore(
                    self.config.max_user_concurrent
                )
            user_sem = self._user_semaphores[user_id]

        # 同时获取用户级和系统级令牌
        acquired = False

        try:
            # 等待系统级令牌
            await asyncio.wait_for(
                self._system_semaphore.acquire(),
                timeout=self.config.queue_timeout
            )

            # 等待用户级令牌
            await asyncio.wait_for(
                user_sem.acquire(),
                timeout=self.config.queue_timeout
            )

            acquired = True
            logger.debug(f"并发令牌已获取: user={user_id}")

            # 返回一个上下文管理器
            class _LockContext:
                def __init__(self, user_sem, sys_sem, user_id, manager):
                    self.user_sem = user_sem
                    self.sys_sem = sys_sem
                    self.user_id = user_id
                    self.manager = manager

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    self.user_sem.release()
                    self.sys_sem.release()
                    logger.debug(f"并发令牌已释放: user={self.user_id}")

            return _LockContext(user_sem, self._system_semaphore, user_id, self)

        except asyncio.TimeoutError:
            if acquired:
                # 如果部分获取成功，需要释放
                user_sem.release()
            self._system_semaphore.release()
            raise PermissionError(f"并发请求过多，请稍后重试")

    def get_stats(self) -> Dict:
        """获取并发统计"""
        return {
            "system_available": self._system_semaphore._value,
            "user_count": len(self._user_semaphores),
        }
```

---

## 四、GLM-4.7 思考能力支持

### 4.1 思考参数格式

根据智谱文档，GLM-4.7 的思考能力通过以下参数启用：

```json
{
  "thinking": {
    "type": "enabled",
    "clear_thinking": false
  }
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `thinking.type` | string | 固定值 "enabled" |
| `thinking.clear_thinking` | boolean | false=保留式思考（长任务），true=清除式思考（批量任务） |

### 4.2 LangChain 集成

通过 LangChain 的 `model_kwargs` 参数传递：

```python
ChatOpenAI(
    model="glm-4.7",
    api_key="your-api-key",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    model_kwargs={
        "thinking": {
            "type": "enabled",
            "clear_thinking": False
        }
    }
)
```

### 4.3 编程 API 支持

用户提供的编程 API 端点：
- 标准 API: `https://open.bigmodel.cn/api/paas/v4`
- 编程 API: `https://open.bigmodel.cn/api/coding/paas/v4`

在模型配置中通过 `api_base_url` 指定。

---

## 五、流式输出支持

### 5.1 后端实现

```python
# API 路由示例
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口"""

    async def generate():
        ai_service = get_ai_service()
        async for chunk in ai_service.stream_completion(
            user_id=request.user_id,
            messages=request.messages,
            model_id=request.model_id,
        ):
            # SSE 格式输出
            yield f"data: {chunk.json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### 5.2 前端实现

```typescript
// 前端流式接收示例
async function streamChat(message: string) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    // 处理 SSE 格式: data: {...}\n\n
    const lines = chunk.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        // 实时更新 UI
        updateUI(data.content);
      }
    }
  }
}
```

---

## 六、配置 Schema 更新

### 6.1 模型配置扩展

```python
# core/ai/model/schemas.py (更新)

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum

class ThinkingMode(str, Enum):
    """思考模式"""
    PRESERVED = "preserved"      # 保留式思考（长任务）
    CLEAR_ON_NEW = "clear_on_new" # 清除式思考（批量任务）
    AUTO = "auto"                # 自动

class AIModelConfigCreate(BaseModel):
    """AI 模型配置创建"""
    model_id: str = Field(..., description="模型 ID")
    platform: str = Field(..., description="平台名称")
    api_key: str = Field(..., description="API 密钥")
    api_base_url: Optional[str] = Field(None, description="API 端点")
    temperature: float = Field(0.5, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大 token 数")

    # 思考能力配置
    thinking_enabled: bool = Field(False, description="是否启用思考能力")
    thinking_mode: Optional[ThinkingMode] = Field(None, description="思考模式")

    # 并发配置
    timeout_seconds: int = Field(60, gt=0, description="超时时间（秒）")
```

---

## 七、依赖管理

### 7.1 Poetry 依赖

```toml
# pyproject.toml

[tool.poetry.dependencies]
# LangChain 核心
langchain = "^0.3"
langchain-core = "^0.3"
langchain-openai = "^0.2"

# 可选：Anthropic Claude 支持
langchain-anthropic = "^0.2"

# 异步支持
httpx-sse = "^0.4"
```

---

## 八、迁移步骤

### 8.1 第一阶段：核心组件实现

| 任务 | 文件 | 说明 |
|------|------|------|
| 定义统一数据结构 | `core/ai/types.py` | AIMessage, AIResponse 等 |
| 实现 LangChain 适配器 | `core/ai/langchain/adapter.py` | 创建 ChatModel |
| 实现 AI 统一服务 | `core/ai/service.py` | AIService 类 |
| 实现并发管理 | `core/ai/concurrency.py` | ConcurrencyManager |

### 8.2 第二阶段：集成与测试

| 任务 | 说明 |
|------|------|
| 更新模型配置 Schema | 添加 thinking_enabled 等字段 |
| 更新 API 路由 | 使用新的 AIService |
| TradingAgents 集成 | 替换旧的 LLM 调用 |
| 前端 API 适配 | 流式输出处理 |

### 8.3 第三阶段：清理与优化

| 任务 | 说明 |
|------|------|
| 删除旧代码 | llm/provider.py, llm/thinking_adapter.py 等 |
| 添加测试 | 单元测试和集成测试 |
| 性能优化 | 模型缓存、连接池等 |

---

## 九、参考资料

### 9.1 官方文档

| 来源 | 链接 |
|------|------|
| 智谱 LangChain 集成 | https://docs.bigmodel.cn/cn/guide/develop/langchain/introduction |
| 智谱 API 文档 | https://docs.bigmodel.cn/cn/api/introduction |
| LangChain 文档 | https://python.langchain.com/docs/get_started/introduction |

### 9.2 GLM-4.7 思考能力

| 特性 | 支持状态 |
|------|----------|
| 保留式思考 (Preserved) | ✅ 通过 model_kwargs 支持 |
| 清除式思考 (Clear-on-new) | ✅ 通过 model_kwargs 支持 |
| reasoning_content 响应解析 | ✅ LangChain 自动处理 |

---

## 十、变更历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v4.0 | 2026-01-12 | 全面采用 LangChain，简化架构 |
| v3.0 | 2026-01-12 | 可扩展网关架构（已废弃） |
| v2.0 | 2026-01-12 | 多 Provider 架构（已废弃） |
| v1.0 | 2026-01-12 | 初始版本 |

---

**文档结束**
