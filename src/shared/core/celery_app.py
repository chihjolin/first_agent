from celery import Celery  # type: ignore

from src.shared.core.config import settings

# 實例化 Celery 應用程式 (作為任務派發的 Producer)
celery_app = Celery(
    "first_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# 設定 autodiscover_tasks，讓 Celery 啟動時能自動找到我們散落在各目錄的任務函式(Task Register)
# 這邊要對應到專案路徑
celery_app.autodiscover_tasks(
    [
        "src.worker.agent_runtime",
        "src.worker.ingestion",
    ]
)

# 基礎設定，確保任務是以 JSON 格式序列化並推送到 Redis
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
    # 關閉 Celery 對 root logger 的接管
    worker_hijack_root_logger=False,
)

# routing table 生效是 針對 Celery 任務名稱
# （必須完全對應對應fastapi: task_service: celery_app.send_task的參數celery_task_name）
celery_app.conf.task_routes = {
    "agent_runtime.tasks.process_chat_inference": {"queue": "inference_queue"},
    "ingestion.tasks.process_document": {"queue": "document_queue"},
}
