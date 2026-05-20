from src.shared.core.celery_app import celery_app
from src.worker.ingestion.pipeline import run_ingestion_pipeline
from src.worker.utils.task_runner import run_worker_task


@celery_app.task(
    name="ingestion.tasks.process_document",
    bind=True,  # bind=True 讓我們可以在函式內使用 self.retry()
    autoretry_for=(
        ConnectionError,
        TimeoutError,
    ),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_document(self, task_id: str, payload: dict):
    """Celery 任務入口：處理文件上傳"""
    return run_worker_task(
        task_id,
        run_ingestion_pipeline,
        task_id,  # 傳遞給 ingestion pipeline 的第一個參數
        payload,  # 傳遞給 ingestion pipeline 的第二個參數
    )
