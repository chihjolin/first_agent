from typing import Iterator

from src.shared.core.logger import get_logger
from src.worker.ingestion.chunkers.base import BaseChunker
from src.worker.ingestion.domain.exceptions import ChunkingException
from src.worker.ingestion.domain.models import Chunk, IngestionDocument

# from langchain_core.documents import Document
# from langchain_text_splitters import RecursiveCharacterTextSplitter


logger = get_logger(__name__)


class TextChunker(BaseChunker):
    """
    基礎文字切塊器(Character-based Chunking)

    設計目標：
        - 將長文本切分為適合 embedding 的 chunk
        - 保留 chunk overlap，降低語意斷裂
        - 與 framework 完全解耦
        - 使用 streaming(yield)降低記憶體使用

    注意：
    目前使用 character-based chunking(MVP)
    未來可升級：
        - token-aware chunking
        - semantic chunking
        - markdown-aware chunking
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        初始化 Chunker

        Args:
            chunk_size:
                每個 chunk 最大字元數

            chunk_overlap:
                chunk 間重疊字元數

        overlap設計目的:
        embedding model 沒有「記憶」，overlap 可以保留語意連續性。
        """

        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        document: IngestionDocument,
    ) -> Iterator[Chunk]:

        logger.info(
            "[TextChunker] Start chunking document. doc_id=%s",
            document.doc_id,
        )
        """
        將 IngestionDocument 切成多個 Chunk

        為什麼用 Iterator(yield)?

        因為：
        - chunk 數量可能非常大
        - 不想一次建立整個 list
        - 可以 streaming pipeline

        Parser:
            yield document

        Chunker:
            yield chunk

        Embedder:
            consume chunk

        整條 pipeline 可以做到：
            「邊解析 → 邊切塊 → 邊 embedding」

        非常省記憶體。
        """

        try:
            text = document.content

            # doc_id 非常重要，未來 retrieval 時：chunk -> doc，都靠 doc_id 關聯，所以 pipeline 一定要保證存在。
            if not document.doc_id:
                raise ValueError("document.doc_id is required")

            doc_id = document.doc_id

            if not text.strip():
                return

            chunk_index = 0

            # chunk 起點
            start = 0

            while start < len(text):

                # chunk 終點: min()避免超出文字長度
                end = min(
                    start + self.chunk_size,
                    len(text),
                )
                chunk_text = text[start:end].strip()

                # 跳過空chunk
                if not chunk_text:
                    start = end
                    continue

                # 建立 chunk metadata(不要直接修改：document.metadata["xxx"] = yyy，避免污染原始 document。所以用dict copy)
                metadata = {
                    **document.metadata,
                    "chunk_index": chunk_index,
                    "chunk_start": start,
                    "chunk_end": end,
                }

                yield Chunk(
                    content=chunk_text,
                    metadata=metadata,
                    doc_id=document.doc_id or "",
                    chunk_index=chunk_index,
                )

                chunk_index += 1

                # 下一段起點: start = end - overlap，保留語意完整性
                start = end - self.chunk_overlap

            logger.info(
                "[TextChunker] Completed chunking. total_chunks=%d",
                chunk_index,
            )

        except Exception as e:
            logger.error(
                "[TextChunker] Failed to chunk document: %s",
                str(e),
                exc_info=True,
            )

            raise ChunkingException(
                f"Failed to chunk document: {document.doc_id}"
            ) from e
