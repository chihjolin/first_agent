from src.worker.agent_runtime.domain.models import LLMMessage
from src.worker.agent_runtime.llm.litellm_client import LiteLLMClient


def test_litellm_client_with_ollama():
    llm = LiteLLMClient(
        model="ollama/llama3.2",
        api_base="http://localhost:11434",
        temperature=0.0,
    )

    response = llm.generate(
        messages=[
            LLMMessage(
                role="user",
                content="請用一句話介紹你自己。",
            )
        ]
    )

    print(response)

    assert response.content
    assert response.model
