"""
LangGraph 工作流执行器

遵循 LangGraph 官方最佳实践：
- 使用 invoke 执行同步工作流
- 使用 stream 实现实时进度推送
- 使用 config["configurable"]["thread_id"] 标识任务
- 使用 checkpointer 实现持久化和恢复

官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#invoking-the-graph
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

from .state import (
    TradingAgentState,
    TradingAgentInputState,
    TradingAgentOutputState,
    create_initial_state,
    TaskStatus,
)
from .graph import create_trading_agent_graph

logger = logging.getLogger(__name__)


# =============================================================================
# 工作流执行器
# =============================================================================


class TradingAgentWorkflow:
    """
    TradingAgents 工作流执行器

    遵循官方最佳实践：
    - 封装图的执行逻辑
    - 使用 thread_id 标识任务
    - 使用 stream 实现实时进度推送
    - 支持从检查点恢复执行
    - **重要**: 支持动态加载用户配置创建 Phase 1 节点
    """

    def __init__(
        self,
        checkpointer_path: str = "data/trading_agents_checkpoints.db",
        websocket_manager=None,
        use_redis_checkpointer: bool = True,
    ):
        """
        初始化工作流执行器

        Args:
            checkpointer_path: 检查点数据库路径
            websocket_manager: WebSocket 管理器（用于实时推送）
            use_redis_checkpointer: 是否使用 Redis checkpointer
        """
        logger.info("[执行器] 初始化工作流执行器")

        self.checkpointer_path = checkpointer_path
        self.websocket_manager = websocket_manager
        self.use_redis_checkpointer = use_redis_checkpointer

        # 图缓存: {config_key: graph}
        # 避免为每个用户都重新创建图
        self._graph_cache: Dict[str, StateGraph] = {}

        # 保存最后一次使用的配置（用于 get_state）
        self._last_agent_config = None
        self._last_task_id = None

    def _get_graph(self, agent_config: Optional[Dict[str, Any]] = None) -> StateGraph:
        """
        获取或创建工作流图

        **重要修改**: 根据 agent_config 动态创建图，支持用户自定义 Phase 1 智能体

        Args:
            agent_config: 智能体配置（从用户配置加载，可以是字典或 Pydantic 对象）

        Returns:
            StateGraph 实例
        """
        # 如果没有配置，使用默认配置
        if agent_config is None:
            from modules.trading_agents.config.loader import load_default_config

            agent_config = load_default_config()

        # 处理字典类型的配置
        if isinstance(agent_config, dict):
            phase1_agents = agent_config.get("phase1", {}).get("agents", [])
        else:
            # Pydantic 对象
            phase1_agents = agent_config.phase1.agents if agent_config else []

        # 生成配置缓存键（基于 phase1 agents 的 slug 列表）
        enabled_slugs = []
        for a in phase1_agents:
            if isinstance(a, dict):
                if a.get("enabled"):
                    enabled_slugs.append(a.get("slug"))
            else:
                if a.enabled:
                    enabled_slugs.append(a.slug)
        config_key = ":".join(sorted(enabled_slugs))

        # 检查缓存
        if config_key in self._graph_cache:
            logger.debug(f"[执行器] 使用缓存的图: {config_key}")
            return self._graph_cache[config_key]

        # 创建新图
        logger.info(f"[执行器] 创建新图: {config_key}")
        graph = create_trading_agent_graph(
            checkpointer_path=self.checkpointer_path,
            use_redis_checkpointer=self.use_redis_checkpointer,
            agent_config=agent_config,
        )

        # 缓存图
        self._graph_cache[config_key] = graph

        return graph

    async def run(
        self, input_state: TradingAgentInputState, config: Optional[Dict[str, Any]] = None
    ) -> TradingAgentOutputState:
        """
        运行工作流

        遵循官方最佳实践：
        - 使用 ainvoke 执行异步工作流
        - 使用 config["configurable"]["thread_id"] 标识任务
        - 使用 astream 实现实时进度推送
        - **重要**: 根据用户配置动态创建图

        官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#invoking-the-graph

        Args:
            input_state: 输入状态（包含 agent_config）
            config: 额外配置

        Returns:
            输出状态
        """
        task_id = input_state.get("task_id", "unknown")
        logger.info(f"[执行器] 开始运行任务: {task_id}")

        # **关键修改**: 从 input_state 中获取 agent_config
        agent_config = input_state.get("agent_config")

        # 保存配置供 get_state 使用
        self._last_agent_config = agent_config
        self._last_task_id = task_id

        # 获取或创建工作流图（根据用户配置）
        graph = self._get_graph(agent_config)

        # 准备运行时配置（官方模式）
        # thread_id 用于标识会话，支持持久化和恢复
        runnable_config = {
            "configurable": {
                "thread_id": task_id  # 官方模式：使用 thread_id 标识会话
            },
            "metadata": {
                "task_id": task_id,
                "user_id": input_state.get("user_id"),
                "stock_code": input_state.get("stock_code"),
            },
        }

        if config:
            runnable_config.update(config)

        # 转换输入状态为内部状态
        initial_state = self._convert_input_to_internal_state(input_state)

        try:
            # 使用 stream 实现实时进度推送（官方模式）
            # 参考: https://docs.langchain.com/oss/python/langgraph/graph-api/#streaming
            if self.websocket_manager:
                logger.debug(f"[执行器] 启用实时进度推送: {task_id}")

                final_state = None
                async for event in graph.astream(initial_state, runnable_config):
                    # event 格式: {node_name: state_update}
                    logger.debug(f"[执行器] 事件: {list(event.keys())}")

                    # 推送进度到前端
                    for node_name, state_update in event.items():
                        await self._broadcast_progress(task_id, node_name, state_update)

                    # 保存最终状态
                    final_state = event

                # 构建输出状态
                if final_state:
                    output_state = self._extract_output_from_state(final_state)
                else:
                    # 如果没有 final_state，重新获取
                    final_state = await graph.aget_state(runnable_config)
                    output_state = self._extract_output_from_state(final_state)

            else:
                # 不使用 stream，直接 invoke（更简单）
                logger.debug(f"[执行器] 直接 invoke（无进度推送）: {task_id}")
                logger.debug(f"[执行器] initial_state 类型: {type(initial_state)}")
                logger.debug(
                    f"[执行器] initial_state keys: {initial_state.keys() if isinstance(initial_state, dict) else 'N/A'}"
                )
                logger.debug(f"[执行器] runnable_config: {runnable_config}")

                logger.info(f"[执行器] 🚀 调用 graph.ainvoke() 开始...")
                try:
                    final_state = await asyncio.wait_for(
                        graph.ainvoke(initial_state, runnable_config),
                        timeout=1800  # 30分钟超时
                    )
                    logger.info(f"[执行器] ✅ graph.ainvoke() 完成，返回状态类型: {type(final_state)}")
                except asyncio.TimeoutError:
                    logger.error(f"[执行器] ❌ graph.ainvoke() 超时（10分钟）")
                    raise TimeoutError("工作流执行超时")

                # 详细日志：检查所有状态字段
                logger.info(f"[执行器] ===== 完整状态检查 =====")
                logger.info(f"[执行器] final_state 所有字段: {list(final_state.keys()) if isinstance(final_state, dict) else 'Not a dict'}")

                # **关键修复**：ainvoke 返回的状态不完整，需要使用 aget_state 获取完整状态
                logger.info(f"[执行器] 使用 aget_state 获取完整状态...")
                state_snapshot = await graph.aget_state(runnable_config)

                if state_snapshot and hasattr(state_snapshot, 'values'):
                    # StateSnapshot.values 是一个属性
                    output_state = state_snapshot.values if isinstance(state_snapshot.values, dict) else dict(state_snapshot.values)
                    logger.info(f"[执行器] 从 StateSnapshot 提取状态，字段数: {len(output_state)}")
                else:
                    logger.warning(f"[执行器] aget_state 返回 None 或无 values，使用 ainvoke 返回值")
                    output_state = final_state

                logger.info(f"[执行器] 最终状态字段: {list(output_state.keys())}")

                # 检查关键累积字段
                for field in ['analyst_reports', 'token_usage', 'completed_analysts', 'debate_turns', 'risk_assessments']:
                    value = output_state.get(field, 'MISSING')
                    if isinstance(value, list):
                        logger.info(f"[执行器] {field}: {len(value)} 条")
                    else:
                        logger.info(f"[执行器] {field}: {value}")

                logger.info(f"[执行器] ===== 状态检查结束 =====")

            logger.info(f"[执行器] 任务完成: {task_id}")

            return output_state

        except Exception as e:
            logger.error(f"[执行器] ❌ 任务执行失败: {task_id}")
            logger.error(f"[执行器] 错误类型: {type(e).__name__}")
            logger.error(f"[执行器] 错误信息: {str(e)}")
            import traceback

            logger.error(f"[执行器] 堆栈跟踪:\n{traceback.format_exc()}")
            raise

    async def stream(
        self, input_state: TradingAgentInputState, config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行工作流（生成器模式）

        遵循官方最佳实践：使用 astream 逐步输出事件

        Args:
            input_state: 输入状态
            config: 额外配置

        Yields:
            事件字典 {node_name: state_update}
        """
        task_id = input_state.get("task_id", "unknown")
        logger.info(f"[执行器] 开始流式执行任务: {task_id}")

        # 准备运行时配置
        runnable_config = {
            "configurable": {"thread_id": task_id},
            "metadata": {
                "task_id": task_id,
                "user_id": input_state.get("user_id"),
                "stock_code": input_state.get("stock_code"),
            },
        }

        if config:
            runnable_config.update(config)

        # 转换输入状态
        initial_state = self._convert_input_to_internal_state(input_state)

        try:
            # 使用 astream 流式输出事件
            async for event in self.graph.astream(initial_state, runnable_config):
                yield event

            logger.info(f"[执行器] 流式执行完成: {task_id}")

        except Exception as e:
            logger.error(f"[执行器] 流式执行失败: {task_id}, 错误: {e}")
            raise

    async def resume(
        self, task_id: str, config: Optional[Dict[str, Any]] = None
    ) -> TradingAgentOutputState:
        """
        从检查点恢复执行（官方模式）

        使用场景：
        - 系统重启后恢复任务
        - 从中断点继续执行

        官方文档: https://docs.langchain.com/oss/python/langgraph/how-tos/persistence/

        Args:
            task_id: 任务 ID（thread_id）
            config: 额外配置

        Returns:
            输出状态
        """
        logger.info(f"[执行器] 从检查点恢复任务: {task_id}")

        # 准备运行时配置
        runnable_config = {"configurable": {"thread_id": task_id}}

        if config:
            runnable_config.update(config)

        try:
            # 官方模式：传入 None 作为输入，从检查点恢复
            # 参考: https://docs.langchain.com/oss/python/langgraph/how-tos/persistence/#resuming
            final_state = await self.graph.ainvoke(None, runnable_config)
            output_state = self._extract_output_from_state(final_state)

            logger.info(f"[执行器] 任务恢复完成: {task_id}")

            return output_state

        except Exception as e:
            logger.error(f"[执行器] 任务恢复失败: {task_id}, 错误: {e}")
            raise

    async def get_state(
        self, task_id: str, config: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingAgentState]:
        """
        获取任务的当前状态（不从检查点恢复，只查询）

        Args:
            task_id: 任务 ID
            config: 额外配置

        Returns:
            当前状态，如果任务不存在则返回 None
        """
        logger.debug(f"[执行器] 查询任务状态: {task_id}")

        # 使用最后一次使用的 agent_config 获取 graph
        graph = self._get_graph(self._last_agent_config)

        runnable_config = {"configurable": {"thread_id": task_id}}

        if config:
            runnable_config.update(config)

        try:
            state_snapshot = await graph.aget_state(runnable_config)
            return state_snapshot.values if state_snapshot else None

        except Exception as e:
            logger.warning(f"[执行器] 查询任务状态失败: {task_id}, 错误: {e}")
            return None

    async def cancel(self, task_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        取消正在运行的任务

        Args:
            task_id: 任务 ID
            config: 额外配置

        Returns:
            是否成功取消
        """
        logger.info(f"[执行器] 取消任务: {task_id}")

        # LangGraph 本身不支持直接中断
        # 需要通过状态检查实现软中断
        # 这里我们通过更新状态来实现

        try:
            runnable_config = {"configurable": {"thread_id": task_id}}

            if config:
                runnable_config.update(config)

            # 获取当前状态
            state_snapshot = await self.graph.aget_state(runnable_config)

            if state_snapshot and state_snapshot.values:
                # 更新状态为已取消
                # 注意：这不会停止正在运行的节点，但可以阻止下一个节点执行
                # 完整的中断需要使用 LangGraph 的 interrupt 机制
                updated_state = state_snapshot.values.copy()
                updated_state["status"] = TaskStatus.CANCELLED.value
                updated_state["interrupt_signal"] = True
                updated_state["end_time"] = datetime.now().isoformat()

                # 更新状态（通过重新 invoke）
                # 注意：这种方法不是完美的，更好的方式是使用 interrupt
                await self.graph.ainvoke(updated_state, runnable_config)

                logger.info(f"[执行器] 任务已取消: {task_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"[执行器] 取消任务失败: {task_id}, 错误: {e}")
            return False

    # =============================================================================
    # 辅助方法
    # =============================================================================

    def _convert_input_to_internal_state(
        self, input_state: TradingAgentInputState
    ) -> TradingAgentState:
        """
        转换输入状态为内部状态

        Args:
            input_state: 输入状态

        Returns:
            内部状态
        """
        # 使用辅助函数创建初始状态
        return create_initial_state(
            task_id=input_state.get("task_id", ""),
            user_id=input_state.get("user_id", ""),
            stock_code=input_state.get("stock_code", ""),
            trade_date=input_state.get("trade_date", ""),
            max_debate_rounds=input_state.get("max_debate_rounds", 2),
            phase2_concurrency=input_state.get("phase2_concurrency", 1),
            phase3_concurrency=input_state.get("phase3_concurrency", 3),
            enable_phase1=input_state.get("enable_phase1", True),
            enable_phase2=input_state.get("enable_phase2", True),
            enable_phase3=input_state.get("enable_phase3", True),
            enable_phase4=input_state.get("enable_phase4", True),
            model_config=input_state.get("model_config"),
            agent_config=input_state.get("agent_config"),
        )

    def _extract_output_from_state(self, state: TradingAgentState) -> TradingAgentOutputState:
        """
        从内部状态提取输出状态

        Args:
            state: 内部状态

        Returns:
            输出状态
        """
        # 计算总 Token 使用量
        total_tokens = {}
        for usage in state.get("token_usage", []):
            tokens = usage.get("tokens", {})
            for key, value in tokens.items():
                total_tokens[key] = total_tokens.get(key, 0) + value

        # 获取最终报告
        final_report = state.get("final_report")
        recommendation = final_report.get("recommendation") if final_report else None

        return {
            "task_id": state.get("task_id", ""),
            "user_id": state.get("user_id", ""),
            "stock_code": state.get("stock_code", ""),
            "status": state.get("status", ""),
            "final_report": final_report,
            "recommendation": recommendation,
            "token_usage": total_tokens,
            "start_time": state.get("start_time", ""),
            "end_time": state.get("end_time"),
        }

    async def _broadcast_progress(
        self, task_id: str, node_name: str, state_update: Dict[str, Any]
    ) -> None:
        """
        广播进度到 WebSocket

        Args:
            task_id: 任务 ID
            node_name: 节点名称
            state_update: 状态更新
        """
        if not self.websocket_manager:
            return

        try:
            # 提取有用的进度信息
            progress_data = {
                "task_id": task_id,
                "node": node_name,
                "timestamp": datetime.now().isoformat(),
                "current_phase": state_update.get("current_phase"),
                "status": state_update.get("status"),
            }

            # 添加特定节点的信息
            if "analyst_reports" in state_update:
                progress_data["analyst_reports_count"] = len(
                    state_update.get("analyst_reports", [])
                )
            if "debate_turns" in state_update:
                progress_data["debate_round"] = len(state_update.get("debate_turns", []))
            if "risk_assessments" in state_update:
                progress_data["risk_assessments_count"] = len(
                    state_update.get("risk_assessments", [])
                )
            if "final_report" in state_update:
                progress_data["final_report_ready"] = True

            # ===== 新增：推送 agent_messages =====
            # 从 state_update 中获取 agent_messages
            agent_messages = state_update.get("agent_messages", [])
            if agent_messages:
                progress_data["agent_messages"] = agent_messages[-5:]  # 只推送最近 5 条消息

            # 广播到前端
            await self.websocket_manager.broadcast(progress_data)

            logger.debug(f"[执行器] 广播进度: {progress_data}")

        except Exception as e:
            logger.warning(f"[执行器] 广播进度失败: {e}")


# =============================================================================
# 工厂函数
# =============================================================================


def create_workflow_executor(
    checkpointer_path: str = "data/trading_agents_checkpoints.db", websocket_manager=None
) -> TradingAgentWorkflow:
    """
    创建工作流执行器

    Args:
        checkpointer_path: 检查点数据库路径
        websocket_manager: WebSocket 管理器

    Returns:
        TradingAgentWorkflow 实例
    """
    return TradingAgentWorkflow(
        checkpointer_path=checkpointer_path, websocket_manager=websocket_manager
    )
