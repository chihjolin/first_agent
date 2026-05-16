from abc import ABC, abstractmethod
from typing import Iterator

from src.worker.ingestion.domain.models import ParsedDocument


class BaseParser(ABC):
    """
    文件解析器抽象基底類別(Strategy Pattern)。

    負責將不同來源的檔案(PDF / Word / TXT / URL)
    解析為系統內部統一的 Domain Model。

    設計原則：
    - 與上層 Pipeline 解耦
    - 不暴露第三方框架型別
    - 使用 streaming(yield) 降低記憶體消耗
    """

    @abstractmethod
    def parse(
        self,
        file_path: str,
        file_name: str,
    ) -> Iterator[ParsedDocument]:
        """
        將實體檔案解析為 ParsedDocument 串流。

        設計說明：
        - 使用 Iterator (yield) 逐頁 / 逐段產出資料
        - 避免一次載入整份文件造成記憶體爆炸(OOM)
        - 適用於大型檔案（例如數百頁 PDF)

        Args:
            file_path (str): 檔案在系統中的實體路徑
            file_name (str): 原始檔案名稱（用於 metadata)

        Yields:
            ParsedDocument:
                - content: 純文字內容
                - metadata: 與來源相關的資訊(例如 page、source)
        """
        pass
