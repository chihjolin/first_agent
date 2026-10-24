from collections.abc import Iterator

import pytest

from src.shared.db.models import ChatSession
from src.shared.db.session import get_sync_db


@pytest.fixture
def chat_session_id() -> Iterator[str]:
    """
    建立已 Commit 的測試用 ChatSession。

    Setup:
        建立 ChatSession 並 Commit，讓其他 DB Session 可以讀取。

    Teardown:
        刪除測試資料，並確認刪除結果。
    """
    # ----------------------------------------
    # 1. Setup
    # ===建立測試所需要的既有 ChatSession 資料。===
    # ----------------------------------------
    with get_sync_db() as db:
        # Transient: 建立 ORM Instance
        # 物件已存在於 Python，尚未加入 Session，尚未發送 SQL
        chat_session = ChatSession(
            title="pytest-memory-integration",
        )

        # Pending: SQLAlchemy Session 開始追蹤這個 ORM Object
        # SQLAlchemy 知道它需要 INSERT，但尚未真正執行 INSERT
        db.add(chat_session)

        # Persistent:SQLAlchemy 才真的把 SQL 傳送到 PostgreSQL
        db.flush()

        session_id = chat_session.id

    # 此時 ChatSession 已經 Commit

    # ----------------------------------------
    # 2. Test Execution
    # ----------------------------------------
    try:
        yield session_id

    # ----------------------------------------
    # 3. Teardown
    # ----------------------------------------
    finally:
        # Cleanup
        with get_sync_db() as db:
            chat_session = db.get(ChatSession, session_id)

            if chat_session is not None:
                db.delete(chat_session)

        # Verify Cleanup
        with get_sync_db() as db:
            assert (
                db.get(ChatSession, session_id) is None
            ), f"Test ChatSession was not deleted: {session_id}"
