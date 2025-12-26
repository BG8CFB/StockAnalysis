"""
智能体工作流引擎

使用 LangGraph 编排四阶段股票分析工作流。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from modules.trading_agents.core.state import AgentState, create_initial_state
from modules.trading_agents.agents.base import BaseAgent, AnalystAgent
from modules.trading_agents.agents.phase1.analysts import AnalystFactory
from modules.trading_agents.agents.phase2 import create_phase2_agents
from modules.trading_agents.agents.phase3 import create_phase3_agents
from modules.trading_agents.agents.phase4 import create_phase4_agents
from modules.trading_agents.llm.provider import LLMProvider
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
    ):
        """
        初始化工作流引擎

        Args:
            llm: LLM Provider
            config: 用户智能体配置
            ws_manager: WebSocket 管理器（用于实时推送）
        """
        self.llm = llm
        self.config = config
        self.ws_manager = ws_manager  # 如果为None，调用者负责处理

        # 并发控制器
        self.concurrency = get_concurrency_manager()
        
        # 工具注册表
        self.tool_registry = ToolRegistry()

        # 阶段配置
        self.phase1_enabled = config.phase1.enabled
        self.phase2_enabled = config.phase2.enabled if config.phase2 else False
        self.phase3_enabled = config.phase3.enabled if config.phase3 else False
        self.phase4_enabled = config.phase4.enabled if config.phase4 else False

        # 智能体映射
        self._agents: Dict[str, BaseAgent] = {}
        
        # 初始化所有智能体
        self._initialize_agents()

    def _initialize_agents(self):
        """初始化并注册所有阶段的智能体"""
        # Phase 1: 使用工厂动态创建
        if self.config.phase1:
            factory = AnalystFactory(self.llm, self.tool_registry)
            analysts = factory.create_analysts(self.config.phase1)
            for agent in analysts:
                self.register_agent(agent)
                
        # Phase 2: 研究员辩论
        if self.config.phase2:
            phase2_agents = create_phase2_agents(self.llm)
            for agent in phase2_agents:
                self.register_agent(agent)
                
        # Phase 3: 风险评估
        if self.config.phase3:
            phase3_agents = create_phase3_agents(self.llm)
            for agent in phase3_agents:
                self.register_agent(agent)
                
        # Phase 4: 总结
        if self.config.phase4:
            phase4_agents = create_phase4_agents(self.llm)
            for agent in phase4_agents:
                self.register_agent(agent)
        """
        注册智能体

        Args:
            agent: 智能体实例
        """
        self._agents[agent.slug] = agent
        logger.info(f"注册智能体: {agent.slug}")

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
            request: 分析任务请求

        Returns:
            最终报告和元数据
        """
        # 1. 创建初始状态
        max_debate_rounds = self.config.phase2.max_rounds if self.config.phase2 else 2
        state = create_initial_state(
            task_id=task_id,
            user_id=user_id,
            stock_code=request.stock_code,
            trade_date=request.trade_date,
            max_debate_rounds=max_debate_rounds,
            expected_analysts=len(self._get_phase1_agents()),
        )

        logger.info(f"开始工作流执行: task_id={task_id}, stock={request.stock_code}")

        # 发送开始事件
        await self._send_event(task_id, "workflow_started", {
            "stock_code": request.stock_code,
            "phase1_enabled": self.phase1_enabled,
            "phase2_enabled": self.phase2_enabled,
            "phase3_enabled": self.phase3_enabled,
            "phase4_enabled": self.phase4_enabled,
        })

        try:
            # ====================================================================
            # 阶段 1：分析师团队（并行执行）
            # ====================================================================
            if self.phase1_enabled:
                await self._execute_phase1(state)
            else:
                logger.info(f"阶段1已禁用，跳过: task_id={task_id}")

            # ====================================================================
            # 阶段 2：研究员辩论
            # ====================================================================
            if self.phase2_enabled and self._should_continue(state):
                await self._execute_phase2(state)
            else:
                logger.info(f"阶段2已禁用或跳过: task_id={task_id}")

            # ====================================================================
            # 阶段 3：风险评估
            # ====================================================================
            if self.phase3_enabled and self._should_continue(state):
                await self._execute_phase3(state)
            else:
                logger.info(f"阶段3已禁用或跳过: task_id={task_id}")

            # ====================================================================
            # 阶段 4：总结输出
            # ====================================================================
            if self.phase4_enabled and self._should_continue(state):
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

    async def _execute_phase1(self, state: AgentState) -> None:
        """
        执行阶段1：分析师团队

        并行调用所有启用的分析师智能体。
        """
        phase1_agents = self._get_phase1_agents()

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

    async def _execute_phase2(self, state: AgentState) -> None:
        """
        执行阶段2：研究员辩论

        实现看涨/看跌研究员之间的多轮辩论。
        使用 DebateManager 管理辩论流程。
        """
        max_rounds = state["max_debate_rounds"]
        logger.info(f"开始阶段2: 最多{max_rounds}轮辩论")

        await self._send_event(state["task_id"], "phase2_started", {
            "max_rounds": max_rounds,
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

        # 使用 DebateManager 运行辩论
        from ..agents.phase2.debate_manager import DebateManager

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

        # 累加辩论智能体的 token 使用量
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

    async def _execute_phase3(self, state: AgentState) -> None:
        """
        执行阶段3：风险评估

        多派别风险讨论 + CRO 总结
        """
        logger.info("开始阶段3: 风险评估")

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

    def _get_phase1_agents(self) -> List[AnalystAgent]:
        """获取阶段1启用的分析师智能体"""
        agents = []
        for slug, agent in self._agents.items():
            if slug.startswith("phase1_") and isinstance(agent, AnalystAgent):
                # 检查是否启用（从配置中读取）
                if self._is_agent_enabled(slug):
                    agents.append(agent)
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
