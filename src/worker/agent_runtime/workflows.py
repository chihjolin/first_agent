"""
Agent Inference Workflow 業務邏輯

工作流程：接收使用者 Query -> 檢索 Context (RAG) -> 呼叫 LLM -> 儲存對話紀錄 -> 回傳結果
"""

import logging
import time
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.shared.db.crud.sync.chat import ChatSessionSyncRepository
from src.shared.db.session import get_sync_db

logger = logging.getLogger(__name__)


def run_agent_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    執行 AI Agent 推論與回應流水線

    Args:
        payload (Dict[str, Any]): 包含 user_id 與 query 等推論參數

    Returns:
        Dict[str, Any]: 推論結果與 Token 消耗量 (將寫入 Task.result)
    """

    logger.info("[Inference Worker] Starting agent workflow")
    query = payload.get("query")

    if not query:
        raise ValueError("Payload missing required field: 'query'")

    logger.info("[Inference Workflow] User query received: '%s'", query)

    # 1. 模擬耗時的 LLM 推論與 API 呼叫 (不佔用資料庫連線)
    time.sleep(5)
    answer = f"你好！這是針對「{query}」的模擬 AI 回覆。"

    # TODO: (feature/05) 這裡未來會接上 LangChain 與 Vector DB
    # 2. 只有在需要儲存對話歷史時，才開啟極短的 DB 連線
    # with get_sync_db() as session:
    #     repo = ChatSessionSyncRepository(session)
    #     repo.save_message(...)

    result_payload = {
        "answer": answer,
        "model": "gpt-4o-mock",
        "usage": {"total_tokens": 150},
    }

    logger.info("[Inference Workflow] Workflow completed successfully")
    return result_payload
