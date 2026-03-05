import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.api.dependencies import TaskServiceDep
from src.domain.exceptions import BrokerDispatchError, DatabaseWriteError
from src.shared.schemas.task import TaskResponse

router = APIRouter()

# 設定一個暫存上傳檔案的資料夾 (MVP 階段先存在本機)
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/upload", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_document(task_service: TaskServiceDep, file: UploadFile = File(...)):
    """
    上傳文件以進行解析與向量化 (Ingestion Pipeline)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供檔案名稱")

    # 1. 將檔案暫存到伺服器本地 (真實環境可能會上傳至 AWS S3 / MinIO)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檔案儲存失敗: {str(e)}")

    # 2. 呼叫 Service 建立任務並派發到 Celery
    try:
        task = await task_service.create_ingestion_task(
            file_name=file.filename,
            file_path=file_path,
        )
        return task

    except DatabaseWriteError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except BrokerDispatchError as e:
        raise HTTPException(status_code=500, detail=str(e))
