from concurrent.futures import ThreadPoolExecutor
from threading import Event

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


def test_database_memory_concurrent_append(
    chat_session_id: str,
) -> None:
    """驗證兩個獨立 Transaction 並行追加訊息時不會遺失更新。

    使用 ThreadPoolExecutor 模擬兩個並行的資料庫工作單位，
    並透過 Event 控制第一個 Transaction 的 Commit 時機。

    測試限制：
        second_started 僅代表 Thread B 已開始執行，
        不保證已抵達 SELECT FOR UPDATE。
        因此本測試驗證並行寫入結果，但不是確定性的
        Lock Contention Test，單次通過無法證明 B 曾等待 Row Lock。

    Args:
        chat_session_id: Fixture 建立並提交的 ChatSession 主鍵。

    Returns:
        None。

    Raises:
        AssertionError: 訊息遺失、內容不符或同步訊號逾時。
        TimeoutError: Thread 等待提交訊號或 Future 結果逾時。
        Exception: Worker Thread 執行期間發生的其他例外。
    """
    # Event 是 Python Threading 提供的同步工具，它主要用來讓不同 Thread 彼此通知：
    # 某件事情已經發生了。可以把 Event 理解成一個只有兩種狀態的訊號：(False：尚未觸發，True：已觸發)
    # 建立 Event，初始狀態是：False
    first_flushed = Event()
    allow_first_commit = Event()
    second_started = Event()

    message_a = LLMMessage(
        role="user",
        content="Message A",
    )

    message_b = LLMMessage(
        role="user",
        content="Message B",
    )

    def append_first() -> None:
        """追加第一筆訊息並暫時保持 Transaction 開啟。

        Returns:
            None。

        Raises:
            TimeoutError: 等待 Commit 訊號逾時。
        """
        with get_sync_db() as db:
            memory = DatabaseMemory(db)

            memory.append(
                chat_session_id,
                message_a,
            )

            # append 已 flush，且持有 Row Lock
            # event.set(): 將 Event 設定為已觸發。
            first_flushed.set()

            # event.wait(): 如果 Event 尚未觸發，就等待。這段程式會持續等待，直到其他 Thread 執行：event.set()。回傳值是True，代表 Event 已觸發。通常會加入 Timeout，避免無限等待。
            # Main Thread allow_first_commit尚未觸發，所以 Thread A 會停在這裡。(Thread A 雖然暫停執行 Python 程式，但它的 SQLAlchemy Transaction 仍然開啟。PostgreSQL Row Lock 仍然存在。)
            if not allow_first_commit.wait(timeout=10):
                raise TimeoutError("Timed out waiting to commit A")

        # 離開 with 後 Commit，釋放 Row Lock

    def append_second() -> None:
        """使用另一個 Session 追加第二筆訊息。

        Returns:
            None。

        Raises:
            Exception: 資料庫查詢或寫入失敗。
        """
        # 通知 Main Thread: Thread B 已開始執行。(不代表 Thread B 已經開始執行 SQL。)
        second_started.set()

        with get_sync_db() as db:
            memory = DatabaseMemory(db)

            # 如果 Thread A 仍然持有該 Row Lock，Thread B 就必須等待。等 Thread A Commit 後，Thread B 才能取得鎖，讀取最新的 History，追加 Message B。最後 Thread B Commit。
            memory.append(
                chat_session_id,
                message_b,
            )

    # 1. 建立一個 Thread Pool，最多使用兩個 Worker Thread 執行工作。
    with ThreadPoolExecutor(max_workers=2) as executor:

        # 2. 啟動 Thread A
        # submit() 會把 Function 與參數提交給 Thread Pool
        # 相當於要求：請找一個可用的 Worker Thread 執行該 Function
        # Future:它代表一個可能尚未完成的工作。(Pending, Running, Finished)
        future_a = executor.submit(append_first)

        future_b = None

        try:
            # 3. Main Thread 等待 A 完成 Flush並持有 Row Lock。
            # 它確保：在啟動 Thread B 之前，Thread A 已經完成 append / flush。因此我們知道 Thread A 已經取得 Row Lock，而且尚未 Commit。
            assert first_flushed.wait(
                timeout=10
            ), "First transaction did not flush in time"

            # 4. 啟動 Thread B
            future_b = executor.submit(append_second)

            # 5. 等待 B 的啟動訊號，確保 Thread B 至少已經執行到：second_started.set(),
            # 但尚不能保證它已經執行 SELECT FOR UPDATE。
            assert second_started.wait(
                timeout=10
            ), "Second transaction did not start in time"

            # 此時 A 尚未 Commit，B 已開始嘗試執行。
            # 不使用 sleep() 作為正確性的判斷依據。

        finally:
            # 6. 允許 A Commit
            # 當 Main Thread 執行 allow_first_commit.set()，Thread A 的：allow_first_commit.wait()就會結束等待。接著離開with get_sync_db() as db:觸發db.commit()，PostgreSQL 提交 Transaction，釋放 Row Lock。

            # 即使 Main Thread assertion 失敗，也要讓 A 有機會結束，避免測試本身造成永久等待。
            allow_first_commit.set()

        # 7. 等待兩個 Thread 完成
        # Future.result(): 如果工作還沒完成，Main Thread 會等待；如果工作成功，回傳 Function 的結果。如果 Worker Thread 裡發生 Exception，`result()` 會在呼叫端重新拋出該 Exception，確保 Worker 的 Exception 能讓 pytest 判定測試失敗。

        # 如果任何一個 Thread 發生 Exception，測試會失敗。如果超過指定等待時間，`Future.result()` 會拋出 concurrent.futures.TimeoutError。但它不會自動終止仍在執行的 Thread，因此每個 Thread 內部的等待也應有合理的 Timeout。
        future_a.result(timeout=15)

        if future_b is not None:
            future_b.result(timeout=15)

    # 重新建立 Session，確認兩筆訊息都已持久化。
    with get_sync_db() as db:
        memory = DatabaseMemory(db)

        loaded_messages = memory.load(chat_session_id)

        assert len(loaded_messages) == 2

        assert {message.content for message in loaded_messages} == {
            "Message A",
            "Message B",
        }
