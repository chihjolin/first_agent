import logging
import os
from typing import List, Sequence

from langchain_ollama import OllamaEmbeddings

from src.shared.core.config import settings
from src.worker.ingestion.domain.exceptions import EmbeddingException
from src.worker.ingestion.domain.models import Chunk, EmbeddedChunk
from src.worker.ingestion.embedders.base import BaseEmbedder

logger = logging.getLogger(__name__)


class OllamaEmbedder(BaseEmbedder):
    """
    基於 Ollama 的向量嵌入器
    """

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        expected_dimension: int | None = None,
    ):

        _model_name = model_name or settings.OLLAMA_EMBED_MODEL
        # _base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _base_url = base_url or settings.OLLAMA_BASE_URL
        self.expected_dimension = expected_dimension or settings.EMBEDDING_DIMENSION

        logger.debug(
            "[OllamaEmbedder] Initialized model=%s base_url=%s",
            _model_name,
            _base_url,
        )

        self.embeddings_model = OllamaEmbeddings(
            model=_model_name,
            base_url=_base_url,
        )

    def embed_batch(self, chunks: Sequence[Chunk]) -> List[EmbeddedChunk]:

        if not chunks:
            return []

        logger.info(
            "[OllamaEmbedder] Start embedding: chunk batch_size=%d model=%s",
            len(chunks),
            self.embeddings_model.model,
        )

        try:
            # 抽取模型真正需要的輸入資料（純文字)
            texts = [chunk.content for chunk in chunks]

            # 使用批次向量化以提升吞吐量與 GPU 利用率
            embeddings_list = self.embeddings_model.embed_documents(texts)

            # 將 embedding 結果映射回 Domain Model
            embedded_chunks = []
            for chunk, embedding in zip(chunks, embeddings_list, strict=True):

                # 驗證模型輸出的向量維度是否符合預期
                if len(embedding) != self.expected_dimension:
                    raise EmbeddingException(
                        f"Embedding dimension mismatch: "
                        f"expected={self.expected_dimension}, "
                        f"got={len(embedding)}"
                    )

                embedded_chunks.append(
                    EmbeddedChunk(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        # 避免共享 mutable metadata 導致資料污染
                        metadata=chunk.metadata.copy(),
                        # 正規化 provider-specific numeric types
                        embedding=list(
                            map(float, embedding)
                        ),  # 確保這是 List[float](infrastructure boundary 做 normalization)
                    )
                )

            logger.info(
                "[OllamaEmbedder] Completed embedding batch_size=%d",
                len(embedded_chunks),
            )

            return embedded_chunks

        except EmbeddingException:
            raise

        except Exception as e:
            logger.error(
                "[OllamaEmbedder] 批次向量化失敗: %s",
                str(e),
                exc_info=True,
            )
            raise EmbeddingException(
                f"Failed to embed batch of {len(chunks)} chunks"
            ) from e
