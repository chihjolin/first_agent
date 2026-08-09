from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class LLMMessage:
    """
    LLM 對話訊息的 Domain Contract。

    這是 Agent Runtime 自己定義的 Message 格式，
    不直接使用 LangChain 的 HumanMessage / AIMessage / ToolMessage。
    後續由 LLM Adapter 負責將這個 Domain Model 轉換成 LiteLLM / LangChain 所需要的格式。

    例如：

        LLMMessage(
            role="user",
            content="如何開立證券戶？"
        )

    role 預期包含：
        - system
        - user
        - assistant
        - tool

    content：
        實際訊息內容。
    """

    role: str
    content: str


@dataclass(slots=True)
class ToolCall:
    """
    LLM 要求執行 Tool 時所產生的 Tool Call Contract。

    例如 LLM 決定：

        search_knowledge_base(
            query="開立證券戶條件"
        )

    就可以轉換成：

        ToolCall(
            id="call_123",
            name="search_knowledge_base",
            arguments={
                "query": "開立證券戶條件"
            },
        ),

    注意：
    ToolCall 只描述「LLM 想做什麼」， 不負責實際執行 Tool。
    """

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass(slots=True)
class LLMResponse:
    """
    LLM 推論結果的 Domain Contract。

    用來隔離不同 LLM Provider 的 Response 格式。

    例如 LiteLLM、Ollama、OpenAI 等 Provider 最後都應該被 Adapter 正規化成這個格式。

    content：
        LLM 產生的文字內容。

    tool_calls：
        如果 LLM 決定呼叫 Tool， 則會在這裡提供 ToolCall。

    model：
        實際使用的模型名稱。

    usage：
        Token 使用量等資訊。 不同 Provider 提供的欄位可能不同， 因此使用 Dict 保留彈性。
    """

    content: Optional[str]
    tool_calls: List[ToolCall] = field(default_factory=list)

    model: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """
    Tool 執行結果的 Domain Contract。

    ToolCall 描述： 「LLM 要做什麼」
    ToolResult 描述： 「Tool 實際做完後得到什麼」

    例如：
        ToolResult(
            tool_call_id="call_123",
            name="search_knowledge_base",
            content="開立證券戶需要準備..."
        )

    tool_call_id：
        用來對應原本的 ToolCall。

    name：
        實際執行的 Tool 名稱。

    content：
        Tool 回傳給 Agent / LLM 的結果。

    is_error：
        表示 Tool 執行是否失敗。
    """

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


@dataclass(slots=True)
class AgentResult:
    """
    Agent Workflow 最終輸出的 Domain Contract。

    這是整個 Agent Runtime 對外傳遞的最終推論結果。

    例如：

        AgentResult(
            answer="開立證券戶需要準備...",
            model="llama3.1",
            usage={"total_tokens": 250},
        )

    answer：
        Agent 最終回覆給使用者的文字。

    model：
        最終使用的 LLM。

    usage：
        Token 使用量等資訊。

    tool_calls：
        本次 Agent 推論過程中使用過的 Tool， 可用於 logging、debugging、observability。

    metadata：
        保留額外的 workflow metadata， 例如 latency、retrieved_documents 等資訊。
    """

    answer: str
    model: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[ToolCall] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
