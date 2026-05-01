from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.shared.core.logger import get_logger
from src.worker.ingestion.chunkers.base import BaseChunker

logger = get_logger(__name__)


class TextChunker(BaseChunker):
    """
    基於 LangChain 的遞迴字元切塊器。
    確保語意完整性，並在 metadata 中注入 chunk_index。
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120):
        # 初始化 LangChain 最強大的切塊器
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # 切塊優先順序：雙換行(段落) > 單換行 > 空白 > 字元
            separators=["\n\n", "\n", " ", ""],
        )

    def chunk(self, documents: List[Document]) -> List[Document]:
        logger.info("[TextChunker] 開始進行文件切塊...")

        # 1. 呼叫 LangChain 進行切塊 (它會自動保留 Parser 傳過來的 metadata 比如 page)
        splitted_docs = self.splitter.split_documents(documents)

        # 2. 關鍵步驟：注入 chunk_index，滿足 DB Schema 需求
        for index, doc in enumerate(splitted_docs):
            doc.metadata["chunk_index"] = index

        logger.info(
            "[TextChunker] 切塊完成！原始 %d 頁 -> 切割為 %d 個 Chunk",
            len(documents),
            len(splitted_docs),
        )

        return splitted_docs
