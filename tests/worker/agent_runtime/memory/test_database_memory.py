from src.shared.db.models import ChatSession
from src.shared.db.session import get_sync_db
from src.worker.agent_runtime.domain.models import LLMMessage, ToolCall
from src.worker.agent_runtime.memory.database import DatabaseMemory


def test_database_memory_round_trip():
    with get_sync_db() as db:

        # ===建立測試所需要的既有 ChatSession 資料。===
        # Transient: 建立 ORM Instance
        # 物件已存在於 Python，尚未加入 Session，尚未發送 SQL
        chat_session = ChatSession()

        # Pending: SQLAlchemy Session 開始追蹤這個 ORM Object
        # SQLAlchemy 知道它需要 INSERT，但尚未真正執行 INSERT
        db.add(chat_session)

        # Persistent:SQLAlchemy 才真的把 SQL 傳送到 PostgreSQL
        db.flush()

        # DatabaseMemory 並不負責建立新的 ChatSession，它只負責對既有 ChatSession 操作 Memory。
        memory = DatabaseMemory(db)

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

        for message in messages:
            memory.append(chat_session.id, message)

        lodaded_messages = memory.load(chat_session.id)

        assert lodaded_messages == messages
