from src.domain.exceptions import AppException
from src.shared.embeddings.exceptions import EmbeddingException


class IngestionException(AppException):
    """Ingestion pipeline 的 base exception"""

    pass


# 未來 Celery 看到 ParserError 就不會重試 (因為檔案壞了重試100次也沒用)
class ParserException(IngestionException):
    """解析器例外，用於標記檔案損壞或格式不支援"""

    pass


class ChunkingException(IngestionException):
    """文件切塊過程發生錯誤（例如 chunking 策略失敗或內容異常）"""

    pass
