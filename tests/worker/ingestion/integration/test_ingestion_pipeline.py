import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from src.shared.db.models import DocumentChunk
from src.shared.db.session import get_sync_db
from src.worker.ingestion.pipeline import run_ingestion_pipeline

pytestmark = pytest.mark.integration


@pytest.fixture
def test_pdf_path() -> Path:
    """取得整合測試使用的 PDF 路徑。"""
    pdf_path = os.getenv("INGESTION_TEST_PDF")

    if not pdf_path:
        pytest.skip("INGESTION_TEST_PDF is not configured")

    path = Path(pdf_path)

    if not path.is_file():
        pytest.skip(f"Test PDF does not exist: {path}")

    return path


def test_ingestion_pipeline_persists_embeddings(
    test_pdf_path: Path,
):
    """使用真實 Ollama 與 PostgreSQL 驗證向量寫入。"""

    task_id = str(uuid4())

    payload = {
        "file_path": str(test_pdf_path),
        "file_name": test_pdf_path.name,
    }

    try:
        # Arrange & Act:
        # 使用真實 Parser、Chunker、Embedder 與 PostgreSQL。
        result = run_ingestion_pipeline(
            task_id=task_id,
            payload=payload,
        )

        assert result["total_chunks"] > 0
        assert result["embedding_model"]

        # Assert:
        # 從資料庫重新讀取，確認資料確實持久化。
        with get_sync_db() as session:
            rows = session.execute(
                select(
                    DocumentChunk,
                    # 驗證 PostgreSQL pgvector 欄位中的實際向量維度
                    func.vector_dims(DocumentChunk.embedding).label(
                        "embedding_dimension"
                    ),
                )
                .where(DocumentChunk.document_id == task_id)
                .order_by(DocumentChunk.chunk_index)
            ).all()

            records = [row[0] for row in rows]

            dimensions = [row.embedding_dimension for row in rows]

            assert len(records) == result["total_chunks"]

            assert all(record.embedding is not None for record in records)

            assert all(dimension == 768 for dimension in dimensions)

            assert [record.chunk_index for record in records] == list(
                range(len(records))
            )

            assert all(record.document_id == task_id for record in records)

            assert all(len(record.embedding) == 768 for record in records)

            assert all(
                isinstance(record.content, str) and record.content.strip()
                for record in records
            )

    finally:
        # Cleanup:
        # 僅刪除本次測試產生的 Chunk。
        with get_sync_db() as session:
            session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == task_id)
            )
