from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.file_service import FileStorageService
from src.services.task_service import TaskService
from src.shared.db.session import get_db

# ==========================================
# 1. Database Session Dependency
# ==========================================
# 將 get_db 包裝成型別標註
SessionDep = Annotated[AsyncSession, Depends(get_db)]


# ==========================================
# 2. Service Dependencies (企業級做法：隱藏 Repo，暴露 Service)
# ==========================================
def get_task_service(session: SessionDep) -> TaskService:
    # Service 內部會自己去實例化需要的 Repository
    return TaskService(session)


def get_file_service() -> FileStorageService:
    # 獨立的純 I/O 服務
    # singleton
    file_service = FileStorageService()
    return file_service


# 定義型別標註：這才是我們未來要在 Router 裡使用的終極武器！
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
FileServiceDep = Annotated[FileStorageService, Depends(get_file_service)]
