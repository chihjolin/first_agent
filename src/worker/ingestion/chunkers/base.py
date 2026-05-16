from abc import ABC, abstractmethod
from typing import Iterator

from src.worker.ingestion.domain.models import IngestionDocument, PendingChunk

# from langchain_core.documents import Document


class BaseChunker(ABC):
    """
    文件切塊器抽象基底類別(Strategy Pattern)

    負責將單一文件切分為 Chunk 串流。

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
    - 使用 streaming(yield) 降低記憶體消耗
    - 保持 stateless，利於平行處理與策略替換

    為什麼重要：
    Chunking 是 RAG 品質的核心，
    未來極可能頻繁替換策略，
    因此必須與 framework 完全解耦。
    """

    @abstractmethod
    def chunk(
        self,
        document: IngestionDocument,
    ) -> Iterator[PendingChunk]:
        """
        將單一 IngestionDocument 切分為 PendingChunk 串流。

        Args:
            document: Pipeline 注入 doc_id 後的文件資料

        Yields:
            PendingChunk:
                - doc_id: 文件識別碼
                - content: chunk 文字內容
                - metadata: 保留來源 metadata
                - local_chunk_index: 文件內 chunk 順序
        """
        pass
