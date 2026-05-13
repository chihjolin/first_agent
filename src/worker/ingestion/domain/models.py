from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# dataclass: 定義 ingestion pipeline 的資料契約（Data Contract)


@dataclass
class IngestionDocument:
    content: str
    metadata: Dict[str, Any]
    # doc_id 應該由「pipeline 控制」，不是 parser
    doc_id: Optional[str] = None  # (?)


@dataclass
class Chunk:
    content: str
    metadata: Dict[str, Any]
    doc_id: str  # (?)
    chunk_index: int


@dataclass
class EmbeddedChunk:
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    embedding: List[float]
