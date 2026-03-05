import os

from celery import Celery  # type: ignore

from src.shared.core.celery_app import celery_app

# 讀取 Docker 注入的環境變數
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 建立Celery實例
celery = Celery(
    "agent_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)


# @celery_app.task(queue="inference_queue")
@celery.task(name="dummy_inference_task")
def dummy_inference():
    return "Inference worker is ready!"
