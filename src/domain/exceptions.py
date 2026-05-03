class AppException(Exception):
    """整個系統的 base exception"""

    pass


class InfrastructureException(AppException):
    """DB / Redis / 外部服務"""

    pass


class DomainException(AppException):
    """業務邏輯錯誤"""

    pass


# class DomainException(Exception):
#     """系統領域錯誤的基底類別"""

#     pass


# class DatabaseWriteError(DomainException):
#     """當資料庫寫入、更新或 Commit 失敗時拋出"""

#     pass


# class BrokerDispatchError(DomainException):
#     """當 Celery 任務無法成功推送到 Redis 時拋出"""

#     pass


class DatabaseWriteError(InfrastructureException):
    """當資料庫寫入、更新或 Commit 失敗時拋出"""

    pass


class BrokerDispatchError(InfrastructureException):
    """當 Celery 任務無法成功推送到 Redis 時拋出"""

    pass


class TaskNotFoundError(DomainException):
    """當查詢的任務 ID 不存在時拋出"""

    pass


class FileProcessError(DomainException):
    """當上傳檔案儲存、讀取或驗證失敗時拋出"""

    pass


class DomainFileNotFoundError(DomainException):
    """ingestion worker找不到檔案時拋出"""

    pass


class InvalidTaskStateTransition(DomainException):
    """worker狀態轉換不合法時拋出"""

    pass
