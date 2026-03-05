from celery import Celery  # type: ignore

from src.shared.core.config import settings

# 實例化 Celery 應用程式 (作為任務派發的 Producer)
celery_app = Celery(
    "first_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# 設定 autodiscover_tasks，讓 Celery 啟動時能自動找到我們散落在各目錄的任務函式
celery_app.autodiscover_tasks(
    [
        "src.agent_runtime",
        "src.ingestion",
    ]
)

# 基礎設定，確保任務是以 JSON 格式序列化並推送到 Redis
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
)

# routing table 生效是 針對 Celery 任務名稱（task name）
celery_app.conf.task_routes = {
    "agent_runtime.tasks.process_chat_inference": {"queue": "inference_queue"},
    "ingestion.tasks.process_document": {"queue": "document_queue"},
}
