from typing import Iterator, cast

import fitz  # type: ignore

from src.shared.core.logger import get_logger
from src.worker.ingestion.domain.exceptions import ParserException
from src.worker.ingestion.domain.models import IngestionDocument
from src.worker.ingestion.parsers.base import BaseParser

# from langchain_core.documents import Document


logger = get_logger(__name__)


class PDFParser(BaseParser):
    """
    PDF 文件解析器（基於 PyMuPDF)

    設計目標：
    - 將 PDF 轉換為 IngestionDocument(Domain Model)
    - 使用 streaming(yield)避免一次載入大量資料
    - 與 LangChain 完全解耦
    """

    def parse(self, file_path: str, file_name: str) -> Iterator[IngestionDocument]:
        logger.info("[PDFParser] Start parsing file: %s", file_name)

        try:
            # 使用 context manager，確保檔案資源一定會被釋放
            # doc: fitz.Document
            with fitz.open(file_path) as doc:

                total_pages = doc.page_count
                extracted_pages = 0

                # 逐頁解析 PDF（避免一次載入）
                for page_index in range(total_pages):

                    # 取得第 page_index 頁
                    page = doc.load_page(page_index)
                    # 將 PDF page 轉為純文字
                    text = cast(str, page.get_text("text"))
                    # 基礎清理：移除前後空白
                    text = text.strip()
                    # 如果是空頁則跳過（節省後續計算資源）
                    if not text:
                        continue

                    extracted_pages += 1

                    # 回傳 domain model（不依賴 LangChain)
                    yield IngestionDocument(
                        content=text,
                        metadata={
                            "source": file_name,  # RAG trace
                            "page": page_index + 1,  # chunk 排序 (page編號習慣從1開始)
                            "file_type": "pdf",  # multi-parser
                        },
                    )

                    logger.info(
                        "[PDFParser] Completed parsing. total_pages=%d, extracted_pages=%d",
                        total_pages,
                        extracted_pages,
                    )

        except Exception as e:
            logger.error(
                "[PDFParser] Failed to parse PDF (%s): %s",
                file_name,
                str(e),
                exc_info=True,
            )
            # 統一轉為 ParserException（供上層控制 retry / logging; from e: 保留原始 stack trace
            raise ParserException(f"Failed to parse PDF: {file_name}") from e
