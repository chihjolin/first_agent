import os

from celery import Celery  # type: ignore

from src.shared.core.celery_app import celery_app

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "ingestion_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)


# @celery_app.task(queue="document_queue")
@celery.task(name="dummy ingestion task")
def dummy_ingestion():
    return "Ingestion worker is ready!"
