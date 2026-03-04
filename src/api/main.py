from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.shared.core.logger import get_logger
from src.shared.db.session import async_engine

# 初始化標準 Logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 應用程式生命週期管理
    """
    # ---------------- 啟動階段 (Startup) ----------------
    logger.info("FastAPI App is starting up...")
    yield  # 應用程式執行期間停留在這裡

    # ---------------- 關閉階段 (Shutdown) ----------------
    logger.info("FastAPI App is shutting down...")
    logger.info("Disposing database engine...")
    await async_engine.dispose()
    logger.info("Shutdown complete.")


# 實例化 FastAPI 應用程式
app = FastAPI(title="First Agent API", description="AI Agent Gateway")


@app.get("/")
async def root():
    return {"status": "ok", "message": "API Gateway is running"}
