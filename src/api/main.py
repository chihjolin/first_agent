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


app = FastAPI(title="First Agent API", description="AI Agent Gateway")


@app.get("/")
async def root():
    return {"status": "ok", "message": "API Gateway is running"}
