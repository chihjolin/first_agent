from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import TaskServiceDep
from src.domain.exceptions import BrokerDispatchError, DatabaseWriteError
from src.shared.schemas.task import TaskResponse

router = APIRouter()


# 簡單定義一下前端傳過來的 Request Body 格式
class ChatRequest(BaseModel):
    query: str
    user_id: str = "anonymous"


@router.post("", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_chat_task(request: ChatRequest, task_service: TaskServiceDep):
    """
    發送對話推論請求。
    採非同步處理，立即回傳 Task ID，請透過 /tasks/{id} 輪詢結果。
    """
    try:
        # 呼叫純淨的業務邏輯
        task = await task_service.create_chat_task(
            query=request.query, user_id=request.user_id
        )
        return task

    except DatabaseWriteError as e:
        # 翻譯：資料庫層級錯誤 -> 500 伺服器內部錯誤
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except BrokerDispatchError as e:
        # 翻譯：Redis/佇列派發失敗 -> 503 服務無法使用
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
