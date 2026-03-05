from fastapi import APIRouter

from src.api.routes import chat, task

# 建立一個 Master Router
api_router = APIRouter()

# 統一在這裡掛載並設定前綴 (Prefix) 與標籤 (Tags)
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(task.router, prefix="/tasks", tags=["Tasks"])
# api_router.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion"])
