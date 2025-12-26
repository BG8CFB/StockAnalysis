"""
工具循环检测器

检测智能体在调用工具时的无限循环行为，防止系统资源浪费。
"""

import json
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from modules.trading_agents.core.exceptions import ToolLoopDetectedException

logger = logging.getLogger(__name__)


@dataclass
class CallRecord:
    """工具调用记录"""
    tool_name: str
    arguments: Dict
    timestamp: float


class ToolLoopDetector:
    """
    工具循环检测器

    检测规则：
    - 同一个智能体
    - 连续 3 次调用同一个工具
    - 3 次调用的参数完全相同（JSON 比较）
    """

    # 循环检测阈值
    LOOP_DETECTION_COUNT = 3

    def __init__(self):
        # {task_id: {agent_slug: [CallRecord, ...]}}
        self._call_history: Dict[str, Dict[str, List[CallRecord]]] = {}

    def record_call(
        self,
        task_id: str,
        agent_slug: str,
        tool_name: str,
        arguments: Dict
    ) -> Optional[str]:
        """
        记录工具调用并检测循环

        Args:
            task_id: 任务 ID
            agent_slug: 智能体标识
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            如果检测到循环，返回被禁用的工具名称；否则返回 None
        """
        # 确保数据结构存在
        if task_id not in self._call_history:
            self._call_history[task_id] = {}

        if agent_slug not in self._call_history[task_id]:
            self._call_history[task_id][agent_slug] = []

        history = self._call_history[task_id][agent_slug]

        # 创建调用记录
        call_record = CallRecord(
            tool_name=tool_name,
            arguments=self._normalize_args(arguments),
            timestamp=__import__("time").time()
        )

        # 添加到历史记录
        history.append(call_record)

        # 保留最近 3 次调用记录
        if len(history) > self.LOOP_DETECTION_COUNT:
            history.pop(0)

        # 检测循环：连续 3 次相同调用
        if len(history) == self.LOOP_DETECTION_COUNT:
            if self._is_loop(history):
                logger.warning(
                    f"检测到工具循环: task={task_id}, agent={agent_slug}, "
                    f"tool={tool_name}, 连续调用{self.LOOP_DETECTION_COUNT}次，参数完全相同"
                )
                return tool_name

        return None

    def _is_loop(self, history: List[CallRecord]) -> bool:
        """
        判断是否为循环

        Args:
            history: 调用历史记录

        Returns:
            是否为循环
        """
        if len(history) < self.LOOP_DETECTION_COUNT:
            return False

        # 检查工具名称是否相同
        first_tool = history[0].tool_name
        if not all(record.tool_name == first_tool for record in history):
            return False

        # 检查参数是否相同
        first_args = history[0].arguments
        if not all(record.arguments == first_args for record in history):
            return False

        return True

    def _normalize_args(self, args: Dict) -> Dict:
        """
        标准化参数用于比较

        Args:
            args: 原始参数

        Returns:
            标准化后的参数
        """
        # JSON 序列化后排序，确保键顺序一致
        try:
            normalized = json.dumps(args, sort_keys=True)
            return json.loads(normalized)
        except (TypeError, json.JSONDecodeError):
            # 如果无法序列化，直接返回原值
            return args

    def clear_history(self, task_id: str, agent_slug: Optional[str] = None) -> None:
        """
        清除历史记录

        Args:
            task_id: 任务 ID
            agent_slug: 智能体标识，如果为 None 则清除该任务的所有记录
        """
        if task_id not in self._call_history:
            return

        if agent_slug is None:
            # 清除该任务的所有记录
            del self._call_history[task_id]
            logger.debug(f"清除任务的所有工具调用历史: task={task_id}")
        else:
            # 清除特定智能体的记录
            if agent_slug in self._call_history[task_id]:
                del self._call_history[task_id][agent_slug]
                logger.debug(
                    f"清除智能体的工具调用历史: task={task_id}, agent={agent_slug}"
                )

            # 如果该任务没有记录了，删除任务条目
            if not self._call_history[task_id]:
                del self._call_history[task_id]

    def get_history_count(self, task_id: str, agent_slug: str) -> int:
        """
        获取指定智能体的历史记录数量

        Args:
            task_id: 任务 ID
            agent_slug: 智能体标识

        Returns:
            历史记录数量
        """
        if task_id not in self._call_history:
            return 0

        if agent_slug not in self._call_history[task_id]:
            return 0

        return len(self._call_history[task_id][agent_slug])

    def get_recent_calls(
        self,
        task_id: str,
        agent_slug: str,
        count: int = 3
    ) -> List[CallRecord]:
        """
        获取最近的调用记录

        Args:
            task_id: 任务 ID
            agent_slug: 智能体标识
            count: 返回记录数量

        Returns:
            最近调用记录列表
        """
        if task_id not in self._call_history:
            return []

        if agent_slug not in self._call_history[task_id]:
            return []

        history = self._call_history[task_id][agent_slug]
        return history[-count:]


# =============================================================================
# 全局工具循环检测器实例
# =============================================================================

loop_detector = ToolLoopDetector()


def get_loop_detector() -> ToolLoopDetector:
    """获取全局工具循环检测器实例"""
    return loop_detector


# =============================================================================
# 辅助函数
# =============================================================================

def check_tool_loop(
    task_id: str,
    agent_slug: str,
    tool_name: str,
    arguments: Dict,
    detector: Optional[ToolLoopDetector] = None
) -> Tuple[bool, Optional[str]]:
    """
    检查工具是否循环

    Args:
        task_id: 任务 ID
        agent_slug: 智能体标识
        tool_name: 工具名称
        arguments: 工具参数
        detector: 循环检测器（可选，默认使用全局实例）

    Returns:
        (是否循环, 被禁用的工具名称)
    """
    if detector is None:
        detector = loop_detector

    disabled_tool = detector.record_call(
        task_id=task_id,
        agent_slug=agent_slug,
        tool_name=tool_name,
        arguments=arguments
    )

    return disabled_tool is not None, disabled_tool


def clear_agent_history(
    task_id: str,
    agent_slug: str,
    detector: Optional[ToolLoopDetector] = None
) -> None:
    """
    清除智能体的调用历史

    Args:
        task_id: 任务 ID
        agent_slug: 智能体标识
        detector: 循环检测器（可选，默认使用全局实例）
    """
    if detector is None:
        detector = loop_detector

    detector.clear_history(task_id, agent_slug)
