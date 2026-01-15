"""
Phase 1 智能体模板

**版本**: v4.0 (LangChain 1.1.0 create_agent 重构版)
**最后更新**: 2026-01-15

智能体模板，用于动态创建分析师智能体。
"""

import logging
from typing import Dict, Any, Optional, List

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from modules.trading_agents.models.state import WorkflowState, AgentExecution, TaskStatus

logger = logging.getLogger(__name__)


class Phase1AgentTemplate:
    """
    Phase 1 智能体模板

    提供分析师智能体的基础模板和通用功能。
    """

    def __init__(
        self,
        model: BaseChatModel,
        agent_config: Dict[str, Any],
        tools: List[BaseTool]
    ):
        """
        初始化智能体模板

        Args:
            model: LLM 模型
            agent_config: 智能体配置
            tools: 工具列表
        """
        self.model = model
        self.config = agent_config
        self.tools = tools
        self.slug = agent_config.get("slug", "unknown")
        self.name = agent_config.get("name", "分析师")
        self.agent = self._create_agent()

    def _create_agent(self):
        """创建智能体实例 (LangChain 1.1.0 create_agent API)"""
        system_prompt_str = self._build_system_prompt()

        # 使用 LangChain 1.1.0 的 create_agent
        # 返回 CompiledStateGraph
        graph = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=system_prompt_str,
            debug=False
        )

        return graph

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词

        Args:
            agent_config: 智能体配置

        Returns:
            系统提示词
        """
        # 基础角色定义
        role_definition = self.config.get("roleDefinition", "")

        # 添加上下文信息
        prompt = f"""
# 角色信息
- 名称: {self.name}
- 描述: {self.config.get('description', '')}

# 角色定义
{role_definition}

# 输出要求
1. 所有报告必须使用 Markdown 格式
2. 报告必须包含时间戳和数据来源
3. 结论必须基于数据和逻辑，禁止主观臆测
4. 如果数据缺失，必须明确说明而非编造
"""
        return prompt.strip()

    async def execute(
        self,
        state: WorkflowState,
        user_prompt: str
    ) -> Dict[str, Any]:
        """
        执行智能体分析

        Args:
            state: 工作流状态
            user_prompt: 用户提示词

        Returns:
            执行结果
        """
        # 创建执行记录
        execution = AgentExecution(
            slug=self.slug,
            name=self.name,
            status=TaskStatus.RUNNING,
        )

        try:
            # 调用 agent (LangChain 1.1.0 create_agent 格式)
            logger.info(f"[Phase 1] 执行智能体: {self.slug} ({self.name})")

            # LangChain 1.1.0 使用 messages 格式
            inputs = {
                "messages": [
                    {"role": "user", "content": user_prompt}
                ]
            }

            result = await self.agent.ainvoke(inputs, config={"recursion_limit": 10})

            # 提取输出
            output = self._extract_output(result)

            # 更新执行记录
            execution.status = TaskStatus.COMPLETED
            execution.output = output

            logger.info(
                f"[Phase 1] 智能体完成: {self.slug} ({self.name}), "
                f"输出长度: {len(output) if output else 0}"
            )

            return {
                "slug": self.slug,
                "name": self.name,
                "output": output,
                "execution": execution,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 1] 智能体失败: {self.slug} ({self.name}), error={e}")

            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)

            return {
                "slug": self.slug,
                "name": self.name,
                "output": None,
                "execution": execution,
                "error": str(e)
            }

    def _extract_output(self, result: Any) -> Optional[str]:
        """
        从 agent 结果中提取输出

        Args:
            result: agent 返回结果

        Returns:
            输出文本
        """
        if isinstance(result, dict):
            # LangChain 1.1.0 create_agent 返回格式: {"messages": [...]}
            messages = result.get("messages", [])
            if messages:
                # 获取最后一条消息
                last_message = messages[-1]
                # 处理消息对象
                if hasattr(last_message, "content"):
                    return last_message.content
                # 处理字典格式
                elif isinstance(last_message, dict):
                    return last_message.get("content", "")

        # 直接返回字符串
        if isinstance(result, str):
            return result

        return str(result)
