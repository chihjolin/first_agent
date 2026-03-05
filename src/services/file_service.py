import os
import uuid

import aiofiles  # type: ignore
import aiofiles.os  # type: ignore
from fastapi import UploadFile

from src.domain.exceptions import FileProcessError
from src.shared.core.logger import get_logger

logger = get_logger(__name__)


class FileStorageService:
    """
    專責處理 Ingestion 流程中的檔案 I/O 與驗證
    """

    def __init__(self):
        # 設定檔案儲存路徑 (對應到 docker-compose 的 Volume 掛載點)
        self.upload_dir = "temp_uploads"
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_upload_file(self, file: UploadFile) -> str:
        """
        處理檔案上傳：驗證檔名 -> 儲存至 Shared Volume -> 回傳絕對/相對路徑
        """
        logger.info(f"Receiving file upload: {file.filename}")

        if not file.filename:
            raise FileProcessError("未提供檔案名稱，無法處理上傳請求。")

        # 這裡可以加入更多驗證，例如副檔名檢查
        # if not file.filename.endswith(".pdf"):
        #     raise FileProcessError("目前僅支援 PDF 檔案上傳。")

        # 資安防禦 1: 防範 Path Traversal (路徑穿越攻擊)
        # 即使駭客傳入 "../../../etc/passwd"，basename 也會把它洗成 "passwd"
        safe_filename = os.path.basename(file.filename)

        # 資安防禦 2: 防範 Filename Collision (檔名衝突覆蓋)
        # 加上 UUID 前綴，確保每個檔案都是獨一無二的
        unique_name = f"{uuid.uuid4()}_{safe_filename}"

        file_path = os.path.join(self.upload_dir, unique_name)

        try:
            # 效能優化: 使用 aiofiles 進行非同步 chunk 寫入，不阻塞主執行緒
            async with aiofiles.open(file_path, "wb") as f:
                # 每次讀取 1MB (1024 * 1024 bytes)
                while chunk := await file.read(1024 * 1024):
                    await f.write(chunk)

            # HTTP Request -> temporary file -> UploadFile
            # 關掉FastAPI 的 UploadFile，避免temporary file descriptor 可能殘留
            await file.close()

            logger.info(f"File {safe_filename} successfully saved to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {str(e)}")
            raise FileProcessError(f"檔案寫入 Volume 失敗。詳細原因: {str(e)}")

    async def delete_file(self, file_path: str):
        """
        (可選) 補償機制：如果後續派發任務失敗，Router 可以呼叫這個方法把剛存好的檔案刪掉，避免佔用空間
        """
        # 效能優化: 使用 aiofiles.os.path.exists 與 aiofiles.os.remove 達成全非同步
        if await aiofiles.os.path.exists(file_path):
            try:
                await aiofiles.os.remove(file_path)
                logger.info(f"Rollback: Deleted file {file_path}")
            except Exception as e:
                # 即使刪除失敗也只記錄 Log，不要引發 Exception 蓋過原本 Router 正在處理的錯誤(DatabaseWriteError, BrokerDispatchError)
                logger.warning(
                    f"Failed to rollback (delete) file {file_path}: {str(e)}"
                )
