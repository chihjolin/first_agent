from typing import Iterator

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.shared.core.logger import get_logger
from src.worker.ingestion.chunkers.base import BaseChunker
from src.worker.ingestion.domain.exceptions import ChunkingException
from src.worker.ingestion.domain.models import IngestionDocument, PendingChunk

logger = get_logger(__name__)


class TextChunker(BaseChunker):

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
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

        logger.info(
            "[TextChunker] Start chunking document. doc_id=%s",
            document.doc_id,
        )

        try:

            # retrieval 與 traceability 依賴 doc_id 關聯(pipeline 一定要保證其存在)
            if not document.doc_id:
                raise ValueError("document.doc_id is required")

            # 1. 純粹的字串切塊: 利用 LangChain 的演算法進行智能切塊 (這只是內部實作，沒有污染對外的 Domain Model)
            texts = self.splitter.split_text(document.content)

            for local_index, text in enumerate(texts):

                # Recursive splitter 有時會產出"  "
                text = text.strip()

                if not text:
                    continue

                # 2. 建立乾淨的 metadata 副本 (只負責這份 document 自己知道的資訊)
                metadata = document.metadata.copy()

                # 3. 產出 PendingChunk
                yield PendingChunk(
                    doc_id=document.doc_id,
                    content=text,
                    metadata=metadata,
                    local_chunk_index=local_index,
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
