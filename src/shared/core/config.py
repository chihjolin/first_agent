from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 環境標籤 (預設為 production，本地開發靠 .env.local 覆寫為 local)
    ENVIRONMENT: str = "production"
    # 資料庫設定 (不給預設值，強迫設定檔必須提供)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_HOST_PORT: int  # 本機port
    POSTGRES_PORT: int  # 容器port

    # Docker 啟動時會自動讀取系統環境變數覆蓋這個 None(預設值 None，所以設定檔沒寫也不會報錯)
    DATABASE_URL_ASYNC: str | None = None
    DATABASE_URL_SYNC: str | None = None

    REDIS_URL: str = f"redis://localhost:6379/0"  # 本機開發用

    # 賦予本機預設值。
    # 當在 Docker 內執行時，會自動被 docker-compose 注入的 http://ollama:11434 覆寫！
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Chunking
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Embedding
    EMBEDDING_BATCH_SIZE: int = 100
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768

    # 由左至右讀取，開發環境中.env.local 會覆蓋 .env
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore
