import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ==========================================
# Base Class (給 models.py 裡的 Table 繼承用)
# ==========================================
class Base(DeclarativeBase):
    pass


# ==========================================
# Enum 定義：限制狀態與類型的白名單
# ==========================================
class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"  # 剛放入 Redis 佇列
    PROCESSING = "PROCESSING"  # Worker 正在處理
    COMPLETED = "COMPLETED"  # 處理成功
    FAILED = "FAILED"  # 發生錯誤


class TaskType(str, enum.Enum):
    INGESTION = "INGESTION"  # 文件解析與向量化任務
    INFERENCE = "INFERENCE"  # Agent 對話推論任務


# ==========================================
# 1. 任務追蹤表 (Task)
# 負責記錄 FastAPI 派發給 Celery 的所有非同步任務狀態
# ==========================================
class Task(Base):
    __tablename__ = "tasks"

    # 使用 String(36) 儲存 UUID，這剛好完美對應 Celery 預設的 task_id 格式
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False
    )

    # 儲存 Worker 處理完的結果 (例如回答的文字，或是解析完的檔案 Meta)
    # # Optional 對應 nullable=True
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # 若狀態為 FAILED，這裡儲存 Exception 內容方便除錯
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ==========================================
# 2. 對話記憶表 (ChatSession)
# 負責儲存 Agent 的對話上下文 (Memory Interface)
# ==========================================
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # 例如自動總結的第一句話

    # 將對話歷史以 JSON Array 格式儲存 (專門給 LangChain 或 LLM 用的記憶體 (Memory))
    # 格式預計為: [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "您好！"}]
    history: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ==========================================
# 3. 向量文件區塊表 (DocumentChunk)
# 負責儲存 Ingestion Pipeline 切割後的文字與 Embedding 向量
# ==========================================
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # 關聯原始檔案名稱或 ID; 建立索引以加速搜尋
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 切塊後的真實文字內容

    # pgvector 欄位
    # nomic-embed-text 模型預設輸出的向量維度是 768 維
    # 目的:下 SQL 語法算「餘弦相似度 (Cosine Similarity)」，找出最相關的文件
    # 專案時限考量，embedding NOT NULL的強制性暫時先靠Pydantic來守
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768), nullable=True)

    # 儲存 metadata，例如這塊文字來自 PDF 的第幾頁 (page_number: 1)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
