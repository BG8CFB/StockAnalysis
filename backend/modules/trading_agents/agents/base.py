"""
智能体基类

定义所有智能体的通用行为和接口。
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from modules.trading_agents.core.state import AgentState, AnalystOutput
from core.ai.llm.provider import LLMProvider, Message, Tool
from modules.trading_agents.tools.loop_detector import check_tool_loop, clear_agent_history
from modules.trading_agents.tools.registry import ToolDefinition
from modules.trading_agents.core.exceptions import ToolCallException, ToolLoopDetectedException

logger = logging.getLogger(__name__)


# =============================================================================
# 智能体基类
# =============================================================================

class BaseAgent(ABC):
    """
    智能体基类

    所有智能体必须继承此类并实现 execute 方法。
    """

    def __init__(
        self,
        slug: str,
        name: str,
        llm: LLMProvider,
        tools: Optional[List[ToolDefinition]] = None,
    ):
        """
        初始化智能体

        Args:
            slug: 智能体唯一标识
            name: 智能体显示名称
            llm: LLM Provider
            tools: 可用工具列表
        """
        self.slug = slug
        self.name = name
        self.llm = llm
        self.tools = tools or []

        # Token 追踪
        self._token_usage: Dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    @abstractmethod
    async def execute(self, state: AgentState) -> str:
        """
        执行智能体逻辑

        Args:
            state: 工作流状态

        Returns:
            分析报告内容
        """
        pass

    def get_system_prompt(self) -> str:
        """
        获取系统提示词

        Returns:
            系统提示词内容
        """
        return ""

    def build_messages(self, state: AgentState) -> List[Message]:
        """
        构建消息列表

        Args:
            state: 工作流状态

        Returns:
            消息列表
        """
        messages = [
            Message(role="system", content=self.get_system_prompt()),
            Message(role="user", content=self.build_user_message(state)),
        ]
        return messages

    def build_user_message(self, state: AgentState) -> str:
        """
        构建用户消息

        Args:
            state: 工作流状态

        Returns:
            用户消息内容
        """
        return f"""
请分析以下股票：
- 股票代码：{state['stock_code']}
- 交易日期：{state['trade_date']}

