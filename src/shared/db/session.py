import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.shared.core.logger import get_logger

logger = get_logger(__name__)

# 直接從 Docker 環境變數讀取組裝好的 URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("環境變數 DATABASE_URL 尚未設定！")

logger.info(f"Connecting to database via: {DATABASE_URL}")


# ---------------------------------------------------
# Base Class (給 models.py 裡的 Table 繼承用)
# ---------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------
# 自動判斷建立 Sync 或 Async Engine
# ---------------------------------------------------
engine = None
async_engine = None
SessionLocal = None
AsyncSessionLocal = None

if "asyncpg" in DATABASE_URL:
    # --- 給 FastAPI 用的非同步引擎 ---
    async_engine = create_async_engine(
        DATABASE_URL,
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
else:
    # --- 給 Celery Worker 用的同步引擎 ---
    engine = create_engine(
        DATABASE_URL,
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
