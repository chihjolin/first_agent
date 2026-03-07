from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import TaskServiceDep
from src.domain.exceptions import TaskNotFoundError
from src.shared.schemas.task import TaskResponse

router = APIRouter()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str, task_service: TaskServiceDep):
    """
    查詢特定任務的執行狀態與結果
    """
    try:
        # Router 盲目信任 Service，拿到什麼就回傳什麼
        task = await task_service.get_task_status(task_id)
        return task
    except TaskNotFoundError as e:
        # 將領域例外翻譯為 HTTP 404 Not Found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
