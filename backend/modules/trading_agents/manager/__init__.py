"""
任务管理模块

包含任务管理器、批量管理器、并发控制器等任务管理相关组件。
"""

# 异常
from ..exceptions import (
    TradingAgentsException,
    TaskNotFoundException,
    TaskAlreadyRunningException,
    TaskCancelledException,
    TaskExpiredException,
    TaskExecutionException,
    get_http_status_from_exception,
)

# 基础设施（已合并到 manager 目录）
from .database import (
    init_indexes,
    get_collection_stats,
    drop_collections,
)
from .alerts import (
    AlertManager,
    get_alert_manager,
)

# 任务管理
from .task_manager import (
    TaskManager,
    task_manager,
    get_task_manager,
)
from .task_manager_restore import (
    restore_running_tasks_with_checkpoint,
)
from .batch_manager import (
    BatchTaskManager,
    get_batch_manager,
)
from .concurrency_controller import (
    ConcurrencyController,
    get_concurrency_controller,
)
from .task_queue import (
    TaskQueueManager,
    get_task_queue_manager,
)
from .task_expiry import (
    TaskExpiryHandler,
    get_expiry_handler,
)
from .concurrency import (
    ConcurrencyManager,
    QuotaInfo,
    LockInfo,
    concurrency_manager,
    get_concurrency_manager,
)

__all__ = [
    # Exceptions
    "TradingAgentsException",
    "TaskNotFoundException",
    "TaskAlreadyRunningException",
    "TaskCancelledException",
    "TaskExpiredException",
    "TaskExecutionException",
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
    "ConcurrencyManager",
    "QuotaInfo",
    "LockInfo",
    "concurrency_manager",
    "get_concurrency_manager",
]
