from sqlalchemy.orm import Session

from src.shared.db.crud.sync.base import BaseSyncRepository
from src.shared.db.models import ChatSession


class TaskSyncRepository(BaseSyncRepository[ChatSession]):
    def __init__(self, session: Session):
        super().__init__(session, ChatSession)
