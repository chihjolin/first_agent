from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionBase(BaseModel):
    title: Optional[str] = None
    # 預設為空陣列，用來存放對話歷史 [{"role": "user", "content": "hi"}, ...]
    history: List[Dict[str, Any]] = Field(default_factory=list)


class ChatSessionCreate(ChatSessionBase):
    # 建立時可以不提供 title 或 history。
    # 若未提供 history，Pydantic 會自動填入空陣列 []。
    # DB 層 nullable=False，但因為有 default=list，不會產生 NULL。
    pass


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


# Response受眾:前端
class ChatSessionResponse(ChatSessionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
