from abc import ABC, abstractmethod
from typing import Iterator

from src.worker.ingestion.domain.models import IngestionDocument

# from langchain_core.documents import Document


class BaseParser(ABC):
    """
    文件解析器抽象基底類別 (Strategy Pattern)

    設計目的：
    - 定義「檔案 → 結構化文字資料」的統一介面
    - 支援多種資料來源(PDF / Word / TXT / URL)
    - 與上層 Pipeline 解耦，讓 Parser 可自由替換

    設計重點：
    本層「不依賴任何第三方框架(例如 LangChain)」，
    僅回傳系統內部定義的 IngestionDocument(Domain Model)。

    這樣的好處：
    - 未來可替換 LangChain / LlamaIndex / 自研 pipeline
    - Parser 不會被特定框架綁死
    - 提高系統可維護性與可擴展性
    """

    @abstractmethod
    def parse(self, file_path: str, file_name: str) -> Iterator[IngestionDocument]:
        """
        將實體檔案解析為系統內部的 IngestionDocument(串流輸出）。

        設計說明：
        - 使用 Iterator (yield) 逐頁 / 逐段產出資料
        - 避免一次載入整份文件造成記憶體爆炸(OOM)
        - 適用於大型檔案（例如數百頁 PDF)

        Args:
            file_path (str): 檔案在系統中的實體路徑
            file_name (str): 原始檔案名稱（用於 metadata)

        Yields:
            IngestionDocument:
                - content: 純文字內容
                - metadata: 與來源相關的資訊（例如 page、source)
        """
        pass
