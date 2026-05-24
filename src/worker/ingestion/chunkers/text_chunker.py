import logging
from typing import Iterator

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.shared.core.config import settings
from src.worker.ingestion.chunkers.base import BaseChunker
from src.worker.ingestion.domain.exceptions import ChunkingException
from src.worker.ingestion.domain.models import IngestionDocument, PendingChunk

logger = logging.getLogger(__name__)


class TextChunker(BaseChunker):

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        # 外部沒傳就讀設定檔，外部有傳就聽外部的
        _chunk_size = chunk_size or settings.CHUNK_SIZE
        _chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap,
            separators=[
                "\n\n",  # 1.優先 paragraph
                "\n",  # 2.再 sentence-ish
                " ",  # 3.再 word
                "",  # 4.最後才 character
            ],
        )

    def chunk(
        self,
        document: IngestionDocument,
    ) -> Iterator[PendingChunk]:

        try:

            # retrieval 與 traceability 依賴 doc_id 關聯(pipeline 一定要保證其存在)
            if not document.doc_id:
                raise ValueError("document.doc_id is required")

            logger.debug(
                "[TextChunker] Start chunking. doc_id=%s content_length=%d",
                document.doc_id,
                len(document.content),
            )

            # 1. 純粹的字串切塊: 利用 LangChain 的演算法進行智能切塊 (這只是內部實作，沒有污染對外的 Domain Model)
            texts = self._splitter.split_text(document.content)

            chunk_count = 0

            for local_index, text in enumerate(texts):

                # Recursive splitter 有時會產出"  "
                text = text.strip()

                if not text:
                    continue

                # 2. 建立乾淨的 metadata 副本 (只負責這份 document 自己知道的資訊)
                metadata = document.metadata.copy()

                chunk_count += 1

                # 3. 產出 PendingChunk
                yield PendingChunk(
                    doc_id=document.doc_id,
                    content=text,
                    metadata=metadata,
                    local_chunk_index=local_index,
                )

            logger.debug(
                "[TextChunker] Completed chunking. doc_id=%s total_chunks=%d",
                document.doc_id,
                chunk_count,
            )

        except Exception as e:
            logger.error(
                "[TextChunker] Failed to chunk document. doc_id=%s error=%s",
                document.doc_id,
                str(e),
                exc_info=True,
            )

            raise ChunkingException(
                f"Failed to chunk document: {document.doc_id}"
            ) from e
