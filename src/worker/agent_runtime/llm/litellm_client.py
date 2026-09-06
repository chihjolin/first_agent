import json
from typing import Any, Sequence, cast

from litellm import completion
from litellm.types.utils import Choices, ModelResponse

from src.worker.agent_runtime.domain.models import LLMMessage, LLMResponse, ToolCall
from src.worker.agent_runtime.llm.base import BaseLLM


class LiteLLMClient(BaseLLM):
    """
    LiteLLM Adapter。

    將 Agent Runtime 的 BaseLLM Interface
    實作為 LiteLLM Python SDK。

    LiteLLM 再負責將統一的 request
    轉換到實際的 LLM Provider，
    例如 Ollama、OpenAI、Anthropic 等。
    """

    def __init__(
        self,
        model: str,
        api_base: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        """
        初始化 LiteLLM Client。

        Args:
            model:
                LiteLLM 使用的 model identifier。

                例如：
                    ollama/llama3.2

            api_base:
                Provider API endpoint。

                例如 Ollama：
                    http://localhost:11434

            temperature:
                LLM sampling temperature。
        """
        self.model = model
        self.api_base = api_base
        self.temperature = temperature

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Any] | None = None,
    ) -> LLMResponse:
        """
        執行一次非 Streaming LLM inference。

        目前 Phase 2.2 只實作最小 inference path，
        尚不處理 Tool Calling 與 Token Usage。

        流程：

            LLMMessage
                ↓
            LiteLLM request
                ↓
            completion()
                ↓
            LLMResponse
        """
        # ------------------------------------------
        # 1. 將 Domain Message 轉換為 LiteLLM format
        # ------------------------------------------
        request_messages = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
        ]

        # ------------------------------------------
        # 2. 建立 LiteLLM request
        # ------------------------------------------
        completion_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": request_messages,
            "temperature": self.temperature,
            "stream": False,
        }

        if self.api_base:
            completion_kwargs["api_base"] = self.api_base

        # if tools:
        #     completion_kwargs["tools"] = list(tools)

        # ------------------------------------------
        # 3. 呼叫 LiteLLM
        # 我們在這個 Adapter 的設計契約裡，不使用 streaming，因此這裡預期的是 ModelResponse
        # ------------------------------------------
        response = cast(
            ModelResponse,
            completion(**completion_kwargs),
        )

        # ------------------------------------------
        # 4. 取得 assistant message
        # ------------------------------------------

        choice = cast(
            Choices,
            response.choices[0],
        )

        message = choice.message

        # ------------------------------------------
        # 5. 將 Tool Calls 轉換為 Domain Model
        # ------------------------------------------
        # tool_calls = []

        # if message.tool_calls:
        #     for tool_call in message.tool_calls:
        #         tool_calls.append(
        #             ToolCall(
        #                 id=tool_call.id,
        #                 name=tool_call.function.name,
        #                 arguments=json.loads(tool_call.function.arguments),
        #             )
        #         )

        # ------------------------------------------
        # 6. 將 LiteLLM response 轉換為 Domain Model
        # ------------------------------------------
        return LLMResponse(
            content=message.content,
            tool_calls=[],
            model=response.model,
            usage={},
        )
