# -*- coding: utf-8 -*-
"""
LangChain 回调处理器 - 用于推送工具调用事件到前端

这个模块提供了一个自定义的 LangChain 回调处理器，可以在智能体执行过程中
实时推送工具调用和工具结果到前端。
使用 AsyncCallbackHandler 以在 ainvoke 时被正确调用。
"""
import logging
from typing import Any, Dict
from uuid import UUID

from langchain_core.callbacks.base import AsyncCallbackHandler

logger = logging.getLogger(__name__)


class WebSocketCallbackHandler(AsyncCallbackHandler):
    """
    WebSocket 回调处理器 - 用于推送工具调用事件

    在智能体执行过程中，会触发以下事件：
    - tool_called: 工具被调用时
    - tool_result: 工具执行结果返回时
    """

    def __init__(
        self,
        task_id: str,
        agent_slug: str,
        agent_name: str,
        websocket_manager: Any = None,
    ):
        """
        初始化回调处理器

        Args:
            task_id: 任务 ID
            agent_slug: 智能体 slug
            agent_name: 智能体名称
            websocket_manager: WebSocket 管理器实例
        """
        self.task_id = task_id
        self.agent_slug = agent_slug
        self.agent_name = agent_name
        self.websocket_manager = websocket_manager
        self._tool_call_count = 0
        # 工具循环检测器
        from modules.trading_agents.tools.loop_detector import get_loop_detector

        self._loop_detector = get_loop_detector()

    async def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """
        工具开始调用时触发

        Args:
            serialized: 工具的序列化信息
            input_str: 工具输入
        """
        self._tool_call_count += 1
        tool_name = serialized.get("name", serialized.get("kwargs", {}).get("name", "unknown"))

        # 循环检测：记录本次调用并检查是否触发循环
        if self._loop_detector:
            result = self._loop_detector.record_call(
                task_id=self.task_id,
                agent_slug=self.agent_slug,
                tool_name=tool_name,
                tool_input=input_str,
            )
            if result.is_loop:
                logger.warning(f"[WebSocketCallback] 工具循环 detected: {result.message}")
                # 推送 tool_disabled 事件
                if self.websocket_manager:
                    try:
                        from modules.trading_agents.workflow.events import (
                            create_tool_disabled_event,
                        )

                        event = create_tool_disabled_event(
                            task_id=self.task_id,
                            agent_slug=self.agent_slug,
                            tool_name=tool_name,
                            reason=result.message,
                        )
                        await self.websocket_manager.broadcast_event(self.task_id, event)
                    except Exception as e:
                        logger.error(f"推送 tool_disabled 事件失败: {e}")
                # 循环检测触发后仍继续推送 tool_called，让前端知晓调用发生

        # 检查工具是否已被禁用（同一任务中后续调用跳过）
        if self._loop_detector and self._loop_detector.is_tool_disabled(
            self.task_id, tool_name, self.agent_slug
        ):
            logger.warning(
                f"[WebSocketCallback] 工具已被禁用，跳过调用: "
                f"task={self.task_id}, tool={tool_name}"
            )
            # 推送 tool_disabled 提醒事件
            if self.websocket_manager:
                try:
                    from modules.trading_agents.workflow.events import create_tool_disabled_event

                    event = create_tool_disabled_event(
                        task_id=self.task_id,
                        agent_slug=self.agent_slug,
                        tool_name=tool_name,
                        reason=f"工具 {tool_name} 因检测到循环调用已被自动禁用",
                    )
                    await self.websocket_manager.broadcast_event(self.task_id, event)
                except Exception as e:
                    logger.error(f"推送 tool_disabled 事件失败: {e}")
            # 不推送 tool_called，直接返回
            return

        # 打印日志
        logger.info(
            f"[WebSocketCallback] 工具调用: task_id={self.task_id}, "
            f"agent={self.agent_slug}, tool={tool_name}"
        )

        # 推送事件
        if self.websocket_manager:
            try:
                # 延迟导入避免循环依赖
                from modules.trading_agents.workflow.events import create_tool_called_event

                called_event = create_tool_called_event(
                    task_id=self.task_id,
                    agent_slug=self.agent_slug,
                    tool_name=tool_name,
                    tool_input=input_str,
                    agent_name=self.agent_name,
                )
                await self.websocket_manager.broadcast_event(self.task_id, called_event)
            except Exception as e:
                logger.error(f"推送 tool_called 事件失败: {e}")

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """
        工具执行完成时触发

        Args:
            output: 工具输出
        """
        # 尝试从 kwargs 获取工具名称
        tool_name = "unknown"
        if "name" in kwargs:
            tool_name = kwargs["name"]
        elif "serialized" in kwargs:
            serialized = kwargs["serialized"]
            tool_name = serialized.get("name", "unknown")

        # 确定是否成功
        success = True
        if output and ("error" in output.lower() or "exception" in output.lower()):
            success = False

        # 打印日志
        logger.info(
            f"[WebSocketCallback] 工具结果: task_id={self.task_id}, "
            f"agent={self.agent_slug}, tool={tool_name}, success={success}"
        )

        # 推送事件
        if self.websocket_manager:
            try:
                # 延迟导入避免循环依赖
                from modules.trading_agents.workflow.events import create_tool_result_event

                event = create_tool_result_event(
                    task_id=self.task_id,
                    agent_slug=self.agent_slug,
                    tool_name=tool_name,
                    success=success,
                    output=output or "",
                )
                await self.websocket_manager.broadcast_event(self.task_id, event)
            except Exception as e:
                logger.error(f"推送 tool_result 事件失败: {e}")

    async def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """
        工具执行出错时触发

        Args:
            error: 错误信息
            run_id: 运行 ID
            parent_run_id: 父运行 ID
        """
        # 尝试从 kwargs 获取工具名称
        tool_name = "unknown"
        if "name" in kwargs:
            tool_name = kwargs["name"]
        elif "serialized" in kwargs:
            serialized = kwargs["serialized"]
            tool_name = serialized.get("name", "unknown")

        error_str = str(error)

        # 打印日志
        logger.error(
            f"[WebSocketCallback] 工具错误: task_id={self.task_id}, "
            f"agent={self.agent_slug}, tool={tool_name}, error={error_str}"
        )

        # 推送错误事件
        if self.websocket_manager:
            try:
                # 延迟导入避免循环依赖
                from modules.trading_agents.workflow.events import create_tool_result_event

                event = create_tool_result_event(
                    task_id=self.task_id,
                    agent_slug=self.agent_slug,
                    tool_name=tool_name,
                    success=False,
                    output=error_str,
                )
                await self.websocket_manager.broadcast_event(self.task_id, event)
            except Exception as e:
                logger.error(f"推送 tool_error 事件失败: {e}")

    def get_tool_call_count(self) -> int:
        """
        获取工具调用次数

        Returns:
            工具调用次数
        """
        return self._tool_call_count
