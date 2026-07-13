"""GitHub 客户端和搜索工具测试。"""

from collections.abc import Callable

import httpx
import pytest

from app.core.config import Settings
from app.tools.github.client import GitHubClient
from app.tools.github.errors import GitHubAuthenticationError, GitHubRateLimitError
from app.tools.github.search import search_repositories


def build_settings(**overrides: object) -> Settings:
    """构造不依赖本地环境文件的测试配置。"""
    values = {
        "github_api_url": "https://api.github.test",
        "github_max_retries": 0,
        "github_cache_ttl_seconds": 60,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def build_client(
    handler: Callable[[httpx.Request], httpx.Response],
    **settings: object,
) -> GitHubClient:
    """使用 MockTransport 构造不会访问真实网络的客户端。"""
    return GitHubClient(
        build_settings(**settings),
        transport=httpx.MockTransport(handler),
        retry_base_delay=0,
    )


@pytest.mark.anyio
async def test_search_normalizes_and_caches_response() -> None:
    """重复查询应命中缓存，且结果字段已标准化。"""
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        assert request.url.params["q"] == "langgraph language:Python"
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [
                    {
                        "id": 1,
                        "full_name": "example/agent",
                        "name": "agent",
                        "owner": {"login": "example"},
                        "description": "Agent project",
                        "html_url": "https://github.com/example/agent",
                        "language": "Python",
                        "topics": ["langgraph"],
                        "stargazers_count": 50,
                        "forks_count": 4,
                        "open_issues_count": 2,
                        "default_branch": "main",
                        "fork": False,
                        "archived": False,
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2026-07-01T00:00:00Z",
                        "pushed_at": "2026-07-01T00:00:00Z",
                    }
                ],
            },
        )

    async with build_client(handler) as client:
        first = await search_repositories(client, "langgraph language:Python")
        second = await search_repositories(client, "langgraph language:Python")

    assert first.items[0].full_name == "example/agent"
    assert second.items[0].stars == 50
    assert request_count == 1


@pytest.mark.anyio
async def test_authentication_error_is_converted() -> None:
    """鉴权失败应转换为工作流可识别的稳定错误。"""
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    async with build_client(handler) as client:
        with pytest.raises(GitHubAuthenticationError) as error:
            await client.get_json("/user", use_cache=False)

    assert error.value.code == "github_authentication_error"
    assert error.value.status_code == 401


@pytest.mark.anyio
async def test_rate_limit_headers_are_preserved() -> None:
    """限流错误应保留重置时间，供任务调度决定恢复时机。"""
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1900000000"},
            json={"message": "API rate limit exceeded"},
        )

    async with build_client(handler) as client:
        with pytest.raises(GitHubRateLimitError) as error:
            await client.get_json("/rate_limit", use_cache=False)

    assert error.value.retryable is True
    assert error.value.rate_limit_reset == 1_900_000_000
