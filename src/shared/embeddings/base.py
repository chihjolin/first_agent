from abc import ABC, abstractmethod
from typing import Sequence


class BaseEmbedder(ABC):
    """定義共用文字向量化介面。"""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """將單一查詢文字轉換為向量。

        Args:
            text: 使用者輸入的查詢文字。

        Returns:
            list[float]: 查詢文字的 Embedding 向量。

        Raises:
            EmbeddingException: 向量化失敗時。
            ValueError: 輸入文字為空時。
        """
        raise NotImplementedError

    @abstractmethod
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
            EmbeddingException: 向量化失敗時。
            ValueError: 輸入包含空文字時。
        """
        raise NotImplementedError
