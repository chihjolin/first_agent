import pytest

from src.shared.db.session import get_sync_db
from src.worker.agent_runtime.domain.models import LLMMessage, ToolCall
from src.worker.agent_runtime.memory.database import DatabaseMemory


def test_database_memory_persistence_across_sessions(chat_session_id: str) -> None:
    """
    Session A 寫入並 Commit。
    Session B 重新讀取，驗證 PostgreSQL Persistence。
    """
    with get_sync_db() as db:

        messages = [
            LLMMessage(
                role="user",
                content="台北天氣如何？",
            ),
            LLMMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_123",
                        name="get_weather",
                        arguments={"city": "Taipei"},
                    )
                ],
            ),
            LLMMessage(
                role="tool",
                content="台北目前晴天。",
                tool_call_id="call_123",
                name="get_weather",
            ),
            LLMMessage(
                role="assistant",
                content="台北目前是晴天。",
            ),
        ]

        # Session A：寫入 + Commit
        with get_sync_db() as db:
            memory = DatabaseMemory(db)
            for message in messages:
                memory.append(chat_session_id, message)

        # Session B：重新讀取
        with get_sync_db() as db:
            memory = DatabaseMemory(db)
            loaded_messages = memory.load(chat_session_id)
            assert loaded_messages == messages


def test_database_memory_rollback(chat_session_id: str) -> None:
    """
    驗證 Memory.append() 已 flush，
    但 Transaction 發生 Exception 時，
    PostgreSQL 不會保留該次修改。
    """
    message = LLMMessage(
        role="user",
        content="這筆訊息應該被 Rollback",
    )

    # Session A：Write + Flush + Exception
    with pytest.raises(
        RuntimeError,
        match="Simulated failure",
    ):
        with get_sync_db() as db:
            memory = DatabaseMemory(db)

            memory.append(
                chat_session_id,
                message,
            )
            # append() 內部已執行 repository.save()
            # repository.save() 已執行 flush()
            # 但尚未 Commit

            raise RuntimeError("Simulated failure")

    # Session B：Verify Rollback
    with get_sync_db() as db:
        memory = DatabaseMemory(db)
        loaded_messages = memory.load(chat_session_id)
        assert loaded_messages == []


def test_database_memory_load_missing_session() -> None:
    missing_session_id = "00000000-0000-0000-0000-000000000000"

    with get_sync_db() as db:
        memory = DatabaseMemory(db)

        with pytest.raises(
            ValueError,
            match="Chat session not found",
        ):
            memory.load(missing_session_id)
