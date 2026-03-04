from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

# 定義泛型變數，代表任何 SQLAlchemy Model
ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get(self, id: str) -> Optional[ModelType]:
        # 使用 session.get() 優先查找記憶體（Identity Map），直接走 PK 查詢，效能極佳
        return await self.session.get(self.model, id)

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def save(self, obj: ModelType) -> ModelType:
        # 把 update 改名為 save，語意更精確 (同步狀態)
        self.session.add(obj)
        await self.session.flush()
        return obj
