"""
任务管理模块

包含任务管理器、批量管理器、并发控制器等任务管理相关组件。
"""

# 异常
from ..exceptions import (
    TaskAlreadyRunningError,
    TaskCancelledError,
    TaskExecutionError,
    TaskExpiredError,
    TaskNotFoundError,
    TradingAgentsError,
    get_http_status_from_exception,
)
from .alerts import (
    AlertManager,
    get_alert_manager,
)
from .batch_manager import (
    BatchTaskManager,
    get_batch_manager,
)
from .concurrency_controller import (
    ConcurrencyController,
    get_concurrency_controller,
)

# 基础设施（已合并到 manager 目录）
from .database import (
    drop_collections,
    get_collection_stats,
    init_indexes,
)
from .task_expiry import (
    TaskExpiryHandler,
    get_expiry_handler,
)

# 任务管理
from .task_manager import (
    TaskManager,
    get_task_manager,
    task_manager,
)
from .task_manager_restore import (
    restore_running_tasks_with_checkpoint,
)
from .task_queue import (
    TaskQueueManager,
    get_task_queue_manager,
)

__all__ = [
    # Exceptions
    "TradingAgentsError",
    "TaskNotFoundError",
    "TaskAlreadyRunningError",
    "TaskCancelledError",
    "TaskExpiredError",
    "TaskExecutionError",
    "get_http_status_from_exception",
    # Infrastructure
    "init_indexes",
    "get_collection_stats",
    "drop_collections",
    "AlertManager",
    "get_alert_manager",
    # Task Management
    "TaskManager",
    "task_manager",
    "get_task_manager",
    "restore_running_tasks_with_checkpoint",
    "BatchTaskManager",
    "get_batch_manager",
    "ConcurrencyController",
    "get_concurrency_controller",
    "TaskQueueManager",
    "get_task_queue_manager",
    "TaskExpiryHandler",
    "get_expiry_handler",
]
