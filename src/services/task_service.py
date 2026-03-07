from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import (
    BrokerDispatchError,
    DatabaseWriteError,
    TaskNotFoundError,
)
from src.shared.core.celery_app import celery_app
from src.shared.core.logger import get_logger
from src.shared.db.crud.task import TaskRepository
from src.shared.db.models import Task, TaskStatus, TaskType

logger = get_logger(__name__)


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_repo = TaskRepository(session)

    # ==========================================
    # [內部共用核心] 處理所有任務的生命週期：寫入 DB -> Commit -> 派發 Celery 任務 -> 錯誤補償
    # ==========================================
    async def _create_and_dispatch(
        self,
        task_type: TaskType,
        celery_task_name: str,  # 只是告訴 Celery Worker 「你要去執行哪一段程式碼」
        payload: Dict[
            str, Any
        ],  # {"payload": {"query": query, "user_id": user_id}} (business data)
    ) -> Task:
        new_task = Task(
            task_type=task_type,
            status=TaskStatus.PENDING,
        )
        # 1. 保證資料庫寫入 (Transaction 1)
        try:
            await self.task_repo.create(new_task)
            # 必須先 Commit，保證 Worker 收到任務去查 DB 時，資料已經 100% 存在
            await self.session.commit()
            logger.info(
                f"[{task_type.value}] Task {new_task.id} saved to DB. Status: {new_task.status}"
            )
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save task to database: {str(e)}")
            raise DatabaseWriteError(
                f"資料庫寫入失敗，無法建立 {task_type.value} 任務。"
            )

        # 2. 派發至 Message Broker(Redis)
        try:
            # 這裡我們把動態產生的 task_id 以及payload 塞進 kwargs 給 Celery
            # Celery 派發
            celery_app.send_task(
                celery_task_name,
                kwargs={
                    "task_id": str(new_task.id),
                    "payload": payload,
                },
            )
            logger.info(
                f"[{task_type.value}] Task {new_task.id} dispatched to Broker: {celery_task_name}"
            )

        except Exception as e:
            # 3. 分散式系統的補償機制 (Compensation)
            # 如果 Redis 罷工了，任務發不出去，必須把 DB 狀態標記為 FAILED (Fail-Fast機制)
            # 派發階段的失敗，交給前端/使用者手動重試；執行階段的失敗，交給 Worker層: Celery 自動重試
            logger.error(f"Failed to dispatch task {new_task.id} to Broker: {str(e)}")
            new_task.status = TaskStatus.FAILED
            new_task.error_message = (
                "Message Broker (Redis) connection or dispatch failed."
            )

            await self.task_repo.save(new_task)
            await self.session.commit()
            raise BrokerDispatchError(
                f"任務 {new_task.id} 已建立，但派發至佇列失敗，狀態已標記為 FAILED。"
            )

        # 4. 回傳帶有 ID 的 Task 物件給 Router (讓 Router 去轉成 Pydantic 回傳給前端)
        return new_task

    # ==========================================
    # 對外開放的業務介面 (Public API)
    # ==========================================

    async def create_chat_task(self, query: str, user_id: str = "anonymous") -> Task:
        """
        建立對話推論任務 (Inference Flow)
        """
        return await self._create_and_dispatch(
            task_type=TaskType.INFERENCE,
            celery_task_name="agent_runtime.tasks.process_chat_inference",
            payload={
                "query": query,
                "user_id": user_id,
            },
        )

    async def create_ingestion_task(self, file_name: str, file_path: str) -> Task:
        """
        建立文件解析與向量化任務 (Ingestion Pipeline)
        """
        # 假設上傳檔案後，我們會先把檔案存在本機或 S3，然後把路徑交給 Celery 處理
        return await self._create_and_dispatch(
            task_type=TaskType.INGESTION,
            celery_task_name="ingestion.tasks.process_document",
            payload={
                "file_name": file_name,
                "file_path": file_path,
            },
        )

    async def get_task_status(self, task_id: str) -> Task:
        """
        供前端 Polling 查詢任務進度。
        如果找不到任務，直接拋出領域例外 (Domain Exception)。
        注意：回傳型別從 Task | None 變成了確定的 Task。
        """
        task = await self.task_repo.get(task_id)
        if not task:
            # 把 Repo 誠實回傳的 None，翻譯成帶有業務意義的 TaskNotFoundError
            raise TaskNotFoundError(f"找不到指定的任務 ID: {task_id}")
        return task
