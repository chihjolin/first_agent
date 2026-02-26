FROM python:3.12-slim

WORKDIR /app

# 安裝系統依賴 (給 psycopg2 等套件編譯使用)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 安裝 Poetry
RUN pip install poetry

# 複製依賴描述檔
COPY pyproject.toml poetry.lock* /app/

# 設定 Poetry 不建立虛擬環境 (因為 Container 本身就是隔離的)，並安裝套件
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev --no-root

# 複製所有原始碼進去
COPY ./src /app/src

# 設定環境變數確保 Python 能找到 src 目錄
ENV PYTHONPATH=/app