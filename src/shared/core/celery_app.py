from celery import Celery  # type: ignore

from src.shared.core.config import settings

# 實例化 Celery 應用程式 (作為任務派發的 Producer)
celery_app = Celery(
    "first_agent",
    broker=settings.REDIS_URL,
)


# 基礎設定，確保任務是以 JSON 格式序列化並推送到 Redis
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
    # task_routes={
    #     "ingestion.tasks.process_document": {"queue": "document_queue"},
    #     "agent_runtime.tasks.process_chat_inference": {"queue": "inference_queue"},
    # },
)
