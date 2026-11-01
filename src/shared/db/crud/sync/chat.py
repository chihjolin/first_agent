from sqlalchemy import select
from sqlalchemy.orm import Session

from src.shared.db.crud.sync.base import BaseSyncRepository
from src.shared.db.models import ChatSession


class ChatSessionSyncRepository(BaseSyncRepository[ChatSession]):
    def __init__(self, session: Session) -> None:
        """初始化 ChatSession Repository。

        Args:
            session: SQLAlchemy 同步 Session，由外部管理生命週期。

        Returns:
            None。
        """
        super().__init__(session, ChatSession)

    def get_for_update(
        self,
        session_id: str,
    ) -> ChatSession | None:
        pass
        """查詢並鎖定指定的 ChatSession。

        使用 PostgreSQL SELECT FOR UPDATE 取得資料列排他鎖，
        避免其他 Transaction 同時修改相同的 ChatSession。

        Lock 會持續到目前 Transaction Commit 或 Rollback。

        Args:
            session_id: 要查詢並鎖定的 ChatSession 主鍵。

        Returns:
            ChatSession | None: 查詢到的 ORM 物件；不存在時回傳 None。

        Raises:
            SQLAlchemyError: 資料庫查詢或連線失敗時。
        """
        stmt = (
            select(ChatSession).where(ChatSession.id == session_id)
            # PostgreSQL: FOR UPDATE Lock，處理資料庫並行寫入
            .with_for_update()
            # populate_existing=True：處理 SQLAlchemy Session 內可能存在的舊 ORM 狀態。要求 SQLAlchemy 使用查詢結果重新填入 ORM 物件的屬性。
            .execution_options(populate_existing=True)
        )

        return self.session.scalar(stmt)
