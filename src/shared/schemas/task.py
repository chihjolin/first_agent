from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from src.shared.db.models import TaskStatus, TaskType


# Base: 包含所有共通的屬性
class TaskBase(BaseModel):
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# Create: API 建立任務時「只需要」給 task_type
class TaskCreate(BaseModel):
    task_type: TaskType


# Update: Worker 處理任務時，更新狀態或結果用的
class TaskUpdate(BaseModel):
    # 如果 API/Worker 沒有傳這個欄位過來，它就是 None。
    # 在我們的 CRUD 邏輯裡，None 的意思等於『請不要修改這個欄位』，而不是『把資料庫清空』
    status: Optional[TaskStatus] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# Response: API 回傳給前端的完整格式 (包含資料庫自動產生的欄位)
class TaskResponse(TaskBase):
    id: str
    created_at: datetime
    updated_at: datetime
    # 魔法屬性：讓 Pydantic 能夠直接讀取 SQLAlchemy 的 ORM 物件
    # 資料庫物件(SQLAlchemy ORM 物件) -> Pydantic Schema -> FastAPI JSON 回應
    model_config = ConfigDict(from_attributes=True)
