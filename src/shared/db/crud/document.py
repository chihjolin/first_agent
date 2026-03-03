from typing import List, Optional

from sqlalchemy import insert, select
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
        values = [
            {
                column.name: getattr(chunk, column.name)
                for column in DocumentChunk.__table__.columns
            }
            for chunk in chunks
        ]
        # Write optimized path
        await self.session.execute(insert(DocumentChunk).values(values))
        await self.session.flush()

    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 5,
        # 加上過濾條件，避免全表掃描炸掉 DB
        document_id: Optional[str] = None,
    ) -> List[DocumentChunk]:
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
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
