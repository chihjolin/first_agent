from abc import ABC, abstractmethod
from typing import Iterator

from src.worker.ingestion.domain.models import Chunk, IngestionDocument

# from langchain_core.documents import Document


class BaseChunker(ABC):
    """
    文件切塊器抽象基底類別(Strategy Pattern)

    設計目的：
    - 定義「文件 → Chunk」的統一介面
    - 支援不同 chunking 策略
        - fixed-size chunking
        - semantic chunking
        - markdown-aware chunking
        - token-aware chunking
    - 與 Pipeline 解耦，讓 chunking 策略可自由替換

    設計重點：
    - 不依賴 LangChain / LlamaIndex
    - 僅使用系統內部定義的 Domain Model
    - 使用 streaming(yield)避免大量記憶體消耗

    為什麼重要：
    Chunking 是 RAG 品質的核心，
    未來極可能頻繁替換策略，
    因此必須與 framework 完全解耦。
    """

    @abstractmethod
    def chunk(
        self,
        documents: IngestionDocument,
    ) -> Iterator[Chunk]:
        """
        將 IngestionDocument 切分為 Chunk(串流輸出)

        Args:
            document (IngestionDocument):
                Parser 產出的文件資料

        Yields:
            Chunk:
                - content: chunk 後的文字內容
                - metadata: 保留來源 metadata
                - doc_id: 文件識別碼
                - chunk_index: chunk 在文件中的順序
        """
        pass
