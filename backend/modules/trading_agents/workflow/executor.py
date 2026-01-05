"""
LangGraph 工作流执行器

遵循 LangGraph 官方最佳实践：
- 使用 invoke 执行同步工作流
- 使用 stream 实现实时进度推送
- 使用 config["configurable"]["thread_id"] 标识任务
- 使用 checkpointer 实现持久化和恢复

官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#invoking-the-graph
"""

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
    TaskStatus
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
    """

    def __init__(
        self,
        checkpointer_path: str = "data/trading_agents_checkpoints.db",
        websocket_manager = None
    ):
        """
        初始化工作流执行器

        Args:
            checkpointer_path: 检查点数据库路径
            websocket_manager: WebSocket 管理器（用于实时推送）
        """
        logger.info("[执行器] 初始化工作流执行器")

        # 创建工作流图
        self.graph = create_trading_agent_graph(checkpointer_path)
        self.websocket_manager = websocket_manager

    async def run(
        self,
        input_state: TradingAgentInputState,
        config: Optional[Dict[str, Any]] = None
    ) -> TradingAgentOutputState:
        """
        运行工作流

        遵循官方最佳实践：
        - 使用 ainvoke 执行异步工作流
        - 使用 config["configurable"]["thread_id"] 标识任务
        - 使用 astream 实现实时进度推送

        官方文档: https://docs.langchain.com/oss/python/langgraph/graph-api/#invoking-the-graph

        Args:
            input_state: 输入状态
            config: 额外配置

        Returns:
            输出状态
        """
        task_id = input_state.get("task_id", "unknown")
        logger.info(f"[执行器] 开始运行任务: {task_id}")

        # 准备运行时配置（官方模式）
        # thread_id 用于标识会话，支持持久化和恢复
        runnable_config = {
            "configurable": {
                "thread_id": task_id  # 官方模式：使用 thread_id 标识会话
            },
            "metadata": {
                "task_id": task_id,
                "user_id": input_state.get("user_id"),
                "stock_code": input_state.get("stock_code")
            }
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
                async for event in self.graph.astream(initial_state, runnable_config):
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
                    final_state = await self.graph.aget_state(runnable_config)
                    output_state = self._extract_output_from_state(final_state)

            else:
                # 不使用 stream，直接 invoke（更简单）
                logger.debug(f"[执行器] 直接 invoke（无进度推送）: {task_id}")

                final_state = await self.graph.ainvoke(initial_state, runnable_config)
                output_state = self._extract_output_from_state(final_state)

            logger.info(f"[执行器] 任务完成: {task_id}, 状态: {output_state.get('status')}")

            return output_state

        except Exception as e:
            logger.error(f"[执行器] 任务执行失败: {task_id}, 错误: {e}")
            raise

    async def stream(
        self,
        input_state: TradingAgentInputState,
        config: Optional[Dict[str, Any]] = None
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
            "configurable": {
                "thread_id": task_id
            },
            "metadata": {
                "task_id": task_id,
                "user_id": input_state.get("user_id"),
                "stock_code": input_state.get("stock_code")
            }
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
        self,
        task_id: str,
        config: Optional[Dict[str, Any]] = None
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
        runnable_config = {
            "configurable": {
                "thread_id": task_id
            }
        }

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
        self,
        task_id: str,
        config: Optional[Dict[str, Any]] = None
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

        runnable_config = {
            "configurable": {
                "thread_id": task_id
            }
        }

        if config:
            runnable_config.update(config)

        try:
            state_snapshot = await self.graph.aget_state(runnable_config)
            return state_snapshot.values if state_snapshot else None

        except Exception as e:
            logger.warning(f"[执行器] 查询任务状态失败: {task_id}, 错误: {e}")
            return None

    async def cancel(
        self,
        task_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
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
            runnable_config = {
                "configurable": {
                    "thread_id": task_id
                }
            }

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
        self,
        input_state: TradingAgentInputState
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
            enable_phase1=input_state.get("enable_phase1", True),
            enable_phase2=input_state.get("enable_phase2", True),
            enable_phase3=input_state.get("enable_phase3", True),
            enable_phase4=input_state.get("enable_phase4", True),
            model_config=input_state.get("model_config"),
            agent_config=input_state.get("agent_config"),
        )

    def _extract_output_from_state(
        self,
        state: TradingAgentState
    ) -> TradingAgentOutputState:
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
        self,
        task_id: str,
        node_name: str,
        state_update: Dict[str, Any]
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
                progress_data["analyst_reports_count"] = len(state_update.get("analyst_reports", []))
            if "debate_turns" in state_update:
                progress_data["debate_round"] = len(state_update.get("debate_turns", []))
            if "risk_assessments" in state_update:
                progress_data["risk_assessments_count"] = len(state_update.get("risk_assessments", []))
            if "final_report" in state_update:
                progress_data["final_report_ready"] = True

            # 广播到前端
            await self.websocket_manager.broadcast(progress_data)

            logger.debug(f"[执行器] 广播进度: {progress_data}")

        except Exception as e:
            logger.warning(f"[执行器] 广播进度失败: {e}")


# =============================================================================
# 工厂函数
# =============================================================================

def create_workflow_executor(
    checkpointer_path: str = "data/trading_agents_checkpoints.db",
    websocket_manager = None
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
        checkpointer_path=checkpointer_path,
        websocket_manager=websocket_manager
    )
