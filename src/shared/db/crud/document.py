from typing import List, Optional, Sequence

from sqlalchemy import insert, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db.crud.base import BaseRepository
from src.shared.db.models import DocumentChunk


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DocumentChunk)

    async def create_many(self, chunks: List[DocumentChunk]) -> None:
        """
        大量新增切塊 (Ingestion Worker 會呼叫這個)
        High-Performance Bulk Insert (略過 ORM 追蹤，專注寫入速度)
        這對於動輒幾千筆切塊的 Ingestion 流程極度重要。
        """
        # 將 ORM 物件轉為純字典陣列
        # [sqlalchemy 2.0 官方推薦]mapper: col.attrs只包含 ORM 真正 mapped 的欄位，不會抓 relationship，hybrid property，computed property
        mapper = inspect(DocumentChunk)
        values = [
            {
                attr.key: value
                for attr in mapper.column_attrs
                # 避免在created at為None的情況下覆寫pg的server_default
                if (value := getattr(chunk, attr.key)) is not None
            }
            for chunk in chunks
        ]
        # Write optimized path
        # [sqlalchemy 2.0 官方推薦]Bulk Insert
        await self.session.execute(insert(DocumentChunk), values)
        await self.session.flush()

    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 5,
        # 加上過濾條件，避免全表掃描炸掉 DB
        document_id: Optional[str] = None,
    ) -> Sequence[DocumentChunk]:
        """
        向量相似度搜尋 (Inference Worker / RAG 會呼叫這個)，距離越小代表越相似
        使用 pgvector 的 cosine_distance 運算子 (<=>) 進行排序
        底層的 pgvector 會把這單一一個 A 廣播 (Broadcast) 出去，
        去跟資料表裡的每一筆 B1, B2, B3 計算距離並排序。所以 input 只需要你當下的那個「查詢向量」
        """
        stmt = select(DocumentChunk)

        # 動態加入過濾條件 (RAG 系統的標準做法)
        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        stmt = stmt.order_by(
            DocumentChunk.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        # Read optimized path
        # .all() 在 SQLAlchemy 2.0 的型別標註是Sequence[DocumentChunk]
        # Sequence 是抽象類型（具體類型如tuple / list 都符合）
        # result = await self.session.execute(stmt)
        # return result.scalars().all()

        # 優化點 3：使用 session.scalars(stmt) 簡化代碼
        # 這等同於 await self.session.execute(stmt) 接著 .scalars()
        result = await self.session.scalars(stmt)
        return result.all()
