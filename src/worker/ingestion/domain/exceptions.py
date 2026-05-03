from src.domain.exceptions import AppException


class IngestionException(AppException):
    """Ingestion pipeline 的 base exception"""

    pass


# 未來 Celery 看到 ParserError 就不會重試 (因為檔案壞了重試100次也沒用)
class ParserException(IngestionException):
    """解析器例外，用於標記檔案損壞或格式不支援"""

    pass


class ChunkingException(IngestionException):
    pass


class EmbeddingException(IngestionException):
    pass
