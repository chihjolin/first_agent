from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.orm import DeclarativeBase, Session

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseSyncRepository(Generic[ModelType]):

    def __init__(self, session: Session, model: Type[ModelType]):
        self.session = session
        self.model = model

    def get(self, id: str) -> Optional[ModelType]:
        return self.session.get(self.model, id)

    def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.flush()
        return obj

    def save(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.flush()
        return obj
