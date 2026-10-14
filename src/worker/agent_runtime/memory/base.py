from abc import ABC, abstractmethod
from typing import Sequence

from src.worker.agent_runtime.domain.models import LLMMessage


class BaseMemory(ABC):
    """
    Agent Runtime 的 Memory 抽象介面。

    Memory 負責管理 Agent 的 conversation history，
    不負責 LLM inference、Tool execution 或 workflow orchestration。
    """

    @abstractmethod
    def load(
        self,
        session_id: str,
    ) -> Sequence[LLMMessage]:
        """
        載入指定 Session 的完整 conversation history。
        """
        raise NotImplementedError

    @abstractmethod
    def append(
        self,
        session_id: str,
        message: LLMMessage,
    ) -> None:
        """
        將一筆 LLMMessage 加入指定 Session 的 history。
        """
        raise NotImplementedError
