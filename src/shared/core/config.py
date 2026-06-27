from functools import cached_property

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChunkingConfig(BaseModel):
    chunk_size: int
    chunk_overlap: int


class EmbeddingConfig(BaseModel):
    batch_size: int
    model: str
    dimension: int


class Settings(BaseSettings):
    ENVIRONMENT: str

    # Atomic Config (暫時保留)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_HOST_PORT: int  # 本機port
    POSTGRES_PORT: int  # 容器port

    # Connection URLs(實際程式使用)
    DATABASE_URL_ASYNC: str
    DATABASE_URL_SYNC: str
    REDIS_URL: str
    OLLAMA_BASE_URL: str

    # Chunking
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int

    # Embedding
    EMBEDDING_BATCH_SIZE: int
    OLLAMA_EMBED_MODEL: str
    EMBEDDING_DIMENSION: int

    # 優先級:
    # 系統環境變數 > .env.local > .env > class default
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @cached_property
    def chunking(self) -> ChunkingConfig:
        return ChunkingConfig(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
        )

    @cached_property
    def embedding(self) -> EmbeddingConfig:
        return EmbeddingConfig(
            batch_size=self.EMBEDDING_BATCH_SIZE,
            model=self.OLLAMA_EMBED_MODEL,
            dimension=self.EMBEDDING_DIMENSION,
        )


settings = Settings()  # type: ignore
