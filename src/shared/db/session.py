from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.shared.core.config import settings
from src.shared.core.logger import get_logger

logger = get_logger(__name__)

# ==========================================
# 獲取或組裝 DATABASE_URL_ASYNC/DATABASE_URL_SYNC
# ==========================================
# 優先使用 Docker 注入的 URL(ASYNC)
DATABASE_URL_ASYNC = settings.DATABASE_URL_ASYNC

# 如果沒有 DATABASE_URL，代表現在是「本機開發/Alembic 執行環境」，依賴 Pydantic 驗證過的安全屬性來組裝
if not DATABASE_URL_ASYNC:
    DATABASE_URL_ASYNC = (
        f"postgresql+asyncpg://"
        f"{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_HOST_PORT}/"
        f"{settings.POSTGRES_DB}"
    )
    logger.info("Local environment detected. Constructed DATABASE_URL from settings.")


# 專業寫法: 建立 URL 物件
url_obj_async = make_url(DATABASE_URL_ASYNC)

# debug用，暫時全部印出
logger.info(
    f"Connecting to database via: {url_obj_async.render_as_string(hide_password=False)}"
)


# SYNC版本(Worker 使用)
DATABASE_URL_SYNC = settings.DATABASE_URL_SYNC

if not DATABASE_URL_SYNC:
    DATABASE_URL_SYNC = (
        f"postgresql+psycopg://"
        f"{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_HOST_PORT}/"
        f"{settings.POSTGRES_DB}"
    )
    logger.info(
        "Local environment detected. Constructed DATABASE_URL_SYNC from settings."
    )

url_obj_sync = make_url(DATABASE_URL_SYNC)

# debug用，暫時全部印出
logger.info(
    f"Connecting to database via: {url_obj_sync.render_as_string(hide_password=False)}"
)


# ---------------------------------------------------
# 建立 Sync / Async Engine
# ---------------------------------------------------
engine = None
async_engine = None
SessionLocal = None
AsyncSessionLocal = None

# --- 給 FastAPI 用的非同步引擎 ---
async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,  # Async 環境極度重要，避免隱式 IO
)
logger.info("Async PostgreSQL Engine Initialized.")

# --- 給 Celery Worker 用的同步引擎 ---
engine = create_engine(
    DATABASE_URL_SYNC,
    echo=False,
    future=True,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
logger.info("Sync PostgreSQL Engine Initialized.")


# ---------------------------------------------------
# FastAPI Dependency Injection
# ---------------------------------------------------
async def get_db():
    """給 FastAPI 路由使用的 Async Session 產生器"""
    if not AsyncSessionLocal:
        raise RuntimeError("Async engine was not initialized.")

    # async with 本身就是 Context Manager，離開區塊時底層會自動執行 close()
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------
# Worker Sync Session Factory
# FastAPI 會自動管理 dependency lifecycle
# Celery 不會, 所以 worker 要自己管理 session lifecycle。
# ---------------------------------------------------


@contextmanager
def get_sync_db():
    """
    給 Celery Worker 使用的 Sync Session Factory
    """
    if not SessionLocal:
        raise RuntimeError("Sync engine was not initialized.")

    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
