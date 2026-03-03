from src.shared.db.crud.base import BaseRepository
from src.shared.db.models import Task


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session):
        super().__init__(session, Task)
