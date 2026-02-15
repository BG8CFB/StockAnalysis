"""
Phase 2: 看涨分析师

从多头角度论证投资机会，构建做多投资方案。

**版本**: v3.2 (LangChain create_tool_calling_agent 重构版)
**最后更新**: 2026-01-15
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from langchain.agents import create_agent
from modules.trading_agents.models.state import WorkflowState, TaskStatus
from modules.trading_agents.workflow.callbacks import WebSocketCallbackHandler

logger = logging.getLogger(__name__)


class BullResearcher:
    """
    看涨分析师

    从多头角度寻找积极因素和增长机会。
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None,
        task_id: str = None,
        websocket_manager: Any = None,
    ):
        """
        初始化看涨分析师

        Args:
            model: LLM 模型
            config: 智能体配置
            task_id: 任务 ID（用于回调推送）
            websocket_manager: WebSocket 管理器实例
        """
        self.model = model
        self.config = config or {}
        self.task_id = task_id
        self.websocket_manager = websocket_manager
        # 创建回调处理器（用于推送工具调用事件）
        self.callbacks = []
        if self.task_id and self.websocket_manager:
            callback_handler = WebSocketCallbackHandler(
                task_id=self.task_id,
                agent_slug="bull_researcher",
                agent_name="看涨分析师",
                websocket_manager=self.websocket_manager,
            )
            self.callbacks.append(callback_handler)
        self.agent = self._create_agent()

    def _create_agent(self):
        """创建智能体实例 (LangChain 1.1.0 create_agent API)"""
        system_prompt_str = self._build_system_prompt()

        # 使用 LangChain 1.1.0 的 create_agent
        # 注意: callbacks 不能在这里传递，需要在 ainvoke 时通过 config 传递
        graph = create_agent(
            model=self.model,
            tools=[],
            system_prompt=system_prompt_str,
            debug=False,
        )

        return graph

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        role_definition = self.config.get("roleDefinition", "")

        prompt = f"""
# 角色
你是一名看涨分析师，你的任务是寻找积极因素、增长机会，构建做多投资方案。

# 职责
1. 基于分析师报告，提炼出所有看涨因素
2. 构建完整的做多投资逻辑
3. 给出具体的买入建议和目标价位

# 工作流程
1. 首先阅读所有分析师的报告
2. 提炼出所有看涨因素（催化剂、增长机会、估值优势等）
3. 构建完整的做多投资逻辑（包括买入理由、持有期限、目标价位）
4. 给出明确的买入建议和风险提示

# 输出格式
```markdown
# 看涨投资方案

## 核心投资逻辑
[一句话总结做多理由]

## 看涨因素分析
### 催化剂 1
- 描述
- 预期影响
- 时间节点

### 增长机会
- ...

## 估值分析
- 当前估值
- 目标价位
- 上涨空间

## 买入建议
- 推荐等级: STRONG_BUY / BUY / HOLD
- 目标买入价
- 目标卖出价
- 持有期限

## 风险提示
[列出主要风险]
```

{role_definition}
"""
        return prompt.strip()

    async def analyze(
        self,
        state: WorkflowState,
        analyst_reports: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行看涨分析

        Args:
            state: 工作流状态
            analyst_reports: 分析师报告列表

        Returns:
            分析结果
        """
        logger.info(f"[Phase 2] 看涨分析师开始分析: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state, analyst_reports)

        try:
            # 调用智能体 (使用 AgentExecutor 的正确输入格式)
            # messages 是一个列表，提取 content 作为 input
            prompt_text = messages[0]["content"] if messages else "请进行分析。"
            # 通过 config 传递 callbacks
            config = {"recursion_limit": 10}
            if self.callbacks:
                from langchain_core.callbacks import CallbackManager
                config["configurable"] = {"callbacks": CallbackManager(self.callbacks)}
            result = await self.agent.ainvoke({"messages": [{"role": "user", "content": prompt_text}]}, config=config)

            # 提取输出
            output = self._extract_output(result)

            logger.info(f"[Phase 2] 看涨分析师分析完成: {state.stock_code}")

            return {
                "role": "bull",
                "output": output,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 2] 看涨分析师分析失败: {state.stock_code}, error={e}")

            return {
                "role": "bull",
                "output": None,
                "error": str(e)
            }

    def _build_input_messages(
        self,
        state: WorkflowState,
        analyst_reports: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """构建输入消息"""
        # 构建分析师报告摘要
        reports_summary = "\n\n".join([
            f"## {report['name']}\n{report['content']}"
            for report in analyst_reports
        ])

        prompt = f"""
请基于以下分析师报告，从看涨角度分析股票 {state.stock_code}:

# 分析师报告
{reports_summary}

请提供你的看涨投资方案，包括：
1. 核心投资逻辑
2. 看涨因素分析
3. 估值分析
4. 买入建议
5. 风险提示
"""

        return [{"role": "user", "content": prompt.strip()}]

    def _extract_output(self, result: Any) -> Optional[str]:
        """从结果中提取输出"""
        if isinstance(result, dict):
            # AgentExecutor 返回格式: {"output": "..."}
            output = result.get("output")
            if output:
                return str(output)

            # 兼容 LangGraph 格式: {"messages": [...]}
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    return last_message.content
                elif isinstance(last_message, dict):
                    return last_message.get("content")

        if isinstance(result, str):
            return result

        return str(result)
