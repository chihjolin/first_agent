from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.domain.exceptions import InvalidTaskStateTransition, TaskNotFoundError
from src.shared.core.logger import get_logger
from src.shared.db.crud.sync.task import TaskSyncRepository
from src.shared.db.models import Task, TaskStatus

logger = get_logger(__name__)


class TaskStateService:
    """
    Worker 專用任務狀態服務 (Sync)
    注意：
        - 不負責 commit
        - transaction 由 get_sync_db() context manager 管理
    """

    # ==========================================
    # State Machine Definition
    # 定義一個有限狀態機 (Finite State Machine, FSM)
    # ==========================================

    _ALLOWED_TRANSITIONS = {
        TaskStatus.PENDING: {TaskStatus.PROCESSING},
        TaskStatus.PROCESSING: {TaskStatus.COMPLETED, TaskStatus.FAILED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.FAILED: set(),
    }

    def __init__(self, session: Session):
        # self.session = session  # service 不需要直接持有 session, 應該是service → repository -> session
        self.repo = TaskSyncRepository(session)

    # ==========================================
    # Internal Helpers
    # ==========================================

    def _get_task_or_raise(self, task_id: str) -> Task:
        task = self.repo.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found.")
        return task

    def _validate_transition(self, task: Task, new_status: TaskStatus) -> None:
        """
        確保狀態轉換合法
        Worker system 一定要有State machine guard: 避免retry / duplicate worker 破壞資料
        """
        current_status = task.status
        allowed = self._ALLOWED_TRANSITIONS.get(current_status, set())

        if new_status not in allowed:
            raise InvalidTaskStateTransition(
                f"Invalid state transition: {current_status} -> {new_status}"
            )

    def _update_status(
        self,
        task: Task,
        status: TaskStatus,  # 欲更新成的新狀態
        *,  # 強制關鍵字參數: 出現在 * 後面的參數，強制只能使用具名呼叫
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> Task:

        # 檢查 state transition
        self._validate_transition(task, status)

        old_status = task.status
        task.status = status

        if result is not None:
            task.result = result

        if error_message is not None:
            task.error_message = error_message

        self.repo.save(task)

        # 延遲字串插值 (Lazy String Interpolation in Logging)
        # 只有當該 Log 等級（例如 INFO）有被啟用時，Python 才會真正在底層去組裝字串。這在每秒幾千次的高併發系統中，能省下可觀的效能
        logger.info(
            "[Task %s] Status updated: %s → %s",
            task.id,
            old_status.value,
            status.value,
        )

        return task

    # ==========================================
    # Public API
    # ==========================================

    def mark_processing(self, task_id: str) -> Task:
        """標記任務為 PROCESSING"""
        task = self._get_task_or_raise(task_id)
        return self._update_status(task, TaskStatus.PROCESSING)

    def mark_completed(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """標記任務為 COMPLETED"""
        task = self._get_task_or_raise(task_id)
        return self._update_status(
            task,
            TaskStatus.COMPLETED,
            result=result,
        )

    def mark_failed(self, task_id: str, error_message: str) -> Task:
        """標記任務為 FAILED"""
        task = self._get_task_or_raise(task_id)
        return self._update_status(
            task,
            TaskStatus.FAILED,
            error_message=error_message,
        )
