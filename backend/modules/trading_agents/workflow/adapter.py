"""
LangGraph 工作流适配器

将新的 LangGraph 工作流适配到现有的 TaskManager 接口

适配器职责：
1. 转换现有的数据结构为 LangGraph 格式
2. 调用 LangGraph 工作流执行器
3. 转换 LangGraph 输出为现有格式
4. 保持接口兼容性
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from modules.trading_agents.workflow import (
    TradingAgentWorkflow,
    create_initial_state,
    TradingAgentInputState,
    TradingAgentOutputState,
)
from modules.trading_agents.websocket import get_ws_manager
from modules.trading_agents.schemas import AnalysisTaskCreate

logger = logging.getLogger(__name__)


# =============================================================================
# 工作流适配器
# =============================================================================

class LangGraphWorkflowAdapter:
    """
    LangGraph 工作流适配器

    将 LangGraph 工作流适配到现有 TaskManager 接口
    """

    def __init__(self):
        """初始化适配器"""
        logger.info("[适配器] 初始化 LangGraph 工作流适配器")

        # 获取 WebSocket 管理器
        ws_manager = get_ws_manager()

        # 创建工作流执行器
        self.executor = TradingAgentWorkflow(
            checkpointer_path="data/trading_agents_checkpoints.db",
            websocket_manager=ws_manager
        )

    async def execute_task(
        self,
        task_id: str,
        user_id: str,
        request: AnalysisTaskCreate,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行分析任务

        将现有格式的请求转换为 LangGraph 格式，执行工作流，然后转换回现有格式

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            request: 分析任务请求（现有格式）
            config: 智能体配置

        Returns:
            任务结果（现有格式）
        """
        logger.info(f"[适配器] 执行任务: task_id={task_id}, user_id={user_id}, stock={request.stock_code}")

        try:
            # 转换请求格式：现有格式 -> LangGraph 格式
            input_state = self._convert_request_to_input_state(
                task_id=task_id,
                user_id=user_id,
                request=request,
                config=config
            )

            # 执行 LangGraph 工作流
            output_state = await self.executor.run(input_state)

            # 转换输出格式：LangGraph 格式 -> 现有格式
            result = self._convert_output_to_result(
                task_id=task_id,
                output_state=output_state,
                request=request
            )

            logger.info(f"[适配器] 任务完成: task_id={task_id}, status={result.get('status')}")

            return result

        except Exception as e:
            logger.error(f"[适配器] 任务执行失败: task_id={task_id}, 错误: {e}")
            raise

    async def resume_task(
        self,
        task_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        从检查点恢复任务

        Args:
            task_id: 任务 ID
            user_id: 用户 ID

        Returns:
            任务结果
        """
        logger.info(f"[适配器] 恢复任务: task_id={task_id}, user_id={user_id}")

        try:
            # 调用 LangGraph 执行器的 resume 方法
            output_state = await self.executor.resume(task_id)

            # 转换输出格式
            result = self._convert_output_to_result(
                task_id=task_id,
                output_state=output_state,
                request=None  # 恢复时不需要请求
            )

            logger.info(f"[适配器] 任务恢复完成: task_id={task_id}")

            return result

        except Exception as e:
            logger.error(f"[适配器] 任务恢复失败: task_id={task_id}, 错误: {e}")
            raise

    async def get_task_state(
        self,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取任务的当前状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态，如果任务不存在则返回 None
        """
        logger.debug(f"[适配器] 查询任务状态: task_id={task_id}")

        try:
            state = await self.executor.get_state(task_id)

            if state:
                # 转换为现有格式
                return self._convert_state_to_dict(state)

            return None

        except Exception as e:
            logger.warning(f"[适配器] 查询任务状态失败: task_id={task_id}, 错误: {e}")
            return None

    async def cancel_task(
        self,
        task_id: str
    ) -> bool:
        """
        取消正在运行的任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        logger.info(f"[适配器] 取消任务: task_id={task_id}")

        try:
            success = await self.executor.cancel(task_id)
            return success

        except Exception as e:
            logger.error(f"[适配器] 取消任务失败: task_id={task_id}, 错误: {e}")
            return False

    # =============================================================================
    # 转换方法
    # =============================================================================

    def _convert_request_to_input_state(
        self,
        task_id: str,
        user_id: str,
        request: AnalysisTaskCreate,
        config: Dict[str, Any]
    ) -> TradingAgentInputState:
        """
        转换请求格式：现有格式 -> LangGraph 格式

        Args:
            task_id: 任务 ID
            user_id: 用户 ID
            request: 分析任务请求（现有格式）
            config: 智能体配置

        Returns:
            LangGraph 输入状态
        """
        # 从 stages 配置中提取各阶段开关
        stages = request.stages or {}
        phase1_enabled = stages.get("phase1", {}).get("enabled", True)
        phase2_enabled = stages.get("phase2", {}).get("enabled", True)
        phase3_enabled = stages.get("phase3", {}).get("enabled", True)
        phase4_enabled = stages.get("phase4", {}).get("enabled", True)

        # 构建模型配置
        model_config = {
            "data_collection_model": request.data_collection_model,
            "debate_model": request.debate_model,
        }

        # 构建智能体配置
        agent_config = config.get("agent_config", {})

        return {
            "user_id": user_id,
            "stock_code": request.stock_code,
            "trade_date": request.trade_date,
            "task_id": task_id,
            "max_debate_rounds": stages.get("phase2", {}).get("max_rounds", 2),
            "enable_phase1": phase1_enabled,
            "enable_phase2": phase2_enabled,
            "enable_phase3": phase3_enabled,
            "enable_phase4": phase4_enabled,
            "model_config": model_config,
            "agent_config": agent_config,
        }

    def _convert_output_to_result(
        self,
        task_id: str,
        output_state: TradingAgentOutputState,
        request: Optional[AnalysisTaskCreate]
    ) -> Dict[str, Any]:
        """
        转换输出格式：LangGraph 格式 -> 现有格式

        Args:
            task_id: 任务 ID
            output_state: LangGraph 输出状态
            request: 原始请求（可选）

        Returns:
            任务结果（现有格式）
        """
        final_report = output_state.get("final_report", {})

        return {
            "task_id": task_id,
            "user_id": output_state.get("user_id"),
            "stock_code": output_state.get("stock_code"),
            "status": output_state.get("status"),
            "final_recommendation": output_state.get("recommendation"),
            "final_report": final_report.get("content") if final_report else None,
            "token_usage": output_state.get("token_usage", {}),
            "start_time": output_state.get("start_time"),
            "end_time": output_state.get("end_time"),
        }

    def _convert_state_to_dict(
        self,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        转换状态为字典

        Args:
            state: LangGraph 状态

        Returns:
            状态字典
        """
        return {
            "task_id": state.get("task_id"),
            "user_id": state.get("user_id"),
            "stock_code": state.get("stock_code"),
            "status": state.get("status"),
            "current_phase": state.get("current_phase"),
            "progress": self._calculate_progress(state),
            "analyst_reports_count": len(state.get("analyst_reports", [])),
            "debate_rounds": len(state.get("debate_turns", [])),
            "risk_assessments_count": len(state.get("risk_assessments", [])),
            "has_final_report": state.get("final_report") is not None,
            "start_time": state.get("start_time"),
            "end_time": state.get("end_time"),
        }

    def _calculate_progress(self, state: Dict[str, Any]) -> float:
        """
        计算任务进度

        Args:
            state: 工作流状态

        Returns:
            进度百分比 (0-100)
        """
        current_phase = state.get("current_phase", "pending")

        # 基于阶段估算进度
        phase_progress = {
            "pending": 0.0,
            "phase1": 25.0,
            "phase2": 50.0,
            "phase3": 75.0,
            "phase4": 90.0,
            "completed": 100.0,
        }

        base_progress = phase_progress.get(current_phase, 0.0)

        # 在阶段内根据完成情况微调
        if current_phase == "phase1":
            completed = state.get("completed_analysts", 0)
            expected = state.get("expected_analysts", 4)
            if expected > 0:
                base_progress += (completed / expected) * 0.25  # 0-25% 范围

        elif current_phase == "phase2":
            rounds = len(state.get("debate_turns", []))
            max_rounds = state.get("max_debate_rounds", 2)
            if max_rounds > 0:
                base_progress += (rounds / max_rounds) * 0.25  # 50-75% 范围

        elif current_phase == "phase3":
            assessments = len(state.get("risk_assessments", []))
            base_progress += (assessments / 3) * 0.15  # 75-90% 范围

        return min(base_progress, 100.0)


# =============================================================================
# 单例实例
# =============================================================================

_adapter_instance: Optional[LangGraphWorkflowAdapter] = None


def get_langgraph_adapter() -> LangGraphWorkflowAdapter:
    """
    获取 LangGraph 适配器单例

    Returns:
        LangGraphWorkflowAdapter 实例
    """
    global _adapter_instance

    if _adapter_instance is None:
        _adapter_instance = LangGraphWorkflowAdapter()

    return _adapter_instance
