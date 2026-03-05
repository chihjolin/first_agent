import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.api.dependencies import FileServiceDep, TaskServiceDep
from src.domain.exceptions import (
    BrokerDispatchError,
    DatabaseWriteError,
    FileProcessError,
)
from src.shared.schemas.task import TaskResponse

router = APIRouter()


@router.post(
    "/upload", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_document(
    file_service: FileServiceDep,  # 注入純檔案 I/O 服務
    task_service: TaskServiceDep,  # 注入任務調度服務
    file: UploadFile = File(
        ...
    ),  # UploadFile 使用 SpooledTemporaryFile(避免記憶體爆掉)
):
    """
    上傳文件以進行解析與向量化 (Ingestion Pipeline)。
    採非同步處理，立即回傳 Task ID，請透過 /tasks/{id} 輪詢進度。
    """
    file_path = None
    try:
        # 1. 指揮 FileStorageService：驗證並將檔案寫入 Shared Volume
        # (這裡會處理檔名驗證與大檔案分塊寫入，若失敗會拋出 FileProcessError)
        file_path = await file_service.save_upload_file(file)

        # 2. 指揮 TaskService：寫入 DB 狀態 (PENDING) 並派發給 Redis
        # 到這裡 file.filename 已經被上一層確保絕對有值了，所以包一層 str() 讓型別檢查器安心
        task = await task_service.create_ingestion_task(
            file_name=str(file.filename), file_path=file_path
        )
        return task

    except FileProcessError as e:
        # 翻譯：檔案處理失敗 (如未提供檔名、寫入硬碟失敗) -> 400 Bad Request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except (DatabaseWriteError, BrokerDispatchError) as e:
        # 跨系統補償機制 (Compensation / Rollback)
        # 如果檔案已經存好了，但是 DB 寫入失敗或 Redis 派發失敗
        # 我們必須把剛才存到硬碟的檔案刪除，避免產生無法被處理的「孤兒檔案」佔用空間！
        if file_path:
            await file_service.delete_file(file_path)

        # 根據錯誤類型，精準翻譯為對應的 HTTP 狀態碼
        if isinstance(e, DatabaseWriteError):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        raise HTTPException(status_code=status_code, detail=str(e))
