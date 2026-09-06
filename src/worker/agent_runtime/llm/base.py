from abc import ABC, abstractmethod
from typing import Any, Sequence

from src.worker.agent_runtime.domain.models import LLMMessage, LLMResponse


class BaseLLM(ABC):
    """
    Agent Runtime 的 LLM 抽象介面。
    定義 Agent Runtime 與 Large Language Model 之間的抽象契約。

    本模組只負責定義「Agent 需要 LLM 提供什麼能力」，
    不負責實作任何特定 LLM Provider。

    例如：
        - Ollama
        - OpenAI
        - Anthropic
        - AWS Bedrock

    皆應透過 Adapter 實作 BaseLLM。

    設計原則：
        Agent Workflow
            ↓
        BaseLLM
            ↓
        LLM Adapter
            ↓
        LiteLLM / Provider
    """

    @abstractmethod
    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Any] | None = None,
    ) -> LLMResponse:
        """
        根據對話訊息產生 LLM Response。

        Args:
            messages:
                Agent 目前的對話上下文。
                包含 system、user、assistant、tool 等訊息。

            tools:
                可選的 Tool 定義。

                如果提供 tools，
                LLM 可以根據目前問題決定是否產生 ToolCall。

        Returns:
            LLMResponse:
                統一的 Agent Runtime LLM Response。

                可能包含：
                    - content
                    - tool_calls
                    - model
                    - usage

        Note:
            這裡只定義 LLM 的能力契約，
            不關心底層實際使用的是：

                LiteLLM
                Ollama
                OpenAI
                Anthropic
                Bedrock
                ...

            Provider-specific 的 Request / Response
            轉換應由具體 Adapter 負責。
        """
        raise NotImplementedError
