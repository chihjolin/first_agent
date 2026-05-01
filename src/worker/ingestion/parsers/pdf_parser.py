from typing import List

import fitz  # type: ignore
from langchain_core.documents import Document

from src.shared.core.logger import get_logger
from src.worker.ingestion.parsers.base import BaseParser

logger = get_logger(__name__)


class PDFParser(BaseParser):
    """
    針對 PDF 檔案的解析器，使用 PyMuPDF (fitz) 實作。
    """

    def parse(self, file_path: str, file_name: str) -> List[Document]:
        logger.info("[PDFParser] 開始解析檔案: %s", file_name)
        documents: List[Document] = []
        try:
            # 1. 開啟 PDF 文件
            doc = fitz.open(file_path)

            # 2. 逐頁讀取
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text")

                # 3. 基礎資料清理：去除頭尾多餘空白
                text = text.strip()

                # 略過完全空白的頁面
                if not text:
                    continue

                # 4. 建立 LangChain Document，並注入 RAG 必備的 Metadata
                doc_chunk = Document(
                    page_content=text,
                    metadata={
                        "source": file_name,
                        "page": page_num + 1,  # 習慣上頁碼從 1 開始標示
                    },
                )
                documents.append(doc_chunk)

            doc.close()
            logger.info(
                "[PDFParser] 解析完成，共取出 %d 頁有內容的文字", len(documents)
            )

            return documents

        except Exception as e:
            logger.error(
                "[PDFParser] 解析 PDF 失敗 (%s): %s", file_name, str(e), exc_info=True
            )
            raise ValueError(f"無法解析 PDF 檔案 {file_name}: {str(e)}")
