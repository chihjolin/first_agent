from dataclasses import dataclass
from typing import Any, Dict, List

# dataclass: 定義 ingestion pipeline 的資料契約（Data Contract)
# slots=True: 降低記憶體，提升 attribute access，止亂塞 attribute


@dataclass(slots=True)
class ParsedDocument:
    content: str
    metadata: Dict[str, Any]


@dataclass(slots=True)
class IngestionDocument:
    # doc_id 由「pipeline」注入
    doc_id: str
    content: str
    metadata: Dict[str, Any]


@dataclass(slots=True)
class PendingChunk:
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    local_chunk_index: int


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any]


@dataclass(slots=True)
class EmbeddedChunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]