请生成专业的分析报告。
"""

    async def call_llm(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        **kwargs
    ) -> str:
        """
        调用 LLM

        Args:
            messages: 消息列表
            tools: 可用工具列表
            **kwargs: 其他参数

        Returns:
            LLM 响应内容
        """
        try:
            # 转换工具定义格式
            llm_tools = None
            if tools:
                llm_tools = [
                    Tool(type=tool.type, function=tool.function)
                    for tool in tools
                ]

            response = await self.llm.chat_completion(
                messages=messages,
                tools=llm_tools,
                **kwargs
            )

            # 记录 token 使用
            if response.usage:
                self._token_usage["prompt_tokens"] += response.usage.get("prompt_tokens", 0)
                self._token_usage["completion_tokens"] += response.usage.get("completion_tokens", 0)
                self._token_usage["total_tokens"] += response.usage.get("total_tokens", 0)

            return response.content

        except Exception as e:
            logger.error(f"LLM 调用失败: agent={self.slug}, error={e}")
            raise

    def get_token_usage(self) -> Dict[str, int]:
        """
        获取 token 使用量

        Returns:
            Token 使用量字典
        """
        return self._token_usage.copy()

    def reset_token_usage(self) -> None:
        """重置 token 使用量"""
        self._token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    async def with_tool_loop_detection(
        self,
        task_id: str,
        state: AgentState,
        func: callable,
    ) -> Any:
        """
        带工具循环检测的执行

        Args:
            task_id: 任务 ID
            state: 工作流状态
            func: 要执行的函数

        Returns:
            函数执行结果
        """
        try:
            return await func()

        except ToolLoopDetectedException as e:
            # 工具循环检测触发
            disabled_tool = e.details.get("tool_name") if e.details else None
            logger.warning(f"工具循环检测触发: agent={self.slug}, tool={disabled_tool}")
            # 不再重试，让智能体继续执行（工具已被禁用）
            raise

        finally:
            # 清除调用历史
            clear_agent_history(task_id, self.slug)


# =============================================================================
# 分析师智能体基类
# =============================================================================

class AnalystAgent(BaseAgent):
    """
    分析师智能体基类

    第一阶段的所有分析师都应继承此类。
    """

    def __init__(
        self,
        slug: str,
        name: str,
        role_definition: str,
        llm: LLMProvider,
        tools: Optional[List[ToolDefinition]] = None,
    ):
        """
        初始化分析师智能体

        Args:
            slug: 智能体唯一标识
            name: 智能体显示名称
            role_definition: 角色定义（系统提示词）
            llm: LLM Provider
            tools: 可用工具列表
        """
        super().__init__(slug, name, llm, tools)
        self.role_definition = role_definition

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.role_definition

    async def execute(self, state: AgentState) -> str:
        """
        执行分析师逻辑

        Args:
            state: 工作流状态

        Returns:
            分析报告内容
        """
        # 构建消息
        messages = self.build_messages(state)

        # 转换工具定义
        llm_tools = None
        if self.tools:
            from core.ai.llm.provider import Tool as LLMTool
            llm_tools = [
                LLMTool(
                    type="function",
                    function={
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                )
                for tool in self.tools
            ]

        # 调用 LLM
        report = await self.with_tool_loop_detection(
            task_id=state["task_id"],
            state=state,
            func=lambda: self.call_llm(messages, llm_tools)
        )

        return report

    def to_analyst_output(self, report: str, state: AgentState) -> AnalystOutput:
        """
        转换为分析师输出格式

        Args:
            report: 报告内容
            state: 工作流状态

        Returns:
            分析师输出对象
        """
        return AnalystOutput(
            agent_name=self.name,
            role=self.slug,
            content=report,
            data_sources=[t.mcp_server for t in self.tools if t.mcp_server],
            timestamp=time.time(),
            token_usage=self.get_token_usage(),
        )


# =============================================================================
# 辩论智能体基类
# =============================================================================

class DebateAgent(BaseAgent):
    """
    辩论智能体基类

    第二、三阶段的辩论智能体都应继承此类。
    """

    def __init__(
        self,
        slug: str,
        name: str,
        role_definition: str,
        llm: LLMProvider,
        opponent_view: Optional[str] = None,
    ):
        """
        初始化辩论智能体

        Args:
            slug: 智能体唯一标识
            name: 智能体显示名称
            role_definition: 角色定义（系统提示词）
            llm: LLM Provider
            opponent_view: 对手观点（用于反驳）
        """
        super().__init__(slug, name, llm, tools=[])
        self.role_definition = role_definition
        self.opponent_view = opponent_view

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        prompt = self.role_definition

        # 如果有对手观点，添加到提示词中
        if self.opponent_view:
            prompt += f"""

<opponent_view>
{self.opponent_view}
</opponent_view>

请针对以上观点进行反驳和论证。
"""

        return prompt

    def set_opponent_view(self, view: str) -> None:
        """
        设置对手观点

        Args:
            view: 对手观点
        """
        self.opponent_view = view

    async def execute(self, state: AgentState) -> str:
        """
        执行辩论智能体逻辑

        Args:
            state: 工作流状态

        Returns:
            辩论内容
        """
        messages = self.build_messages(state)
        return await self.call_llm(messages)


# =============================================================================
# 总结智能体基类
# =============================================================================

class SummaryAgent(BaseAgent):
    """
    总结智能体基类

    第四阶段的总结智能体应继承此类。
    """

    def __init__(
        self,
        slug: str,
        name: str,
        role_definition: str,
        llm: LLMProvider,
    ):
        """
        初始化总结智能体

        Args:
            slug: 智能体唯一标识
            name: 智能体显示名称
            role_definition: 角色定义（系统提示词）
            llm: LLM Provider
        """
        super().__init__(slug, name, llm, tools=[])
        self.role_definition = role_definition

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.role_definition

    def build_user_message(self, state: AgentState) -> str:
        """构建用户消息（包含所有报告）"""
        message = super().build_user_message(state)

        # 添加所有已完成的分析报告
        if state.get("analyst_reports"):
            message += "\n\n## 分析师报告\n\n"
            for report in state["analyst_reports"]:
                message += f"### {report['agent_name']}\n\n"
                message += report["content"]
                message += "\n\n---\n\n"

        # 添加辩论结果（如果有）
        if state.get("trade_plan"):
            message += f"\n## 交易计划\n\n{state['trade_plan']}\n\n"

        # 添加风险评估（如果有）
        if state.get("risk_assessment"):
            message += f"\n## 风险评估\n\n{state['risk_assessment']}\n\n"

        return message

    async def execute(self, state: AgentState) -> str:
        """
        执行总结智能体逻辑

        Args:
            state: 工作流状态

        Returns:
            最终报告内容
        """
        messages = self.build_messages(state)
        return await self.call_llm(messages)
