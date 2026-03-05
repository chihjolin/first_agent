from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.api import api_router
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
    if async_engine is not None:
        logger.info("Disposing database engine...")
        await async_engine.dispose()
    logger.info("Shutdown complete.")


# 實例化 FastAPI 應用程式
app = FastAPI(
    title="First Agent API",
    description="AI Agent Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

# 設定 CORS (MVP 階段先全開)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # 這在 production 會出錯, allow_credentials=True 時不能 allow_origins=["*"]
    allow_credentials=True,  # MVP OK，但之後一定要改成：allow_origins=["http://localhost:3000"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# 統一掛載所有 API 路由，並設定全域的基礎路徑
app.include_router(api_router, prefix="/api/v1")


# ==========================================
# 基礎路由 (Base Routes)
# ==========================================
@app.get("/")
async def root():
    return {"status": "ok", "message": "API Gateway is running"}


@app.get("/health", tags=["System"])
async def health_check():
    """
    系統健康檢查端點 (供監控使用)
    """
    logger.info("Health check endpoint called.")
    return {
        "status": "ok",
        "service": "First Agent API Gateway",
        "message": "系統正常運作",
    }
