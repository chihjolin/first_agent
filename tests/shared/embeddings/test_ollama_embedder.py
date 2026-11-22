from unittest.mock import MagicMock

import pytest

from src.shared.embeddings.exceptions import EmbeddingException
from src.shared.embeddings.ollama import OllamaEmbedder


@pytest.fixture
def mock_ollama_embeddings(monkeypatch):
    mock_model = MagicMock()

    monkeypatch.setattr(
        "src.shared.embeddings.ollama.OllamaEmbeddings",
        lambda **kwargs: mock_model,
    )

    return mock_model


@pytest.fixture
def embedder(mock_ollama_embeddings):
    return OllamaEmbedder(
        model_name="test-model",
        base_url="http://localhost:11434",
        expected_dimension=3,
    )


def test_embed_query_success(
    embedder,
    mock_ollama_embeddings,
):
    """測試單一 Query 向量化成功。"""
    mock_ollama_embeddings.embed_query.return_value = [
        0.1,
        0.2,
        0.3,
    ]

    result = embedder.embed_query("What is AI?")

    assert result == [0.1, 0.2, 0.3]

    mock_ollama_embeddings.embed_query.assert_called_once_with("What is AI?")


def test_embed_query_empty_text(embedder):
    """測試空白 Query 應拒絕執行。"""
    with pytest.raises(ValueError):
        embedder.embed_query("   ")


def test_embed_query_dimension_mismatch(
    embedder,
    mock_ollama_embeddings,
):
    """測試 Query 向量維度不符。"""
    mock_ollama_embeddings.embed_query.return_value = [
        0.1,
        0.2,
    ]

    with pytest.raises(EmbeddingException):
        embedder.embed_query("What is AI?")


def test_embed_query_provider_error(
    embedder,
    mock_ollama_embeddings,
):
    """測試 Provider 發生錯誤時的例外轉換。"""
    mock_ollama_embeddings.embed_query.side_effect = RuntimeError(
        "Provider unavailable"
    )

    with pytest.raises(EmbeddingException):
        embedder.embed_query("What is AI?")


def test_embed_documents_success(
    embedder,
    mock_ollama_embeddings,
):
    """測試批次文件向量化成功。"""
    mock_ollama_embeddings.embed_documents.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]

    texts = [
        "Document A",
        "Document B",
    ]

    result = embedder.embed_documents(texts)

    assert result == [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]

    mock_ollama_embeddings.embed_documents.assert_called_once_with(texts)


def test_embed_documents_empty_batch(
    embedder,
    mock_ollama_embeddings,
):
    """測試空批次應回傳空列表。"""
    result = embedder.embed_documents([])

    assert result == []

    mock_ollama_embeddings.embed_documents.assert_not_called()


def test_embed_documents_contains_empty_text(
    embedder,
):
    """測試批次輸入包含空文字。"""
    with pytest.raises(ValueError):
        embedder.embed_documents(
            [
                "Document A",
                "    ",
            ]
        )


def test_embed_documents_result_count_mismatch(
    embedder,
    mock_ollama_embeddings,
):
    """測試 Provider 回傳數量與輸入數量不一致。"""
    mock_ollama_embeddings.embed_documents.return_value = [
        [0.1, 0.2, 0.3],
    ]

    with pytest.raises(EmbeddingException):
        embedder.embed_documents(
            [
                "Document A",
                "Document B",
            ]
        )


def test_embed_documents_dimension_mismatch(
    embedder,
    mock_ollama_embeddings,
):
    """測試批次向量中有向量維度不符合設定。"""
    mock_ollama_embeddings.embed_documents.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5],
    ]

    with pytest.raises(EmbeddingException):
        embedder.embed_documents(
            [
                "Document A",
                "Document B",
            ]
        )
