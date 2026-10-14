from typing import Any

from sqlalchemy.orm import Session

from src.shared.db.crud.sync.chat import ChatSessionSyncRepository
from src.worker.agent_runtime.domain.models import LLMMessage, ToolCall
from src.worker.agent_runtime.memory.base import BaseMemory


class DatabaseMemory(BaseMemory):
    """
    使用 PostgreSQL ChatSession 作為持久化儲存的 Memory。

    DatabaseMemory 負責：

        Domain LLMMessage
            ↕
        JSON-serializable dict
            ↕
        ChatSession.history

    不負責：

        - transaction commit / rollback
        - LLM inference
        - Tool execution
        - Agent orchestration

    Session lifecycle 由外部 application / worker scope 管理。
    """

    def __init__(self, session: Session) -> None:
        self.repository = ChatSessionSyncRepository(session)

    def load(
        self,
        session_id: str,
    ) -> list[LLMMessage]:
        """
        載入指定 ChatSession 的完整 conversation history。
        """
        chat_session = self.repository.get(session_id)

        if chat_session is None:
            raise ValueError(f"Chat session not found: {session_id}")

        return [self._deserialize_message(item) for item in chat_session.history]

    def append(
        self,
        session_id: str,
        message: LLMMessage,
    ) -> None:
        """
        將一筆 LLMMessage 加入指定 ChatSession 的 history。

        注意：
        此方法只 flush，不 commit。
        Transaction lifecycle 由外層 Session scope 管理。
        """
        chat_session = self.repository.get(session_id)

        if chat_session is None:
            raise ValueError(f"Chat session not found: {session_id}")

        history = list(chat_session.history)
        history.append(self._serialize_message(message))

        # 顯式重新指定整個 list，
        # 避免依賴 JSONB 的 in-place mutation detection。

        chat_session.history = history
        self.repository.save(chat_session)

    @staticmethod
    def _serialize_message(
        message: LLMMessage,
    ) -> dict[str, Any]:
        """
        將 Domain LLMMessage 轉換成 JSON-safe dict。

        只儲存有意義的 optional fields，
        因此可以相容既有的簡單 history 格式。
        """
        data: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }

        if message.tool_calls:
            data["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                }
                for tool_call in message.tool_calls
            ]

        if message.tool_call_id is not None:
            data["tool_call_id"] = message.tool_call_id

        if message.name is not None:
            data["name"] = message.name

        return data

    @staticmethod
    def _deserialize_message(
        data: dict[str, Any],
    ) -> LLMMessage:
        """
        將 ChatSession.history 中的 dict
        還原成 Domain LLMMessage。
        """
        role = data.get("role")
        if not isinstance(role, str):
            raise ValueError("Invalid stored message: role must be a string.")

        content = data.get("content")
        if content is not None and not isinstance(content, str):
            raise ValueError(
                "Invalid stored message: content must be a string or None."
            )

        tool_calls: list[ToolCall] = []
        raw_tool_calls = data.get("tool_calls", [])
        if not isinstance(raw_tool_calls, list):
            raise ValueError("Invalid stored message: tool_calls must be a list.")

        for raw_tool_call in raw_tool_calls:
            if not isinstance(raw_tool_call, dict):
                raise ValueError("Invalid stored tool call: expected an object.")

            tool_call_id = raw_tool_call.get("id")
            tool_name = raw_tool_call.get("name")
            arguments = raw_tool_call.get("arguments")

            if not isinstance(tool_call_id, str):
                raise ValueError("Invalid stored tool call: id must be a string.")

            if not isinstance(tool_name, str):
                raise ValueError("Invalid stored tool call: name must be a string.")

            if not isinstance(arguments, dict):
                raise ValueError(
                    "Invalid stored tool call: arguments must be an object."
                )

            tool_calls.append(
                ToolCall(
                    id=tool_call_id,
                    name=tool_name,
                    arguments=arguments,
                )
            )

        tool_call_id = data.get("tool_call_id")

        if tool_call_id is not None and not isinstance(tool_call_id, str):
            raise ValueError(
                "Invalid stored message: tool_call_id must be a string or None."
            )

        name = data.get("name")

        if name is not None and not isinstance(name, str):
            raise ValueError("Invalid stored message: name must be a string or None.")

        return LLMMessage(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            name=name,
        )
