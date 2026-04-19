"""
工具循环检测器

监控系统中的工具调用，检测重复循环调用模式。
当某个工具被连续调用相同参数超过阈值时，自动标记该工具为禁用状态，
防止智能体陷入无限循环浪费 Token。
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# 默认阈值：连续相同工具调用 3 次即触发禁用
DEFAULT_LOOP_THRESHOLD = 3


@dataclass
class ToolCallRecord:
    """单次工具调用记录"""

    tool_name: str
    tool_input: str
    agent_slug: str
    call_index: int = 0


@dataclass
class LoopDetectionResult:
    """循环检测结果"""

    is_loop: bool = False
    tool_name: str = ""
    agent_slug: str = ""
    consecutive_count: int = 0
    threshold: int = DEFAULT_LOOP_THRESHOLD
    message: str = ""


class ToolLoopDetector:
    """
    工具循环检测器

    按任务维度跟踪工具调用历史，检测重复模式：
    - 同一智能体对同一工具使用相同输入连续调用
    - 跨智能体对同一工具使用相同输入连续调用

    当检测到循环时：
    1. 记录告警日志
    2. 将工具加入禁用列表
    3. 推送 TOOL_DISABLED 事件到前端
    """

    def __init__(self, threshold: int = DEFAULT_LOOP_THRESHOLD):
        """
        初始化检测器

        Args:
            threshold: 触发禁用的连续相同调用次数阈值
        """
        self.threshold = threshold
        # {task_id: [ToolCallRecord, ...]}
        self._call_history: Dict[str, List[ToolCallRecord]] = defaultdict(list)
        # {task_id: {tool_name: set(agent_slug)}}
        self._disabled_tools: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

    def record_call(
        self,
        task_id: str,
        agent_slug: str,
        tool_name: str,
        tool_input: str,
    ) -> LoopDetectionResult:
        """
        记录一次工具调用，并检测是否形成循环

        Args:
            task_id: 任务 ID
            agent_slug: 智能体标识
            tool_name: 工具名称
            tool_input: 工具输入参数（字符串化）

        Returns:
            LoopDetectionResult: 检测结果
        """
        history = self._call_history[task_id]
        call_index = len(history)

        record = ToolCallRecord(
            tool_name=tool_name,
            tool_input=tool_input,
            agent_slug=agent_slug,
            call_index=call_index,
        )
        history.append(record)

        # 检测该任务中同一工具的连续重复调用
        consecutive_count = self._count_consecutive_calls(history, tool_name, tool_input)

        # 如果已连续调用达到阈值，判定为循环
        if consecutive_count >= self.threshold:
            # 标记工具为禁用（按任务维度）
            self._disabled_tools[task_id][tool_name].add(agent_slug)

            message = (
                f"检测到工具循环调用: task={task_id}, agent={agent_slug}, "
                f"tool={tool_name}, 连续调用 {consecutive_count} 次（阈值={self.threshold}）。"
                f"该工具在此任务中已被自动禁用。"
            )
            logger.warning(f"[LoopDetector] {message}")

            return LoopDetectionResult(
                is_loop=True,
                tool_name=tool_name,
                agent_slug=agent_slug,
                consecutive_count=consecutive_count,
                threshold=self.threshold,
                message=message,
            )

        return LoopDetectionResult(
            is_loop=False,
            tool_name=tool_name,
            agent_slug=agent_slug,
            consecutive_count=consecutive_count,
            threshold=self.threshold,
        )

    def is_tool_disabled(self, task_id: str, tool_name: str, agent_slug: str) -> bool:
        """
        检查工具是否已被禁用

        Args:
            task_id: 任务 ID
            tool_name: 工具名称
            agent_slug: 智能体标识

        Returns:
            是否已被禁用（若该工具已被全局禁用或该智能体禁用则返回 True）
        """
        disabled_agents = self._disabled_tools.get(task_id, {}).get(tool_name, set())
        # 如果已记录任意智能体触发禁用，则该工具在整个任务中禁用
        # 避免其他智能体也陷入同一循环
        return len(disabled_agents) > 0

    def _count_consecutive_calls(
        self,
        history: List[ToolCallRecord],
        tool_name: str,
        tool_input: str,
    ) -> int:
        """
        计算同一工具相同输入的最近连续调用次数

        从历史记录末尾向前扫描，统计连续匹配的记录数。
        """
        count = 0
        # 从最后一条记录向前检查
        for record in reversed(history):
            if record.tool_name == tool_name and record.tool_input == tool_input:
                count += 1
            else:
                break
        return count

    def get_disabled_tools(self, task_id: str) -> Dict[str, Set[str]]:
        """
        获取指定任务中所有被禁用的工具

        Args:
            task_id: 任务 ID

        Returns:
            {tool_name: set(agent_slug)}
        """
        return dict(self._disabled_tools.get(task_id, {}))

    def clear_task(self, task_id: str) -> None:
        """
        清理指定任务的检测状态（任务完成后调用）

        Args:
            task_id: 任务 ID
        """
        if task_id in self._call_history:
            del self._call_history[task_id]
        if task_id in self._disabled_tools:
            del self._disabled_tools[task_id]
        logger.debug(f"[LoopDetector] 已清理任务状态: task={task_id}")

    def get_task_stats(self, task_id: str) -> Dict:
        """
        获取任务的工具调用统计

        Args:
            task_id: 任务 ID

        Returns:
            统计信息字典
        """
        history = self._call_history.get(task_id, [])
        disabled = self._disabled_tools.get(task_id, {})

        tool_counts: Dict[str, int] = {}
        for record in history:
            tool_counts[record.tool_name] = tool_counts.get(record.tool_name, 0) + 1

        return {
            "task_id": task_id,
            "total_calls": len(history),
            "tool_counts": tool_counts,
            "disabled_tools": {t: list(a) for t, a in disabled.items()},
        }


# =============================================================================
# 全局检测器实例
# =============================================================================

_loop_detector: Optional[ToolLoopDetector] = None


def get_loop_detector(threshold: int = DEFAULT_LOOP_THRESHOLD) -> ToolLoopDetector:
    """
    获取全局工具循环检测器实例

    Args:
        threshold: 触发禁用的阈值

    Returns:
        ToolLoopDetector 实例
    """
    global _loop_detector
    if _loop_detector is None:
        _loop_detector = ToolLoopDetector(threshold=threshold)
    return _loop_detector


def reset_loop_detector(threshold: int = DEFAULT_LOOP_THRESHOLD) -> ToolLoopDetector:
    """
    重置全局检测器实例（测试或配置变更时使用）

    Args:
        threshold: 新的阈值

    Returns:
        新的 ToolLoopDetector 实例
    """
    global _loop_detector
    _loop_detector = ToolLoopDetector(threshold=threshold)
    return _loop_detector
