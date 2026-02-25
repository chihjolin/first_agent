#!/bin/sh
# 如果任何命令執行失敗（回傳非 0 的 Exit Code），立即中止腳本
set -e

export OLLAMA_HOST_URL=http://${OLLAMA_HOST}:${OLLAMA_PORT}

# # --- 1. 等待 Ollama 服務就緒 ---
# echo "Waiting for Ollama API..."

# until curl -s $OLLAMA_HOST_URL/api/tags > /dev/null; do
#   sleep 2
# done

# echo "Ollama ready!"

# 由於 docker-compose 已經設定了 service_healthy 等待，
# 執行到這裡時，ollama 伺服器保證已經是 ready 的狀態了。

# --- 2. 檢查並pull models ---

echo "Starting Ollama models initialization..."
pull_if_not_exists () {
    MODEL=$1
    # 檢查模型是否已經存在
    if ! ollama list | grep -q "$MODEL"; then
        echo "Model $MODEL not found. Pulling..."
        ollama pull "$MODEL"
        echo "Model $MODEL pulled successfully!"
    else
        echo "Model $MODEL already exists. Skipping."
    fi
}

# 依序檢查並下載需要的模型
pull_if_not_exists "llama3.2"
pull_if_not_exists "nomic-embed-text"

echo "All Ollama models are initialized and ready to use!"