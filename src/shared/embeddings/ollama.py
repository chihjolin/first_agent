import logging
from typing import Sequence

from langchain_ollama import OllamaEmbeddings

from src.shared.core.config import settings
from src.shared.embeddings.base import BaseEmbedder
from src.shared.embeddings.exceptions import EmbeddingException

logger = logging.getLogger(__name__)


class OllamaEmbedder(BaseEmbedder):
    """基於 Ollama 的文字向量化實作。"""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        expected_dimension: int | None = None,
    ) -> None:
        self._model_name = (
            model_name if model_name is not None else settings.embedding.model
        )

        _base_url = base_url if base_url is not None else settings.OLLAMA_BASE_URL

        self.expected_dimension = (
            expected_dimension
            if expected_dimension is not None
            else settings.embedding.dimension
        )

        self.embeddings_model = OllamaEmbeddings(
            model=self._model_name,
            base_url=_base_url,
        )

        logger.info(
            "[OllamaEmbedder] Initialized. model=%s expected_dimension=%d",
            self.model_name,
            self.expected_dimension,
        )

    @property
    def model_name(self) -> str:
        """取得目前使用的 Embedding 模型名稱。

        Returns:
            str: Embedding 模型名稱。
        """
        return self._model_name

    def embed_query(self, text: str) -> list[float]:
        """將單一查詢文字轉換為向量。

        Args:
            text: 使用者輸入的查詢文字。

        Returns:
            list[float]: 查詢文字的 Embedding 向量。

        Raises:
            EmbeddingException: 向量化失敗或維度不符時。
            ValueError: 輸入文字為空時。
        """
        if not text.strip():
            raise ValueError("text cannot be empty")

        logger.info(
            "[OllamaEmbedder] Starting query embedding. model=%s",
            self.model_name,
        )

        try:
            embedding = self.embeddings_model.embed_query(text)
            result = self._validate_embedding(embedding)

            logger.info(
                "[OllamaEmbedder] Query embedding completed. dimension=%d",
                len(result),
            )

            return result

        except EmbeddingException:
            raise

        except Exception as e:
            logger.exception(
                "[OllamaEmbedder] Query embedding failed. model=%s",
                self.model_name,
            )
            raise EmbeddingException("Failed to embed query") from e

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """批次將文件文字轉換為向量。

        Args:
            texts: 待向量化的文件文字序列。

        Returns:
            list[list[float]]: 與輸入順序一致的 Embedding 向量序列。

        Raises:
            EmbeddingException: 向量化失敗或維度不符時。
            ValueError: 輸入包含空文字時。
        """
        if not texts:
            logger.debug(
                "[OllamaEmbedder] Empty document batch received. "
                "Returning empty result."
            )
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("texts cannot contain empty strings")

        logger.info(
            "[OllamaEmbedder] Starting document embedding. " "model=%s batch_size=%d",
            self.model_name,
            len(texts),
        )

        try:
            embeddings = self.embeddings_model.embed_documents(list(texts))

            if len(embeddings) != len(texts):
                raise EmbeddingException(
                    "Embedding result count does not match input count: "
                    f"expected={len(texts)}, got={len(embeddings)}"
                )

            results = [self._validate_embedding(embedding) for embedding in embeddings]

            logger.info(
                "[OllamaEmbedder] Document embedding completed. "
                "model=%s batch_size=%d embedding_count=%d",
                self.model_name,
                len(texts),
                len(results),
            )

            return results

        except EmbeddingException:
            raise
        except Exception as e:
            logger.exception(
                "[OllamaEmbedder] Document embedding failed. " "model=%s batch_size=%d",
                self.model_name,
                len(texts),
            )
            raise EmbeddingException(f"Failed to embed {len(texts)} documents") from e

    def _validate_embedding(
        self,
        embedding: Sequence[float],
    ) -> list[float]:
        """驗證向量維度並正規化數值型別。

        Args:
            embedding: Provider 回傳的向量。

        Returns:
            list[float]: 經過驗證的向量。

        Raises:
            EmbeddingException: 向量維度不符合設定時。
        """
        if len(embedding) != self.expected_dimension:
            raise EmbeddingException(
                f"Embedding dimension mismatch: "
                f"expected={self.expected_dimension}, "
                f"got={len(embedding)}"
            )

        return [float(value) for value in embedding]
