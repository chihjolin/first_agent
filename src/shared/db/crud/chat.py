from src.shared.db.crud.base import BaseRepository
from src.shared.db.models import ChatSession


class ChatSessionRepository(BaseRepository[ChatSession]):
    def __init__(self, session):
        super().__init__(session, ChatSession)
