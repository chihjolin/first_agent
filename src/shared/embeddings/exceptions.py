from src.domain.exceptions import AppException


class EmbeddingException(AppException):
    """Embedding 向量化過程發生錯誤。"""
