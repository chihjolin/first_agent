# class DomainException(Exception):
#     """系統領域錯誤的基底類別 (Base Class)"""

#     def __init__(self, message: str):
#         self.message = message
#         # 把 message 傳給 Exception base class
#         super().__init__(self.message)


class DomainException(Exception):
    """系統領域錯誤的基底類別"""

    pass


class DatabaseWriteError(DomainException):
    """當資料庫寫入、更新或 Commit 失敗時拋出"""

    pass


class BrokerDispatchError(DomainException):
    """當 Celery 任務無法成功推送到 Redis 時拋出"""

    pass


class TaskNotFoundError(DomainException):
    """當查詢的任務 ID 不存在時拋出"""

    pass
