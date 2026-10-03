from src.worker.agent_runtime.domain.models import LLMMessage
from src.worker.agent_runtime.llm.litellm_client import LiteLLMClient

WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "取得指定城市的天氣。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名稱。",
                }
            },
            "required": ["city"],
        },
    },
}


def test_litellm_client_tool_with_ollama():
    llm = LiteLLMClient(
        model="ollama/llama3.2",
        api_base="http://localhost:11434",
        temperature=0.0,
    )

    response = llm.generate(
        messages=[
            LLMMessage(
                role="user",
                content="請使用 get_weather 工具查詢台南的天氣。",
            ),
        ],
        tools=[WEATHER_TOOL],
    )

    print(response)

    assert response.tool_calls
    assert response.tool_calls[0].name == "get_weather"
    assert response.tool_calls[0].arguments["city"] == "台南"
