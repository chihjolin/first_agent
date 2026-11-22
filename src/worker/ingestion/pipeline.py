import logging
import os
from typing import Any, Dict, List

from src.domain.exceptions import DomainFileNotFoundError
from src.shared.core.config import settings
from src.shared.db.crud.sync.document import DocumentChunkSyncRepository
from src.shared.db.models import DocumentChunk
from src.shared.db.session import get_sync_db
from src.shared.embeddings.ollama import OllamaEmbedder
from src.worker.ingestion.chunkers.text_chunker import TextChunker
from src.worker.ingestion.domain.models import Chunk, EmbeddedChunk, IngestionDocument
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

    Raises:
        ValueError: 任務 Payload 不完整時。
        DomainFileNotFoundError: Worker 找不到指定檔案時。
        Exception: 文件解析、向量化或資料庫操作失敗時。
    """
    file_path = payload.get("file_path")
    file_name = payload.get("file_name")

    if not file_path or not file_name:
        raise ValueError(
            f"Invalid payload. file_path={file_path}, file_name={file_name}"
        )

    logger.info(
        "[Ingestion Pipeline] Task %s: Verifying file. file_name=%s",
        task_id,
        file_name,
    )

    # 實體檔案防呆檢查：驗證 Docker Volume 是否真的有掛載成功！
    if not os.path.exists(file_path):
        raise DomainFileNotFoundError(f"Worker 無法在路徑 {file_path} 找到檔案")

    logger.info(
        "[Ingestion Pipeline] Task %s: File verified. "
        "Starting ingestion. file_name=%s",
        task_id,
        file_name,
    )

    # 1. 實例化三大器官
    parser = PDFParser()
    chunker = TextChunker()
    embedder = OllamaEmbedder()

    # 2. 狀態與批次控制變數
    global_chunk_index = 0

    batch_size = (
        settings.embedding.batch_size
    )  # 每 N個 Chunk 呼叫一次 Embedding 與 DB Insert

    chunk_buffer: List[Chunk] = []

    logger.info(
        "[Ingestion Pipeline] Task %s: Pipeline initialized. "
        "embedding_model=%s batch_size=%d",
        task_id,
        embedder.model_name,
        batch_size,
    )

    # 內部 Helper: 負責將 Buffer 清空、轉向量、並寫入 DB
    def _flush_buffer(buffer: list[Chunk]) -> None:
        """將目前累積的 Chunk 批次向量化並寫入資料庫。

        Args:
            buffer: 等待處理的 Chunk 緩衝區。

        Raises:
            Exception: 向量化或資料庫寫入失敗時。
        """
        if not buffer:
            return

        current_batch_size = len(buffer)

        logger.info(
            "[Ingestion Pipeline] Task %s: Starting batch processing. "
            "batch_size=%d total_chunks=%d",
            task_id,
            current_batch_size,
            global_chunk_index,
        )

        # Phase 3: 批次轉向量
        texts = [chunk.content for chunk in buffer]

        logger.debug(
            "[Ingestion Pipeline] Task %s: Starting embedding. " "batch_size=%d",
            task_id,
            current_batch_size,
        )

        embeddings = embedder.embed_documents(texts)

        if len(embeddings) != current_batch_size:
            # 防止 Embedder 實作未遵守介面契約。
            raise ValueError(
                "Embedding count mismatch: "
                f"expected={current_batch_size}, got={len(embeddings)}"
            )

        embedded_chunks = [
            EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                metadata=chunk.metadata.copy(),
                embedding=embedding,
            )
            for chunk, embedding in zip(buffer, embeddings, strict=True)
        ]

        logger.info(
            "[Ingestion Pipeline] Task %s: Embedding completed. " "embedding_count=%d",
            task_id,
            len(embedded_chunks),
        )

        # Phase 4: 批次寫入 PostgreSQL
        logger.debug(
            "[Ingestion Pipeline] Task %s: Starting database persistence. "
            "batch_size=%d",
            task_id,
            current_batch_size,
        )

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

        logger.info(
            "[Ingestion Pipeline] Task %s: Batch persisted successfully. "
            "batch_size=%d total_chunks=%d",
            task_id,
            current_batch_size,
            global_chunk_index,
        )

        # 成功完成向量化及 DB 寫入後才清空 Buffer
        buffer.clear()  # 清空緩衝區，釋放記憶體

    # ==========================================
    # 核心資料流 (The Data Flow)
    # ==========================================
    try:
        # Phase 1: 串流解析
        logger.info(
            "[Ingestion Pipeline] Task %s: Starting PDF parsing.",
            task_id,
        )
        parsed_stream = parser.parse(file_path, file_name)

        parsed_document_count = 0

        for parsed_doc in parsed_stream:
            parsed_document_count += 1
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

        logger.info(
            "[Ingestion Pipeline] Task %s: PDF parsing completed. "
            "parsed_documents=%d total_chunks=%d",
            task_id,
            parsed_document_count,
            global_chunk_index,
        )

        # 處理最後不足一個 Batch 的剩餘 Chunk
        if chunk_buffer:
            logger.info(
                "[Ingestion Pipeline] Task %s: Flushing remaining chunks. "
                "remaining_chunks=%d",
                task_id,
                len(chunk_buffer),
            )
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
        "embedding_model": embedder.model_name,
        "status": "Vectorized and stored in pgvector successfully",
    }

    logger.info(
        "[Ingestion Pipeline] Task %s: Pipeline completed successfully. "
        "total_chunks=%d embedding_model=%s",
        task_id,
        global_chunk_index,
        embedder.model_name,
    )

    return result_payload
