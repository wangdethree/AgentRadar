"""OpenAI-compatible 模型客户端测试。"""

import json

import httpx
import pytest

from app.core.config import Settings
from app.providers.llm import LLMClient, LLMProviderError
from app.schemas.search import ParsedRequirement


def llm_response(content: dict[str, object], *, tokens: int = 23) -> httpx.Response:
    """构造标准 Chat Completions JSON 响应。"""
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": {"total_tokens": tokens},
        },
    )


@pytest.mark.anyio
async def test_llm_client_validates_structured_response_and_usage() -> None:
    """客户端应附带鉴权、校验 Schema 并返回 Token 用量。"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["response_format"] == {"type": "json_object"}
        return llm_response(
            {
                "topics": ["LangGraph"],
                "languages": ["Python"],
                "preferred_technologies": ["FastAPI"],
                "required_capabilities": ["tool calling"],
                "difficulty": "intermediate",
                "goal": "learn",
                "excluded_features": [],
            }
        )

    settings = Settings(
        _env_file=None,
        llm_api_key="test-key",
        llm_base_url="https://llm.test/v1",
        llm_model="test-model",
    )
    async with LLMClient(settings, transport=httpx.MockTransport(handler)) as client:
        result = await client.generate_structured(
            "解析需求",
            ParsedRequirement,
            operation="parse_requirement",
        )

    assert result.data.topics == ["LangGraph"]
    assert result.data.languages == ["Python"]
    assert result.total_tokens == 23


@pytest.mark.anyio
async def test_llm_client_retries_server_error() -> None:
    """临时服务端错误应在预算内重试。"""
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": "temporary"})
        return llm_response({"topics": ["AI Agent"]})

    settings = Settings(
        _env_file=None,
        llm_base_url="https://llm.test/v1/chat/completions",
        llm_model="test-model",
        llm_max_retries=1,
    )
    async with LLMClient(settings, transport=httpx.MockTransport(handler)) as client:
        result = await client.generate_structured(
            "解析需求",
            ParsedRequirement,
            operation="parse_requirement",
        )

    assert attempts == 2
    assert result.data.topics == ["AI Agent"]


@pytest.mark.anyio
async def test_llm_client_rejects_invalid_schema() -> None:
    """不符合业务 Schema 的模型输出不能进入工作流。"""

    def handler(_: httpx.Request) -> httpx.Response:
        return llm_response({"difficulty": "impossible"})

    settings = Settings(
        _env_file=None,
        llm_base_url="https://llm.test/v1",
        llm_model="test-model",
        llm_max_retries=0,
    )
    async with LLMClient(settings, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMProviderError) as captured:
            await client.generate_structured(
                "解析需求",
                ParsedRequirement,
                operation="parse_requirement",
            )

    assert captured.value.code == "llm_invalid_schema"
