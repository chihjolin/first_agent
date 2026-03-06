from src.shared.core.celery_app import celery_app
from src.worker.agent_runtime.workflows import run_agent_workflow
from src.worker.utils.task_runner import run_worker_task


@celery_app.task(
    name="agent_runtime.tasks.process_chat_inference",
    bind=True,  # bind=True 讓我們可以在函式內使用 self.retry()
    autoretry_for=(
        ConnectionError,
        TimeoutError,
    ),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_chat_inference(self, task_id: str, payload: dict):
    """Celery 任務入口：處理對話推論"""
    run_worker_task(
        task_id,
        run_agent_workflow,
        payload,
    )
