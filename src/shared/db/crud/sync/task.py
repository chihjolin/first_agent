from sqlalchemy.orm import Session

from src.shared.db.crud.sync.base import BaseSyncRepository
from src.shared.db.models import Task


class TaskSyncRepository(BaseSyncRepository[Task]):
    def __init__(self, session: Session):
        super().__init__(session, Task)
