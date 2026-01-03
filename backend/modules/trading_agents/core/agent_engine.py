"""
智能体工作流引擎

使用 LangGraph 编排四阶段股票分析工作流。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from modules.trading_agents.models import AgentState, create_initial_state
from modules.trading_agents.agents.base import BaseAgent, AnalystAgent
from modules.trading_agents.agents.phase1.analysts import AnalystFactory
from modules.trading_agents.agents.phase2 import create_phase2_agents
from modules.trading_agents.agents.phase3 import create_phase3_agents
from modules.trading_agents.agents.phase4 import create_phase4_agents
from core.ai.llm.provider import LLMProvider
from modules.trading_agents.tools.registry import ToolRegistry
from modules.trading_agents.schemas import (
    AnalysisTaskCreate,
    UserAgentConfigResponse,
    RecommendationEnum,
)
from modules.trading_agents.websocket import get_ws_manager
from modules.trading_agents.core.concurrency import get_concurrency_manager

logger = logging.getLogger(__name__)


# =============================================================================
# 工作流引擎
# =============================================================================

class AgentWorkflowEngine:
    """
    智能体工作流引擎

    编排四阶段分析工作流：
    1. 分析师团队（并行，工厂模式创建）
    2. 研究员辩论（含研究经理裁决）
    3. 风险评估（多派别讨论 + CRO总结）
    4. 总结输出
    """

    def __init__(
        self,
        llm: LLMProvider,
        config: UserAgentConfigResponse,
        ws_manager = None,
        data_collection_llm: Optional[LLMProvider] = None,
        data_collection_model_config: Optional[Dict[str, Any]] = None,
        debate_model_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化工作流引擎

        Args:
            llm: LLM Provider（默认用于所有阶段，优先级低于data_collection_llm）
            config: 用户智能体配置
            ws_manager: WebSocket 管理器（用于实时推送）
            data_collection_llm: 数据收集阶段LLM（第一阶段）
            data_collection_model_config: 数据收集模型配置（包含thinking_enabled等）
            debate_model_config: 辩论模型配置（包含thinking_enabled等）
        """
        self.llm = llm
        self.config = config
        self.ws_manager = ws_manager  # 如果为None，调用者负责处理

        # 双模型支持
        self.data_collection_llm = data_collection_llm or llm
        self.debate_llm = llm

        # 模型配置（用于思考模式）
        self.data_collection_model_config = data_collection_model_config or {}
        self.debate_model_config = debate_model_config or {}

        # 并发控制器
        self.concurrency = get_concurrency_manager()

        # 工具注册表
        self.tool_registry = ToolRegistry()

        # 阶段配置
        self.phase1_enabled = config.phase1.enabled
        self.phase2_enabled = config.phase2.enabled if config.phase2 else False
        self.phase3_enabled = config.phase3.enabled if config.phase3 else False
        self.phase4_enabled = config.phase4.enabled if config.phase4 else False

        # 智能体映射（动态初始化）
        self._agents: Dict[str, BaseAgent] = {}
        self._phase1_agents: List[AnalystAgent] = []

    def register_agent(self, agent: BaseAgent) -> None:
        """
        注册智能体

        Args:
            agent: 智能体实例
        """
        self._agents[agent.slug] = agent
        logger.info(f"注册智能体: {agent.slug}")

    def _collect_enabled_agent_configs(self) -> List[Any]:
        """
        收集所有启用的智能体配置

        Returns:
            启用的智能体配置列表
        """
        from modules.trading_agents.schemas import AgentConfig

        agent_configs: List[Any] = []

        if self.config.phase1 and self.config.phase1.enabled:
            agent_configs.extend([cfg for cfg in self.config.phase1.agents if cfg.enabled])
        if self.config.phase2 and self.config.phase2.enabled:
            agent_configs.extend([cfg for cfg in self.config.phase2.agents if cfg.enabled])
        if self.config.phase3 and self.config.phase3.enabled:
            agent_configs.extend([cfg for cfg in self.config.phase3.agents if cfg.enabled])
        if self.config.phase4 and self.config.phase4.enabled:
            agent_configs.extend([cfg for cfg in self.config.phase4.agents if cfg.enabled])

        return agent_configs

    def _collect_mcp_server_configs(
        self,
        agent_configs: List[Any],
    ) -> Dict[str, Dict[str, Any]]:
        """
        收集所有智能体的 MCP 服务器配置

        Args:
            agent_configs: 智能体配置列表

        Returns:
            {server_name: {"required": bool, "config": MCPServerConfig, "agents": [agent_slugs]}}
        """
        server_configs: Dict[str, Dict[str, Any]] = {}

        for agent_cfg in agent_configs:
            for server_config in agent_cfg.enabled_mcp_servers:
                server_name = server_config.name
                if server_name not in server_configs:
                    server_configs[server_name] = {
                        "required": server_config.required,
                        "config": server_config,
                        "agents": [],
                    }
                server_configs[server_name]["agents"].append(agent_cfg.slug)

        return server_configs

    async def _validate_mcp_servers_available(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """
        验证 MCP 服务器可用性（不创建连接）

        根据最佳实践，在预检查阶段只验证服务器可用性，
        不实际创建连接，避免双重连接问题。
        实际连接在智能体初始化时按需创建。

        Args:
            user_id: 用户 ID
            task_id: 任务 ID

        Returns:
            验证结果统计
        """
        from modules.trading_agents.tools.mcp_tool_filter import get_mcp_tool_filter

        logger.info(f"[MCP可用性检查] 开始验证MCP服务器: user_id={user_id}, task_id={task_id}")

        # 使用辅助方法收集智能体配置
        agent_configs = self._collect_enabled_agent_configs()

        if not agent_configs:
            logger.info("[MCP可用性检查] 没有启用的智能体，跳过验证")
            return {"total_servers": 0, "required_available": 0, "optional_available": 0}

        # 使用辅助方法收集服务器配置
        server_configs = self._collect_mcp_server_configs(agent_configs)

        if not server_configs:
            logger.info("[MCP可用性检查] 没有配置MCP服务器")
            return {"total_servers": 0, "required_available": 0, "optional_available": 0}

        # 获取可用的服务器列表（只查询，不创建连接）
        mcp_filter = get_mcp_tool_filter()
        available_servers = await mcp_filter._get_available_servers(user_id)
        available_server_names = set(available_servers.keys())

        # 分类检查：required vs optional
        required_unavailable = []
        optional_unavailable = []
        required_available = []
        optional_available = []

        for server_name, config in server_configs.items():
            if server_name in available_server_names:
                if config["required"]:
                    required_available.append(server_name)
                else:
                    optional_available.append(server_name)
            else:
                if config["required"]:
                    required_unavailable.append(server_name)
                else:
                    optional_unavailable.append(server_name)

        # 必需服务器不可用时抛出异常
        if required_unavailable:
            raise RuntimeError(
                f"必需的 MCP 服务器不可用: {', '.join(required_unavailable)}\n"
                f"可用的服务器: {', '.join(available_server_names) or '无'}\n"
                f"影响的智能体: {', '.join(set(server_configs[s]['agents'][0] for s in required_unavailable))}"
            )

        # 可选服务器不可用时记录警告
        if optional_unavailable:
            logger.warning(
                f"[MCP可用性检查] 可选服务器不可用（已跳过）: {', '.join(optional_unavailable)}. "
                f"可用的服务器: {', '.join(available_server_names) or '无'}"
            )

        # 如果所有服务器都不可用，阻止任务启动
        if not available_server_names:
            raise RuntimeError(
                f"所有 MCP 服务器均不可用，任务无法启动。\n"
                f"配置的服务器: {', '.join(server_configs.keys())}"
            )

        logger.info(
            f"[MCP可用性检查] 验证完成: "
            f"总计={len(server_configs)}, "
            f"必需可用={len(required_available)}, "
            f"可选可用={len(optional_available)}, "
            f"可选不可用={len(optional_unavailable)}"
        )

        return {
            "total_servers": len(server_configs),
            "required_available": len(required_available),
            "optional_available": len(optional_available),
            "optional_unavailable": optional_unavailable,
        }

    async def _initialize_mcp_connections(self, user_id: str, task_id: str) -> None:
        """
        预初始化所有 MCP 连接（快速失败 + 连接缓存）

        设计原则：
        1. 任务开始时就创建所有 MCP 连接，确保依赖就绪
        2. 如果任何连接失败，立即阻止任务启动（快速失败）
        3. 连接会被缓存，智能体初始化时复用（避免重复创建）
        4. 支持 required/optional 容错策略

        Args:
            user_id: 用户 ID
            task_id: 任务 ID

        Raises:
            RuntimeError: 当必需 MCP 服务器连接失败时
        """
        from modules.trading_agents.tools.mcp_tool_filter import get_mcp_tool_filter

        logger.info(f"[MCP预初始化] 开始创建MCP连接: user_id={user_id}, task_id={task_id}")

        # 使用辅助方法收集智能体配置
        agent_configs = self._collect_enabled_agent_configs()

        if not agent_configs:
            logger.info("[MCP预初始化] 没有启用的智能体，跳过MCP初始化")
            return

        # 使用辅助方法收集服务器配置（提取 MCPServerConfig）
        server_configs_data = self._collect_mcp_server_configs(agent_configs)

        # 转换为 {server_name: MCPServerConfig} 格式
        server_configs_map = {
            name: data["config"]
            for name, data in server_configs_data.items()
        }

        if not server_configs_map:
            logger.info("[MCP预初始化] 没有配置MCP服务器")
            return

        # 获取 MCP 工具过滤器
        mcp_filter = get_mcp_tool_filter()
        all_tools = self.tool_registry.list_all_tools()

        # 按服务器分类：required vs optional
        required_servers = []
        optional_servers = []

        for server_name, server_config in server_configs_map.items():
            if server_config.required:
                required_servers.append((server_name, server_config))
            else:
                optional_servers.append((server_name, server_config))

        # 第一步：初始化所有必需服务器（任何一个失败则阻止任务）
        for server_name, server_config in required_servers:
            try:
                # 创建临时 AgentConfig 用于预初始化
                # 连接会被缓存，后续智能体可以复用
                temp_agent_config = AgentConfig(
                    slug="_temp_preinit",
                    name="Temporary",
                    when_to_use="",
                    enabled_mcp_servers=[server_config],
                )

                tools = await mcp_filter.get_tools_for_agent(
                    agent_config=temp_agent_config,
                    user_id=user_id,
                    task_id=task_id,
                    all_tools=all_tools,
                )

                logger.info(
                    f"[MCP预初始化] 必需服务器 {server_name} 初始化成功: "
                    f"{len(tools)} 个工具"
                )

            except Exception as e:
                logger.error(
                    f"[MCP预初始化] 必需服务器 {server_name} 初始化失败: {e}",
                    exc_info=True
                )
                # ✅ 关键：必需服务器失败，立即抛出异常，阻止任务启动
                raise RuntimeError(
                    f"必需 MCP 服务器 '{server_name}' 初始化失败: {e}\n"
                    f"任务无法启动，请检查该服务器配置。"
                ) from e

        # 第二步：初始化所有可选服务器（失败时记录警告，不阻止任务）
        for server_name, server_config in optional_servers:
            try:
                temp_agent_config = AgentConfig(
                    slug="_temp_preinit",
                    name="Temporary",
                    when_to_use="",
                    enabled_mcp_servers=[server_config],
                )

                tools = await mcp_filter.get_tools_for_agent(
                    agent_config=temp_agent_config,
                    user_id=user_id,
                    task_id=task_id,
                    all_tools=all_tools,
                )

                logger.info(
                    f"[MCP预初始化] 可选服务器 {server_name} 初始化成功: "
                    f"{len(tools)} 个工具"
                )

            except Exception as e:
                logger.warning(
                    f"[MCP预初始化] 可选服务器 {server_name} 初始化失败（已跳过）: {e}"
                )
                # ✅ 可选服务器失败，记录警告但不抛出异常
                continue

        logger.info("[MCP预初始化] MCP连接预初始化完成")

    async def _initialize_agents_for_task(self, user_id: str, task_id: str) -> None:
        """
        为任务动态初始化智能体（带 MCP 连接）

        执行流程：
        1. 预初始化 MCP 连接（快速失败，连接缓存）
        2. 初始化各阶段智能体（复用已缓存的 MCP 连接）

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
        """
        logger.info(f"开始为任务初始化智能体: user_id={user_id}, task_id={task_id}")

        # 第一步：预初始化所有 MCP 连接（快速失败）
        # 连接会被缓存，后续智能体初始化时复用
        await self._initialize_mcp_connections(user_id, task_id)

        # Phase 1: 使用工厂动态创建（异步，按需创建 MCP 连接）
        if self.config.phase1:
            factory = AnalystFactory(self.data_collection_llm, self.tool_registry)
            analysts = await factory.create_analysts(
                self.config.phase1,
                user_id=user_id,
                task_id=task_id,
            )
            self._phase1_agents = analysts
            for agent in analysts:
                # 设置数据收集模型的思考配置
                self._apply_thinking_config(agent, self.data_collection_model_config)
                self.register_agent(agent)

        # Phase 2: 研究员辩论
        if self.config.phase2:
            phase2_agents = create_phase2_agents(self.debate_llm, phase2_config=self.config.phase2)
            for agent in phase2_agents:
                # 设置辩论模型的思考配置
                self._apply_thinking_config(agent, self.debate_model_config)
                self.register_agent(agent)

        # Phase 3: 风险评估
        if self.config.phase3:
            phase3_agents = create_phase3_agents(self.debate_llm, phase3_config=self.config.phase3)
            for agent in phase3_agents:
                # 设置辩论模型的思考配置
                self._apply_thinking_config(agent, self.debate_model_config)
                self.register_agent(agent)

        # Phase 4: 总结
        if self.config.phase4:
            phase4_agents = create_phase4_agents(self.debate_llm, phase4_config=self.config.phase4)
            for agent in phase4_agents:
                # 设置辩论模型的思考配置
                self._apply_thinking_config(agent, self.debate_model_config)
                self.register_agent(agent)

        logger.info(f"智能体初始化完成: 总计 {len(self._agents)} 个智能体")

    def get_agent(self, slug: str) -> Optional[BaseAgent]:
        """
        获取智能体

        Args:
            slug: 智能体标识

        Returns:
            智能体实例或 None
        """
        return self._agents.get(slug)

    async def execute_workflow(
        self,
        task_id: str,
        user_id: str,
        request: AnalysisTaskCreate,
    ) -> Dict[str, Any]:
        """
        执行完整工作流

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            request: 分析任务请求（包含 stages 配置）

        Returns:
            最终报告和元数据
        """
        # 动态初始化智能体（传递 user_id 和 task_id）
        await self._initialize_agents_for_task(user_id, task_id)

        # 从 request.stages 中读取阶段配置
        stages = request.stages
        stage1_enabled = stages.stage1.enabled
        stage2_enabled = stages.stage2.enabled
        stage3_enabled = stages.stage3.enabled
        stage4_enabled = stages.stage4.enabled

        # 获取辩论轮次配置
        phase2_debate_rounds = stages.stage2.debate.rounds if stage2_enabled and stages.stage2.debate.enabled else 0
        phase3_debate_rounds = stages.stage3.debate.rounds if stage3_enabled and stages.stage3.debate.enabled else 0

        # 1. 创建初始状态
        state = create_initial_state(
            task_id=task_id,
            user_id=user_id,
            stock_code=request.stock_code,
            trade_date=request.trade_date,
            max_debate_rounds=phase2_debate_rounds if phase2_debate_rounds > 0 else 2,
            expected_analysts=len(self._get_phase1_agents(stages)),
            selected_agents=stages.stage1.selected_agents,
        )

        logger.info(f"开始工作流执行: task_id={task_id}, stock={request.stock_code}")
        logger.info(f"阶段配置: stage1={stage1_enabled}, stage2={stage2_enabled}, stage3={stage3_enabled}, stage4={stage4_enabled}")

        # 发送开始事件
        await self._send_event(task_id, "workflow_started", {
            "stock_code": request.stock_code,
            "phase1_enabled": stage1_enabled,
            "phase2_enabled": stage2_enabled,
            "phase3_enabled": stage3_enabled,
            "phase4_enabled": stage4_enabled,
        })

        try:
            # ====================================================================
            # 阶段 1：分析师团队（并行执行）
            # ====================================================================
            if stage1_enabled:
                await self._execute_phase1(state, stages)
            else:
                logger.info(f"阶段1已禁用，跳过: task_id={task_id}")

            # ====================================================================
            # 阶段 2：研究员辩论
            # ====================================================================
            if stage2_enabled and self._should_continue(state):
                await self._execute_phase2(state, stages)
            else:
                logger.info(f"阶段2已禁用或跳过: task_id={task_id}")

            # ====================================================================
            # 阶段 3：风险评估
            # ====================================================================
            if stage3_enabled and self._should_continue(state):
                await self._execute_phase3(state, stages)
            else:
                logger.info(f"阶段3已禁用或跳过: task_id={task_id}")

            # ====================================================================
            # 阶段 4：总结输出
            # ====================================================================
            if stage4_enabled and self._should_continue(state):
                await self._execute_phase4(state)
            else:
                logger.info(f"阶段4已禁用或跳过: task_id={task_id}")

            # 标记完成
            state["status"] = "completed"

            # 发送完成事件
            await self._send_event(task_id, "workflow_completed", {
                "final_report": state.get("final_report"),
                "total_tokens": state["total_token_usage"],
            })

            return {
                "final_report": state.get("final_report", "无报告"),
                "analyst_reports": state.get("analyst_reports", []),
                "trade_plan": state.get("trade_plan"),
                "risk_assessment": state.get("risk_assessment"),
                "token_usage": state["total_token_usage"],
                "status": "completed",
            }

        except Exception as e:
            logger.error(f"工作流执行失败: task_id={task_id}, error={e}")
            state["status"] = "failed"

            await self._send_event(task_id, "workflow_failed", {
                "error": str(e),
            })

            raise

    # ========================================================================
    # 阶段执行方法
    # ========================================================================

    async def _execute_phase1(self, state: AgentState, stages) -> None:
        """
        执行阶段1：分析师团队

        Args:
            state: 工作流状态
            stages: 阶段配置对象

        并行调用所有用户选择的已启用分析师智能体。
        """
        phase1_agents = self._get_phase1_agents(stages)

        if not phase1_agents:
            logger.warning("没有启用的分析师智能体")
            return

        logger.info(f"开始阶段1: {len(phase1_agents)}个分析师并行执行")

        await self._send_event(state["task_id"], "phase1_started", {
            "analysts": [agent.name for agent in phase1_agents],
        })

        # 并行执行（使用并发控制）
        tasks = [
            self._run_analyst(agent, state)
            for agent in phase1_agents
        ]

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"分析师执行失败: {phase1_agents[i].slug}, error={result}")
            else:
                # 添加到状态
                state["analyst_reports"].append(result)
                state["completed_analysts"] += 1

                # 发送进度事件
                await self._send_event(state["task_id"], "analyst_completed", {
                    "agent_name": phase1_agents[i].name,
                    "progress": f"{state['completed_analysts']}/{state['expected_analysts']}",
                })

        logger.info(f"阶段1完成: {state['completed_analysts']}/{state['expected_analysts']}个分析师完成")

    async def _execute_phase2(self, state: AgentState, stages) -> None:
        """
        执行阶段2：研究员辩论

        Args:
            state: 工作流状态
            stages: 阶段配置对象

        实现看涨/看跌研究员之间的多轮辩论。
        使用 DebateManager 管理辩论流程。
        """
        # 从 stages 配置中获取辩论轮次
        debate_enabled = stages.stage2.debate.enabled if stages else True
        max_rounds = stages.stage2.debate.rounds if stages and debate_enabled else state.get("max_debate_rounds", 2)

        logger.info(f"开始阶段2: 最多{max_rounds}轮辩论, 辩论启用={debate_enabled}")

        await self._send_event(state["task_id"], "phase2_started", {
            "max_rounds": max_rounds,
            "debate_enabled": debate_enabled,
        })

        # 提取初始观点（从分析师报告中）
        reports = state.get("analyst_reports", [])
        if not reports:
            logger.warning("没有分析师报告，跳过辩论")
            return

        # 获取辩论智能体
        bull_agent = self.get_agent("phase2_bull")
        bear_agent = self.get_agent("phase2_bear")
        trade_plan_agent = self.get_agent("phase2_planner")

        if not bull_agent or not bear_agent:
            logger.warning("缺少辩论智能体，跳过阶段2")
            return

        # 如果启用辩论，运行辩论
        if debate_enabled and max_rounds > 0:
            from modules.trading_agents.agents.phase2.debate_manager import DebateManager

            debate_manager = DebateManager(
                bull_agent=bull_agent,
                bear_agent=bear_agent,
                max_rounds=max_rounds,
            )

            # 运行辩论
            await debate_manager.run_debate(state)

            # 每轮辩论后发送进度事件
            for turn in state.get("debate_turns", []):
                await self._send_event(state["task_id"], "debate_round_completed", {
                    "round": turn["round_index"],
                    "max_rounds": max_rounds,
                })

        # 研究经理裁决
        research_manager = self.get_agent("phase2_manager")
        if research_manager:
            logger.info("研究经理开始裁决")
            decision = await research_manager.execute(state)
            state["manager_decision"] = decision

            # 累加 token
            token_usage = research_manager.get_token_usage()
            state["total_token_usage"]["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
            state["total_token_usage"]["completion_tokens"] += token_usage.get("completion_tokens", 0)
            state["total_token_usage"]["total_tokens"] += token_usage.get("total_tokens", 0)

            await self._send_event(state["task_id"], "research_manager_decision", {
                "decision": decision[:200] + "..."
            })

        # 生成交易计划
        if trade_plan_agent:
            state["trade_plan"] = await trade_plan_agent.execute(state)
            # 累加 token 使用量
            token_usage = trade_plan_agent.get_token_usage()
            state["total_token_usage"]["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
            state["total_token_usage"]["completion_tokens"] += token_usage.get("completion_tokens", 0)
            state["total_token_usage"]["total_tokens"] += token_usage.get("total_tokens", 0)

        # 累加辩论智能体的 token 使用量（如果运行了辩论）
        if debate_enabled:
            if bull_agent:
                token_usage = bull_agent.get_token_usage()
                state["total_token_usage"]["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
                state["total_token_usage"]["completion_tokens"] += token_usage.get("completion_tokens", 0)
                state["total_token_usage"]["total_tokens"] += token_usage.get("total_tokens", 0)
            if bear_agent:
                token_usage = bear_agent.get_token_usage()
                state["total_token_usage"]["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
                state["total_token_usage"]["completion_tokens"] += token_usage.get("completion_tokens", 0)
                state["total_token_usage"]["total_tokens"] += token_usage.get("total_tokens", 0)

        logger.info("阶段2完成")

    async def _execute_phase3(self, state: AgentState, stages) -> None:
        """
        执行阶段3：风险评估

        Args:
            state: 工作流状态
            stages: 阶段配置对象

        多派别风险讨论 + CRO 总结
        """
        # 从 stages 配置中获取辩论轮次
        debate_enabled = stages.stage3.debate.enabled if stages else False
        max_rounds = stages.stage3.debate.rounds if stages and debate_enabled else 1

        logger.info(f"开始阶段3: 风险评估, 辩论启用={debate_enabled}, 轮次={max_rounds}")

        await self._send_event(state["task_id"], "phase3_started", {})

        # 获取相关智能体
        aggressive = self.get_agent("phase3_aggressive")
        conservative = self.get_agent("phase3_conservative")
        neutral = self.get_agent("phase3_neutral")
        cro = self.get_agent("phase3_cro")

        if not (aggressive and conservative and neutral and cro):
             logger.warning("缺少风险评估智能体，跳过阶段3")
             state["risk_assessment"] = "风险评估智能体缺失，无法执行评估"
             return

        # 1. 运行风险讨论
        from ..agents.phase3.risk_manager import RiskDiscussionManager
        
        discussion_manager = RiskDiscussionManager(
            aggressive_agent=aggressive,
            conservative_agent=conservative,
            neutral_agent=neutral,
            max_rounds=1 # 目前简化为1轮
        )
        
        await discussion_manager.run_discussion(state)
        
        # 发送讨论完成事件
        await self._send_event(state["task_id"], "risk_discussion_completed", {
            "turns_count": len(state.get("risk_discussion_turns", []))
        })
        
        # 2. CRO 总结
        state["risk_assessment"] = await cro.execute(state)
        
        # 累加 token 使用量 (所有参与者)
        for agent in [aggressive, conservative, neutral, cro]:
            token_usage = agent.get_token_usage()
            state["total_token_usage"]["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
            state["total_token_usage"]["completion_tokens"] += token_usage.get("completion_tokens", 0)
            state["total_token_usage"]["total_tokens"] += token_usage.get("total_tokens", 0)

        logger.info("阶段3完成")

    async def _execute_phase4(self, state: AgentState) -> None:
        """
        执行阶段4：总结输出

        汇总所有阶段的报告，生成最终分析报告。
        """
        logger.info("开始阶段4: 总结输出")

        await self._send_event(state["task_id"], "phase4_started", {})

        summary_agent = self.get_agent("phase4_summary")
        if summary_agent:
            state["final_report"] = await summary_agent.execute(state)
            # 累加 token 使用量
            token_usage = summary_agent.get_token_usage()
            state["total_token_usage"]["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
            state["total_token_usage"]["completion_tokens"] += token_usage.get("completion_tokens", 0)
            state["total_token_usage"]["total_tokens"] += token_usage.get("total_tokens", 0)
        else:
            logger.warning("缺少总结智能体")
            # 简单汇总
            state["final_report"] = self._simple_summary(state)

        logger.info("阶段4完成")

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _get_phase1_agents(self, stages) -> List[AnalystAgent]:
        """
        获取阶段1启用的分析师智能体

        Args:
            stages: 阶段配置对象，包含用户选择的智能体列表

        Returns:
            用户选择且已启用的分析师智能体列表
        """
        agents = []
        selected_slugs = stages.stage1.selected_agents if stages else []

        # 如果用户没有选择任何智能体，返回所有启用的
        if not selected_slugs:
            for slug, agent in self._agents.items():
                if slug.startswith("phase1_") and isinstance(agent, AnalystAgent):
                    if self._is_agent_enabled(slug):
                        agents.append(agent)
            return agents

        # 返回用户选择的已启用智能体
        for slug in selected_slugs:
            agent = self._agents.get(slug)
            if agent and isinstance(agent, AnalystAgent):
                if self._is_agent_enabled(slug):
                    agents.append(agent)
                else:
                    logger.warning(f"智能体 {slug} 已被禁用，跳过")

        return agents

    def _is_agent_enabled(self, slug: str) -> bool:
        """检查智能体是否启用"""
        # 从配置中读取启用状态
        # 第一阶段智能体
        if slug.startswith("phase1_"):
            if self.config.phase1 and self.config.phase1.agents:
                for agent_cfg in self.config.phase1.agents:
                    if agent_cfg.slug == slug:
                        return agent_cfg.enabled
        # 第二阶段智能体
        elif slug.startswith("phase2_"):
            if self.config.phase2 and self.config.phase2.agents:
                for agent_cfg in self.config.phase2.agents:
                    if agent_cfg.slug == slug:
                        return agent_cfg.enabled
        # 第三阶段智能体
        elif slug.startswith("phase3_"):
            if self.config.phase3 and self.config.phase3.agents:
                for agent_cfg in self.config.phase3.agents:
                    if agent_cfg.slug == slug:
                        return agent_cfg.enabled
        # 第四阶段智能体
        elif slug.startswith("phase4_"):
            if self.config.phase4 and self.config.phase4.agents:
                for agent_cfg in self.config.phase4.agents:
                    if agent_cfg.slug == slug:
                        return agent_cfg.enabled

        # 默认启用
        return True

    def _apply_thinking_config(self, agent: BaseAgent, model_config: Dict[str, Any]) -> None:
        """
        将模型配置中的思考参数应用到智能体

        Args:
            agent: 智能体实例
            model_config: 模型配置字典
        """
        # 提取思考配置，优先使用任务参数，否则使用模型默认配置
        thinking_enabled = model_config.get("thinking_enabled", model_config.get("model_thinking_enabled", False))
        thinking_mode = model_config.get("thinking_mode") or model_config.get("model_thinking_mode")

        # 设置到agent
        agent.set_thinking_config(
            enabled=thinking_enabled,
            mode=thinking_mode,
        )

    async def _run_analyst(self, agent: AnalystAgent, state: AgentState) -> Dict[str, Any]:
        """
        运行单个分析师智能体

        Args:
            agent: 智能体实例
            state: 工作流状态

        Returns:
            分析师输出
        """
        # 执行前检查中断信号
        if not self._should_continue(state):
            logger.info(f"任务已中断，跳过智能体: {agent.slug}")
            return None

        try:
            report = await agent.execute(state)
            # 累加 token 使用量到工作流状态
            token_usage = agent.get_token_usage()
            state["total_token_usage"]["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
            state["total_token_usage"]["completion_tokens"] += token_usage.get("completion_tokens", 0)
            state["total_token_usage"]["total_tokens"] += token_usage.get("total_tokens", 0)
            return agent.to_analyst_output(report, state)
        except Exception as e:
            logger.error(f"分析师执行失败: {agent.slug}, error={e}")
            raise

    def _should_continue(self, state: AgentState) -> bool:
        """判断工作流是否应该继续"""
        return state.get("status") == "running" and not state.get("interrupt_signal", False)

    def _simple_summary(self, state: AgentState) -> str:
        """简单汇总报告"""
        summary_parts = []

        summary_parts.append(f"# {state['stock_code']} 股票分析报告\n")
        summary_parts.append(f"**分析日期**: {state['trade_date']}\n\n")

        # 分析师报告
        if state.get("analyst_reports"):
            summary_parts.append("## 分析师观点\n\n")
            for report in state["analyst_reports"]:
                summary_parts.append(f"### {report['agent_name']}\n")
                summary_parts.append(f"{report['content']}\n\n")

        # 交易计划
        if state.get("trade_plan"):
            summary_parts.append("## 交易计划\n\n")
            summary_parts.append(f"{state['trade_plan']}\n\n")

        # 风险评估
        if state.get("risk_assessment"):
            summary_parts.append("## 风险评估\n\n")
            summary_parts.append(f"{state['risk_assessment']}\n\n")

        return "".join(summary_parts)

    async def _send_event(self, task_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """
        发送 WebSocket 事件

        Args:
            task_id: 任务 ID
            event_type: 事件类型
            data: 事件数据
        """
        if self.ws_manager:
            await self.ws_manager.send_event(task_id, {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            })
