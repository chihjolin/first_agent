"""
架構決策紀錄 (Architecture Decision Record - ADR)

背景：
在微服務架構的初期開發階段，建立獨立的測試資料庫 (Test DB) 會增加維運成本與拉長測試回饋時間。

決策：
本測試模組採用「共用開發資料庫 + 巢狀事務 (Nested Transaction / Savepoint)」策略。
測試直接連線至 Dev DB，但在最外層包覆一個不提交的 Transaction。

影響：
1. [優勢] 開發便捷：開發者無須額外啟動 Test DB 容器即可光速執行單元測試。
2. [安全] 資料隔離：透過 SQLAlchemy 2.0 的 `create_savepoint`，測試內的 `commit()` 僅在子層生效，
   測試結束後外層強制 `rollback()`，保證不污染開發環境的真實資料。
3. [限制] 未來演進：當專案進入 CI/CD 流水線，或有多人協作時，此機制會有併發干擾風險。
   屆時應將連線字串抽換為 Testcontainers 或 Ephemeral DB (一次性資料庫)。
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db.crud.task import TaskRepository
from src.shared.db.models import Task, TaskStatus, TaskType

# 引入真實的 engine
from src.shared.db.session import async_engine


@pytest_asyncio.fixture
async def db_session():
    """
    企業級的測試資料庫防護機制：
    使用 Connection 綁定，並開啟巢狀事務 (Savepoint)。
    這樣測試裡面就算呼叫了 session.commit()，也只是釋放 Savepoint，
    最後外層的 transaction.rollback() 會把所有變更徹底抹除！
    """
    # 1. 建立獨立連線
    async with async_engine.connect() as conn:
        # 2. 開啟外層的「總事務」
        transaction = await conn.begin()

        # 3. 綁定 Session，開啟 SAVEPOINT 模式，允許測試內部安全地模擬 commit
        async with AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,  # 關鍵就在這
        ) as session:
            yield session

        # 4. 測試結束，無條件回滾「總事務」，確保資料庫 100% 乾淨
        await transaction.rollback()


@pytest.mark.asyncio
async def test_task_crud_lifecycle(db_session):
    repo = TaskRepository(db_session)

    # --- 1. 測試 Create ---
    task = Task(task_type=TaskType.INGESTION)
    await repo.create(task)
    # 模擬真實 API 的 Commit 行為 (觸發 DB 真實寫入)
    await db_session.commit()

    assert task.id is not None
    assert task.status == TaskStatus.PENDING

    # --- 2. 測試 Get (確保是從 DB 真實撈出，而不是從記憶體緩存) ---
    fetched = await repo.get(task.id)
    assert fetched is not None
    assert fetched.id == task.id

    # --- 3. 測試 Update ---
    fetched.status = TaskStatus.COMPLETED
    fetched.result = {"msg": "Done"}

    await repo.save(fetched)
    await db_session.commit()

    assert fetched.status == TaskStatus.COMPLETED
    assert fetched.result == {"msg": "Done"}
