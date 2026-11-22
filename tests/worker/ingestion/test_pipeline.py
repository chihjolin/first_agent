from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.worker.ingestion import pipeline
from src.worker.ingestion.domain.models import Chunk


@pytest.fixture
def mock_components(monkeypatch):
    """建立 Pipeline 所需的 Mock 元件。"""

    # Mock Parser
    mock_parser = MagicMock()

    mock_parser.parse.return_value = [
        SimpleNamespace(
            content="Parsed Document content",
            metadata={"source": "text.pdf"},
        )
    ]

    monkeypatch.setattr(
        pipeline,
        "PDFParser",
        lambda: mock_parser,
    )

    # Mock Chunker
    mock_chunker = MagicMock()

    # mock_chunker 固定會切出 3 個 Chunk（"Chunk A"、"Chunk B"、"Chunk C"）
    def mock_chunk(document):
        return [
            SimpleNamespace(
                content="Chunk A",
                metadata={"page": 1},
            ),
            SimpleNamespace(
                content="Chunk B",
                metadata={"page": 2},
            ),
            SimpleNamespace(
                content="Chunk C",
                metadata={"page": 3},
            ),
        ]

    mock_chunker.chunk.side_effect = mock_chunk

    monkeypatch.setattr(
        pipeline,
        "TextChunker",
        lambda: mock_chunker,
    )

    # Mock Embedder
    mock_embedder = MagicMock()
    mock_embedder.model_name = "test-embedding-model"

    def mock_embed_documents(texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    # 在 Python 的 unittest.mock 規則中，只要 side_effect 不是 None，MagicMock 就會優先執行 side_effect 並完全忽略 return_value
    mock_embedder.embed_documents.side_effect = mock_embed_documents

    monkeypatch.setattr(
        pipeline,
        "OllamaEmbedder",
        lambda: mock_embedder,
    )

    # Mock DB Session
    mock_session = MagicMock()

    @contextmanager
    def mock_get_sync_db():
        yield mock_session

    monkeypatch.setattr(
        pipeline,
        "get_sync_db",
        mock_get_sync_db,
    )

    # Mock Repository
    mock_repo = MagicMock()

    monkeypatch.setattr(
        pipeline,
        "DocumentChunkSyncRepository",
        lambda session: mock_repo,
    )

    # Mock file existence
    monkeypatch.setattr(
        pipeline.os.path,
        "exists",
        lambda path: True,
    )

    return {
        "parser": mock_parser,
        "chunker": mock_chunker,
        "embedder": mock_embedder,
        "session": mock_session,
        "repo": mock_repo,
    }


@pytest.fixture
def test_payload():
    return {
        "file_path": "/tmp/test.pdf",
        "file_name": "test.pdf",
    }


def test_pipeline_success(
    monkeypatch,
    mock_components,
    test_payload,
):
    """測試 Pipeline 正常完成。"""
    monkeypatch.setattr(
        pipeline.settings.embedding,
        "batch_size",
        10,
    )

    result = pipeline.run_ingestion_pipeline(
        task_id="test-task-001",
        payload=test_payload,
    )

    assert result["total_chunks"] == 3
    assert result["embedding_model"] == "test-embedding-model"

    mock_components["embedder"].embed_documents.assert_called_once_with(
        ["Chunk A", "Chunk B", "Chunk C"]
    )

    mock_components["repo"].create_many.assert_called_once()

    records = mock_components["repo"].create_many.call_args.args[0]

    assert len(records) == 3

    assert [record.chunk_index for record in records] == [
        0,
        1,
        2,
    ]

    assert all(record.embedding is not None for record in records)


def test_pipeline_multiple_batches(
    monkeypatch,
    mock_components,
    test_payload,
):
    """測試 Chunk 數量超過 batch_size 時的批次處理。"""
    monkeypatch.setattr(
        pipeline.settings.embedding,
        "batch_size",
        2,
    )

    result = pipeline.run_ingestion_pipeline(
        task_id="test-task-002",
        payload=test_payload,
    )

    # 確認總數沒有因分批而漏算
    assert result["total_chunks"] == 3

    embedder = mock_components["embedder"]
    # 確認批次呼叫次數
    # call_count 是 MagicMock 內建的計數器屬性，專門記錄這個方法總共被呼叫了幾次。
    # 3 個 Chunk 搭配 batch_size = 2，剛好應該分 2 批呼叫 embed_documents
    assert embedder.embed_documents.call_count == 2

    # call_args_list:這是 MagicMock 的「通話紀錄本」，會按順序記下每一次呼叫時收到的參數。
    # 第 1 筆 call：call(["Chunk A", "Chunk B"])
    # 第 2 筆 call：call(["Chunk C"])
    # call_args[0]: 每筆 call 物件的 .args 是一個 tuple，裝著該次呼叫的所有位置參數（positional arguments）。embedder.embed_documents(texts)，texts 是第 0 個位置參數，所以： 第 1 次的 call.args[0] 就是 ["Chunk A", "Chunk B"] → len(call.args[0]) 等於 2。
    batch_size = [len(call.args[0]) for call in embedder.embed_documents.call_args_list]
    # 檢查「每一次」呼叫傳進去的資料筆數
    assert batch_size == [2, 1]

    repo = mock_components["repo"]

    assert repo.create_many.call_count == 2

    persisted_batch_size = [
        len(call.args[0]) for call in repo.create_many.call_args_list
    ]

    assert persisted_batch_size == [2, 1]


def test_pipeline_embedder_failure(
    monkeypatch,
    mock_components,
    test_payload,
):
    """測試 Embedder 發生錯誤時，Pipeline 應向上傳遞例外。"""
    monkeypatch.setattr(
        pipeline.settings.embedding,
        "batch_size",
        10,
    )

    # 直接覆蓋了 .side_effect = RuntimeError(...)
    mock_components["embedder"].embed_documents.side_effect = RuntimeError(
        "Embedding failed"
    )

    with pytest.raises(RuntimeError, match="Embedding failed"):
        pipeline.run_ingestion_pipeline(
            task_id="test-task-003",
            payload=test_payload,
        )

    mock_components["repo"].create_many.assert_not_called()


def test_pipeline_embedding_count_mismatch(
    monkeypatch,
    mock_components,
    test_payload,
):
    """測試 Embedder 回傳數量不符時，不應寫入資料庫。"""
    monkeypatch.setattr(
        pipeline.settings.embedding,
        "batch_size",
        10,
    )

    # 先清空 side_effect
    mock_components["embedder"].embed_documents.side_effect = None
    # 再指定 return_value
    mock_components["embedder"].embed_documents.return_value = [
        [0.1, 0.2, 0.3],
    ]

    with pytest.raises(ValueError, match="Embedding count mismatch"):
        pipeline.run_ingestion_pipeline(
            task_id="test-task-004",
            payload=test_payload,
        )

    mock_components["repo"].create_many.assert_not_called()
