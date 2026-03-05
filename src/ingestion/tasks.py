import time

from src.shared.core.celery_app import celery_app


@celery_app.task(name="ingestion.tasks.process_document")
def process_document(**kwargs):
    task_id = kwargs["task_id"]
    file_name = kwargs["file_name"]
    file_path = kwargs["file_path"]
    print("PROCESSING", task_id)
    time.sleep(30)
    return "Ingestion worker is ready!"
