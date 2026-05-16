"""
Document Ingestion Pipeline 業務邏輯

工作流程：驗證實體檔案 -> 解析文件 (Load) -> 文件切塊 (Chunk) -> 呼叫 Embedding 模型 -> 寫入 Vector DB
"""

import os
import time
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.domain.exceptions import DomainFileNotFoundError
from src.shared.core.logger import get_logger
from src.shared.db.crud.sync.document import DocumentChunkSyncRepository
from src.shared.db.session import get_sync_db

logger = get_logger(__name__)


def run_ingestion_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    執行文件解析與向量化流水線
    stateful orchestrator

    Args:
        payload (Dict[str, Any]):
            file_path: 實體檔案在 Volume 中的絕對路徑
            file_name: 原始檔案名稱

    Returns:
        Dict[str, Any]: 處理完成的 Meta 資訊 (將寫入 Task.result)
    """
    file_path = payload.get("file_path")
    file_name = payload.get("file_name")

    if not file_path or not file_name:
        raise ValueError(
            f"Invalid payload. file_path={file_path}, file_name={file_name}"
        )

    logger.info("[Ingestion Worker] Verifying file: %s", file_name)

    # 實體檔案防呆檢查：驗證 Docker Volume 是否真的有掛載成功！
    if not os.path.exists(file_path):
        raise DomainFileNotFoundError(f"Worker 無法在路徑 {file_path} 找到檔案")

    logger.info(
        "[Ingestion Worker] File verified. Starting parsing for %s...", file_name
    )

    # TODO: (feature/05) 這裡未來會接上 PyMuPDF 與 Embedding 模型
    # 模擬耗時的 PDF 解析與 Embedding 呼叫 (不佔用資料庫連線)
    time.sleep(8)  # MVP 階段模擬 PDF 切塊與 Embedding 的時間

    """
    parser = PDFParser()
    chunker = TextChunker()

    global_chunk_index = 0

    parsed_stream = parser.parse(file_path, file_name)

    for parsed_doc in parsed_stream:

        ingestion_doc = IngestionDocument(
            doc_id=task_id,
            content=parsed_doc.content,
            metadata=parsed_doc.metadata,
        )

        pending_chunks = chunker.chunk(ingestion_doc)

        for pending_chunk in pending_chunks:

            finalized_chunk = Chunk(
                chunk_id=f"{task_id}:{global_chunk_index}",
                doc_id=task_id,
                chunk_index=global_chunk_index,
                content=pending_chunk.content,
                metadata={
                    **pending_chunk.metadata,
                    "global_chunk_index": global_chunk_index,
                },
            )

            global_chunk_index += 1

            yield finalized_chunk
    """

    # 3. 只有在真正需要寫入 Chunk 時，才開啟極短的 DB 連線
    # with get_sync_db() as session:
    #     repo = DocumentChunkSyncRepository(session)
    #     repo.create_many([DocumentChunk(content=c.text, embedding=e) for c, e in zip(chunks, embeddings)])

    # 模擬向量化完成的 Meta 資訊
    result_payload = {
        "file_name": file_name,
        "total_chunks": 42,
        "embedding_model": "text-embedding-3-small-mock",
        "status": "Vectorized and stored in pgvector",
    }

    logger.info("[Ingestion Pipeline] Pipeline completed successfully")

    return result_payload
