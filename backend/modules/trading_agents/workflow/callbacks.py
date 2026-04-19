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


class TokenUsageCallback(AsyncCallbackHandler):
    """
    Token 使用量统计回调

    自动拦截所有 LLM 调用，统计 input_tokens、output_tokens、thinking_tokens。
    支持 GLM 系列模型的思考 token（reasoning_tokens）。

    使用方式:
    - 在调度器中创建实例，附加到模型上
    - 工作流完成后，调用 get_totals() 获取汇总数据
    """

    def __init__(self) -> None:
        super().__init__()
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_thinking_tokens: int = 0
        self.call_count: int = 0

    async def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """
        LLM 调用完成时触发 — 自动统计 token 使用量

        LangChain 的 LLMResult 包含 llm_output 字典，其中:
        - token_usage: {prompt_tokens, completion_tokens, total_tokens}
        - 或 response_metadata 中包含 usage 信息

        对于 GLM 模型，思考 token 在:
        - response_metadata.reasoning_tokens
        - 或 response 的 generations 中 AIMessage.usage_metadata
        """
        try:
            # 方式1: 从 llm_output 中提取（部分模型 provider 使用）
            if hasattr(response, "llm_output") and response.llm_output:
                token_usage = response.llm_output.get("token_usage", {})
                if token_usage:
                    self.total_input_tokens += token_usage.get("prompt_tokens", 0)
                    self.total_output_tokens += token_usage.get("completion_tokens", 0)
                    self.call_count += 1
                    return

            # 方式2: 从 generations 中的 AIMessage.usage_metadata 提取
            if hasattr(response, "generations") and response.generations:
                for gen_list in response.generations:
                    for gen in gen_list:
                        message = gen.message if hasattr(gen, "message") else gen

                        # 提取 usage_metadata
                        usage_metadata = None
                        if hasattr(message, "usage_metadata"):
                            usage_metadata = message.usage_metadata
                        elif hasattr(message, "additional_kwargs"):
                            usage_metadata = message.additional_kwargs.get("usage_metadata")

                        if usage_metadata and isinstance(usage_metadata, dict):
                            self.total_input_tokens += usage_metadata.get("input_tokens", 0)
                            self.total_output_tokens += usage_metadata.get("output_tokens", 0)
                            self.call_count += 1

                        # 提取 thinking/reasoning tokens
                        if hasattr(message, "response_metadata"):
                            meta = message.response_metadata
                            if isinstance(meta, dict):
                                self.total_thinking_tokens += meta.get("reasoning_tokens", 0)
                                # 有些模型放在 thinking_tokens 字段
                                self.total_thinking_tokens += meta.get("thinking_tokens", 0)

                        # 从 additional_kwargs 提取思考 token
                        if hasattr(message, "additional_kwargs"):
                            ak = message.additional_kwargs
                            if isinstance(ak, dict):
                                reasoning = ak.get("reasoning_content", "")
                                # reasoning_content 是文本，无法直接计算 token 数
                                # 但有些 provider 会返回 reasoning_tokens
                                if "reasoning_tokens" in ak:
                                    self.total_thinking_tokens += ak.get("reasoning_tokens", 0)

        except Exception as e:
            logger.debug(f"TokenUsageCallback 解析 token 失败: {e}")

    def get_totals(self) -> Dict[str, int]:
        """获取汇总的 token 使用量"""
        total_output = self.total_output_tokens + self.total_thinking_tokens
        return {
            "prompt_tokens": self.total_input_tokens,
            "completion_tokens": self.total_output_tokens,
            "thinking_tokens": self.total_thinking_tokens,
            "total_tokens": self.total_input_tokens + total_output,
            "call_count": self.call_count,
        }

    def reset(self) -> None:
        """重置统计数据"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_thinking_tokens = 0
        self.call_count = 0
