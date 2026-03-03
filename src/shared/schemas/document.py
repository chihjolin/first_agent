from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunkBase(BaseModel):
    document_id: str
    content: str
    # metadata 在資料庫我們命名為 metadata_ (避開保留字)，但在 API 介面我們通常顯示為 metadata
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")


class DocumentChunkCreate(DocumentChunkBase):
    # API收到JSON Array-> Pydantic 接收 List[float] -> 儲存時 pgvector 會自動轉成向量格式
    # 強制要求輸入向量
    embedding: List[float]


# Response受眾:內部檢索系統 / Worker 居多
class DocumentChunkResponse(DocumentChunkBase):
    id: str
    embedding: Optional[List[float]] = None
    created_at: datetime
    # populate_by_name=True 允許我們用 alias ("metadata") 或原名 ("metadata_") 來存取
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# 專門給 API 回傳搜尋結果用的 Schema (不含 embedding，但多加了相似度分數)
class DocumentSearchResponse(DocumentChunkBase):
    id: str
    # 搜尋結果通常會附帶一個距離或相似度分數
    similarity_score: Optional[float] = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
