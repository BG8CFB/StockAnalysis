"""
阶段1智能体实现 - 工厂模式

分析师团队智能体，负责从不同角度分析股票。
采用工厂模式动态创建，支持自定义配置。
"""

import logging
from typing import List, Dict, Any, Optional, Union

from langchain_core.tools import BaseTool

from modules.trading_agents.agents.base import AnalystAgent
from core.ai.llm.provider import LLMProvider
from modules.trading_agents.tools.registry import ToolRegistry, ToolDefinition
from modules.trading_agents.schemas import Phase1Config, AgentConfig
from modules.trading_agents.tools.mcp_tool_filter import filter_tools_for_agent

logger = logging.getLogger(__name__)


# =============================================================================
# 通用分析师模板
# =============================================================================

class GenericAnalystTemplate(AnalystAgent):
    """
    通用分析师模板
    
    所有第一阶段分析师都使用此模板实例化，通过配置区分角色。
    """

    def __init__(
        self, 
        slug: str, 
        name: str, 
        role_definition: str, 
        llm: LLMProvider, 
        tools: Optional[List[ToolDefinition]] = None
    ):
        """
        初始化通用分析师
        
        Args:
            slug: 唯一标识
            name: 显示名称
            role_definition: 角色定义 (Prompt)
            llm: LLM Provider
            tools: 工具列表
        """
        super().__init__(
            slug=slug,
            name=name,
            role_definition=role_definition,
            llm=llm,
            tools=tools,
        )


# =============================================================================
# 分析师工厂
# =============================================================================

class AnalystFactory:
    """
    分析师工厂

    负责根据配置动态创建分析师智能体实例。
    """

    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry):
        self.llm = llm_provider
        self.tool_registry = tool_registry

    def create_analysts(
        self,
        config: Phase1Config,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[AnalystAgent]:
        """
        根据配置创建分析师列表

        Args:
            config: 第一阶段配置
            user_id: 用户 ID（用于 MCP 连接池，预留）
            task_id: 任务 ID（用于 MCP 连接池，预留）

        Returns:
            分析师实例列表
        """
        analysts = []

        if not config.enabled:
            return []

        # TODO: 在此通过 MCP 工具过滤器获取连接
        # 当提供 user_id 和 task_id 时，预先获取 MCP 连接
        # 这将在后续实现中启用

        for agent_cfg in config.agents:
            if not agent_cfg.enabled:
                continue

            # 获取工具
            tools = self._get_tools_for_agent(agent_cfg)

            # 创建实例
            analyst = GenericAnalystTemplate(
                slug=agent_cfg.slug,
                name=agent_cfg.name,
                role_definition=agent_cfg.role_definition,
                llm=self.llm,  # TODO: 如果支持多模型，这里需要根据 config.model_id 获取特定模型
                tools=tools
            )

            analysts.append(analyst)
            logger.info(f"创建分析师智能体: {analyst.name} ({analyst.slug})")

        return analysts

    def _get_tools_for_agent(self, agent_cfg: AgentConfig) -> List[ToolDefinition]:
        """根据智能体配置获取可用工具"""
        tools = []

        # 1. 获取 MCP 工具
        for server_name in agent_cfg.enabled_mcp_servers:
            mcp_tools = self.tool_registry.get_tools_by_server(server_name)
            tools.extend(mcp_tools)

        # 2. 获取本地工具
        for tool_name in agent_cfg.enabled_local_tools:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tools.append(tool)
            else:
                logger.warning(f"智能体 {agent_cfg.slug} 配置的本地工具不存在: {tool_name}")

        return tools


# =============================================================================
# 辅助函数 (向后兼容/测试用)
# =============================================================================

def create_phase1_agents(
    llm: LLMProvider,
    tools: List[ToolDefinition] = None,
) -> List[AnalystAgent]:
    """
    创建默认的阶段1分析师智能体 (保留用于测试兼容性)
    
    注意：生产环境应使用 AnalystFactory
    """
    # 构造默认配置
    from modules.trading_agents.schemas import AgentConfig
    
    default_agents = [
        AgentConfig(
            slug="phase1_technical",
            name="技术分析师",
            role_definition="""你是一位专业的股票技术分析师。
你的任务是：
1. 分析股票的技术指标（MACD、RSI、KDJ、BOLL、MA等）
2. 识别价格趋势和关键支撑/阻力位
3. 检测图表形态（头肩顶、双底等）
4. 给出技术面买入/卖出/持有建议

请使用可用的工具获取股票数据，然后生成专业的技术分析报告。""",
            when_to_use="技术分析",
            enabled=True
        ),
        AgentConfig(
            slug="phase1_fundamental",
            name="基本面分析师",
            role_definition="""你是一位专业的股票基本面分析师。
你的任务是：
1. 分析公司的财务状况（营收、利润、现金流等）
2. 评估公司的估值水平（PE、PB、PS等）
3. 研究行业竞争格局和发展前景
4. 给出基本面买入/卖出/持有建议

请使用可用的工具获取公司数据和行业信息，然后生成专业的基本面分析报告。""",
            when_to_use="基本面分析",
            enabled=True
        ),
        AgentConfig(
            slug="phase1_sentiment",
            name="市场情绪分析师",
            role_definition="""你是一位专业的市场情绪分析师。
你的任务是：
1. 分析市场情绪和投资者预期
2. 研究资金流向（北向资金、主力资金等）
3. 分析新闻舆情和社交媒体讨论
4. 给出情绪面买入/卖出/持有建议

请使用可用的工具获取市场数据和新闻信息，然后生成专业的情绪面分析报告。""",
            when_to_use="情绪分析",
            enabled=True
        )
    ]
    
    # 手动注入工具 (因为这里绕过了 Factory 的工具查找逻辑)
    # 在这个兼容模式下，我们将所有传入的工具都给所有 agent
    
    analysts = []
    for cfg in default_agents:
        analyst = GenericAnalystTemplate(
            slug=cfg.slug,
            name=cfg.name,
            role_definition=cfg.role_definition,
            llm=llm,
            tools=tools
        )
        analysts.append(analyst)
        
    return analysts
