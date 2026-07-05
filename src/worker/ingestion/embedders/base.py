from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import List

from src.worker.ingestion.domain.models import Chunk, EmbeddedChunk


class BaseEmbedder(ABC):
    """
    向量嵌入器抽象基底類別（Strategy Pattern）。

    實作必須：
    - 保持輸入與輸出順序一致
    - 不修改原始 Chunk
    - 回傳數量必須與輸入一致
    """

    @abstractmethod
    def embed_batch(self, chunks: Sequence[Chunk]) -> List[EmbeddedChunk]:
        """
        將「批次」的 Chunk 轉換為 EmbeddedChunk。

        設計原因：
        - 向量模型 (API/GPU) 對於批次 (Batch) 處理的效能遠大於逐筆 (1-to-1) 處理。
        - 透過 Pipeline 收集固定數量的 Chunk 後，一次性交由本介面處理。

        Args:
            chunks: 一批已完成 chunk_id 與 chunk_index 注入的 Chunk 列表

        Returns:
            List[EmbeddedChunk]: 帶有 embedding 向量的列表
        """
        pass
