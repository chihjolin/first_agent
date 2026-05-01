from abc import ABC, abstractmethod
from typing import Iterator

from langchain_core.documents import Document


class BaseParser(ABC):
    """
    文件解析器抽象基底類別 (Strategy Pattern)
    所有特定格式的解析器 (PDF, Word, TXT) 都必須實作此介面。
    """

    @abstractmethod
    def parse(self, file_path: str, file_name: str) -> Iterator[Document]:
        """
        將實體檔案解析為帶有 Metadata 的 LangChain Document 陣列。

        Args:
            file_path (str): 檔案在系統中的實體路徑
            file_name (str): 原始檔案名稱 (用於 metadata)

        Returns:
            List[Document]: 解析後的純文字，通常以「頁」或「段落」為單位的 Document 列表
        """
        pass
