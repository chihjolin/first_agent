from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionBase(BaseModel):
    title: Optional[str] = None
    # 預設為空陣列，用來存放對話歷史 [{"role": "user", "content": "hi"}, ...]
    history: List[Dict[str, Any]] = Field(default_factory=list)


class ChatSessionCreate(ChatSessionBase):
    pass  # 建立時可以給 title 和 history，也可以都不給(全空)


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


# Response受眾:前端
class ChatSessionResponse(ChatSessionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
