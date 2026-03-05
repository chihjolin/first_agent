import time

from src.shared.core.celery_app import celery_app


@celery_app.task(name="agent_runtime.tasks.process_chat_inference")
def process_chat_inference(**kwargs):
    task_id = kwargs["task_id"]
    query = kwargs["query"]
    user_id = kwargs["user_id"]
    print("PROCESSING", task_id)
    time.sleep(30)
    return "Inference worker is ready!"
