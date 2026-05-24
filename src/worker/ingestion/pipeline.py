import logging
import os
from typing import Any, Dict, List

from src.domain.exceptions import DomainFileNotFoundError
from src.shared.core.config import settings
from src.shared.db.crud.sync.document import DocumentChunkSyncRepository
from src.shared.db.models import DocumentChunk
from src.shared.db.session import get_sync_db
from src.worker.ingestion.chunkers.text_chunker import TextChunker
from src.worker.ingestion.domain.models import Chunk, IngestionDocument
from src.worker.ingestion.embedders.ollama_embedder import OllamaEmbedder
from src.worker.ingestion.parsers.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


def run_ingestion_pipeline(task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    執行文件解析與向量化流水線 (Stateful Orchestrator)
    負責協調 Parser(串流) -> Chunker(串流) -> Embedder(批次) -> DB(批次)

    Args:
        task_id (str): 任務 UUID，將直接作為文件的 doc_id 使用
        payload (Dict[str, Any]): 包含 file_path 與 file_name

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

    # 1. 實例化三大器官
    parser = PDFParser()
    chunker = TextChunker()
    embedder = OllamaEmbedder()

    # 2. 狀態與批次控制變數
    global_chunk_index = 0

    batch_size = (
        settings.EMBEDDING_BATCH_SIZE
    )  # 每 N個 Chunk 呼叫一次 Embedding 與 DB Insert

    logger.info("batch size=%d", batch_size)
    chunk_buffer: List[Chunk] = []

    logger.info("[Ingestion Pipeline] Task %s: Starting ingestion pipeline...", task_id)

    # 內部 Helper: 負責將 Buffer 清空、轉向量、並寫入 DB
    def _flush_buffer(buffer: list[Chunk]) -> None:
        if not buffer:
            return

        current_batch_size = len(buffer)

        logger.info(
            "[Ingestion Pipeline] Processing chunk batch. "
            "task_id=%s batch_size=%d accumulated_chunks=%d",
            task_id,
            current_batch_size,
            global_chunk_index,
        )

        # Phase 3: 批次轉向量
        embedded_chunks = embedder.embed_batch(buffer)

        # Phase 4: 批次寫入 PostgreSQL
        # 貫徹「短連線原則」，只有要寫入的這一瞬間才開啟 Session
        with get_sync_db() as session:
            repo = DocumentChunkSyncRepository(session)

            # 將 Domain Model 轉換為 SQLAlchemy Model
            db_records = [
                DocumentChunk(
                    document_id=ec.doc_id,
                    chunk_index=ec.chunk_index,
                    content=ec.content,
                    embedding=ec.embedding,
                    metadata_=ec.metadata,
                )
                for ec in embedded_chunks
            ]

            repo.create_many(db_records)

            # logger.debug(
            #     "[Ingestion Pipeline] 成功批次寫入 %d 筆 Chunk 進入資料庫", len(buffer)
            # )

        logger.info(
            "[Ingestion Pipeline] Batch persisted successfully. "
            "task_id=%s batch_size=%d total_chunks=%d",
            task_id,
            current_batch_size,
            global_chunk_index,
        )

        buffer.clear()  # 清空緩衝區，釋放記憶體

    # ==========================================
    # 核心資料流 (The Data Flow)
    # ==========================================
    try:
        # Phase 1: 串流解析
        parsed_stream = parser.parse(file_path, file_name)

        for parsed_doc in parsed_stream:
            # 轉換為 IngestionDocument (注入 doc_id)
            ingestion_doc = IngestionDocument(
                doc_id=task_id,
                content=parsed_doc.content,
                metadata=parsed_doc.metadata,
            )

            # Phase 2: 串流切塊
            pending_chunks = chunker.chunk(ingestion_doc)

            for pending_chunk in pending_chunks:
                # 注入全域狀態
                finalized_chunk = Chunk(
                    chunk_id=f"{task_id}:{global_chunk_index}",
                    doc_id=task_id,
                    chunk_index=global_chunk_index,
                    content=pending_chunk.content,
                    metadata=pending_chunk.metadata,
                )

                chunk_buffer.append(finalized_chunk)
                global_chunk_index += 1

                # 當緩衝區滿了，執行一次批次寫入 (Flush)
                if len(chunk_buffer) >= batch_size:
                    _flush_buffer(chunk_buffer)

        # 迴圈結束後，把剩下的尾數清空寫入
        if chunk_buffer:
            _flush_buffer(chunk_buffer)

    except Exception:
        logger.exception(
            "[Ingestion Pipeline] Task %s: Pipeline failed during execution", task_id
        )
        raise

    # 回傳 Meta 資訊給 Task 狀態機
    result_payload = {
        "file_name": file_name,
        "total_chunks": global_chunk_index,
        "embedding_model": embedder.embeddings_model.model,
        "status": "Vectorized and stored in pgvector successfully",
    }

    logger.info(
        "[Ingestion Pipeline] Task %s: Completed successfully. Total chunks: %d",
        task_id,
        global_chunk_index,
    )
    return result_payload
