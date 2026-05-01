from abc import ABC, abstractmethod
from typing import List

from langchain_core.documents import Document


class BaseChunker(ABC):
    """
    文件切塊器抽象基底類別 (Strategy Pattern)
    負責將大篇幅的 Document 切割成適合 Embedding 的小段落 Document。
    """

    @abstractmethod
    def chunk(self, documents: List[Document]) -> List[Document]:
        """
        將傳入的 Document 列表進行切塊處理。

        Args:
            documents (List[Document]): 原始解析出來的文件列表 (例如一頁一個 Document)

        Returns:
            List[Document]: 切塊後的文件列表，且 metadata 必須包含 chunk_index
        """
        pass
