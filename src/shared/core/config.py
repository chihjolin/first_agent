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
    DATABASE_URL: str | None = None

    # 由左至右讀取，開發環境中.env.local 會覆蓋 .env
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore
