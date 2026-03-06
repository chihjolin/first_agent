"""
Celery Worker Task Runner (Worker Orchestration Layer)

核心職責：
- 統一管理任務的狀態機流轉 (PENDING -> PROCESSING -> COMPLETED / FAILED)
- 統一攔截錯誤並觸發 Celery 重試機制
- 確保資料庫連線 (DB Session) 是短暫且高效的，不被耗時邏輯阻塞

設計原則：
- Worker 的 orchestration 與業務邏輯分離
- workflow / pipeline 專注在「任務要做什麼」
- task_runner 專注在「任務如何被執行」
"""

from typing import Any, Callable, Dict

from src.shared.core.logger import get_logger
from src.shared.db.session import get_sync_db
from src.worker.services.task_state import TaskStateService

logger = get_logger(__name__)


def run_worker_task(
    task_id: str,
    workflow: Callable[..., Dict[str, Any]],
    *args,
    **kwargs,
) -> None:
    """
    Worker 任務通用排程器 (Wrapper)

    Args:
        task_id (str): 任務 UUID
        workflow (Callable): 實際要執行的耗時業務邏輯函式
        *args, **kwargs: 傳遞給 workflow 的具體參數
    """
    logger.info("[Task %s] Worker task started", task_id)

    # ==========================================
    # 階段 1：標記 PROCESSING (短連線)
    # ==========================================
    try:
        with get_sync_db() as session:
            state_service = TaskStateService(session)
            state_service.mark_processing(task_id)
    except Exception as e:
        logger.error("[Task %s] Failed to mark as PROCESSING", task_id, exc_info=True)
        raise  # 讓外層 Celery 捕捉並重試

    # ==========================================
    # 階段 2：執行耗時業務邏輯
    # 效能關鍵：這裡不傳入 session！讓 workflow 完全脫離外層的 DB 連線綁架
    # ==========================================
    try:
        result = workflow(*args, **kwargs)
    except Exception as e:
        logger.error(
            "[Task %s] Worker task failed during execution", task_id, exc_info=True
        )

        # 任務失敗，開啟短連線標記 FAILED
        try:
            with get_sync_db() as session:
                state_service = TaskStateService(session)
                state_service.mark_failed(task_id, error_message=str(e))
        except Exception:
            logger.error(
                "[Task %s] Critical: Failed to update status to FAILED",
                task_id,
                exc_info=True,
            )

        raise  # 將錯誤往上丟，觸發 Celery 的 autoretry_for

    # ==========================================
    # 階段 3：標記 COMPLETED (短連線)
    # ==========================================
    try:
        with get_sync_db() as session:
            state_service = TaskStateService(session)
            state_service.mark_completed(task_id, result=result)

        logger.info("[Task %s] Worker task completed successfully", task_id)
    except Exception as e:
        logger.exception("[Task %s] Worker task failed during execution", task_id)
        raise

    # try:
    #     # 建立 DB session
    #     with get_sync_db() as session:
    #         state_service = TaskStateService(session)

    #         # 1. PENDING -> PROCESSING
    #         state_service.mark_processing(task_id)
    #         # 2. 執行實際 workflow / pipeline
    #         result = workflow(session, *args, **kwargs)
    #         # 3. PROCESSING -> COMPLETED
    #         state_service.mark_completed(
    #             task_id,
    #             result=result,
    #         )

    #         logger.info("[Task %s] Worker task completed", task_id)

    # except Exception as e:
    #     # logger.exception 會自動附上 stack trace
    #     logger.exception("[Task %s] Worker task failed", task_id)

    #     # 任務失敗也要寫 DB
    #     try:
    #         with get_sync_db() as session:
    #             state_service = TaskStateService(session)

    #             state_service.mark_failed(
    #                 task_id,
    #                 error_message=str(e),
    #             )

    #     except Exception:
    #         # 如果 DB 更新失敗，仍然要記錄
    #         logger.exception(
    #             "[Task %s] Failed to update task status to FAILED", task_id
    #         )

    #     raise
