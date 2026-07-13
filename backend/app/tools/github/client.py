"""GitHub REST API 异步客户端。"""

import asyncio
import json
from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.cache_service import AsyncTTLCache
from app.tools.github.errors import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubServerError,
    GitHubTimeoutError,
    GitHubTransportError,
)


class GitHubClient:
    """提供缓存、重试、限流识别和安全错误转换。"""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        retry_base_delay: float = 0.25,
    ) -> None:
        self.settings = settings or get_settings()
        self.retry_base_delay = retry_base_delay
        self.cache: AsyncTTLCache[Any] = AsyncTTLCache(
            default_ttl_seconds=self.settings.github_cache_ttl_seconds
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "AgentRadar/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        self._client = httpx.AsyncClient(
            base_url=self.settings.github_api_url.rstrip("/") + "/",
            headers=headers,
            timeout=httpx.Timeout(self.settings.github_timeout_seconds),
            transport=transport,
        )

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """关闭连接池。"""
        await self._client.aclose()

    async def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | bool] | None = None,
        use_cache: bool = True,
        cache_ttl_seconds: int | None = None,
    ) -> Any:
        """发送 GET 请求并返回 JSON，读取接口默认启用缓存。"""
        cache_key = self._build_cache_key(path, params)
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        payload = await self._request_with_retry(path, params=params)
        if use_cache:
            await self.cache.set(cache_key, payload, ttl_seconds=cache_ttl_seconds)
        return payload

    async def _request_with_retry(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | bool] | None,
    ) -> Any:
        """仅对超时、传输失败和 5xx 执行有限指数退避。"""
        attempts = self.settings.github_max_retries + 1
        last_error: GitHubAPIError | None = None

        for attempt in range(attempts):
            try:
                response = await self._client.get(path.lstrip("/"), params=params)
                return self._parse_response(response)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if isinstance(exc, httpx.TimeoutException):
                    last_error = GitHubTimeoutError(
                        "GitHub 请求超时",
                        code="github_timeout",
                        retryable=True,
                    )
                else:
                    last_error = GitHubTransportError(
                        "GitHub 网络连接失败",
                        code="github_transport_error",
                        retryable=True,
                    )
            except GitHubServerError as exc:
                last_error = exc

            if attempt < attempts - 1:
                await asyncio.sleep(self.retry_base_delay * (2**attempt))

        if last_error is None:  # pragma: no cover - 防御性分支
            raise GitHubAPIError("GitHub 请求失败")
        raise last_error

    def _parse_response(self, response: httpx.Response) -> Any:
        """将 HTTP 状态转换成稳定错误，不泄露请求头或 Token。"""
        if response.is_success:
            if response.status_code == 204:
                return {}
            try:
                return response.json()
            except json.JSONDecodeError as exc:
                raise GitHubAPIError(
                    "GitHub 返回了无法解析的响应",
                    code="github_invalid_response",
                    status_code=response.status_code,
                ) from exc

        message = self._extract_message(response)
        reset_value = response.headers.get("x-ratelimit-reset")
        rate_limit_reset = int(reset_value) if reset_value and reset_value.isdigit() else None

        if response.status_code == 401:
            raise GitHubAuthenticationError(
                message,
                code="github_authentication_error",
                status_code=401,
            )
        if response.status_code == 404:
            raise GitHubNotFoundError(message, code="github_not_found", status_code=404)
        if response.status_code == 429 or (
            response.status_code == 403
            and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GitHubRateLimitError(
                message,
                code="github_rate_limit",
                status_code=response.status_code,
                retryable=True,
                rate_limit_reset=rate_limit_reset,
            )
        if response.status_code >= 500:
            raise GitHubServerError(
                message,
                code="github_server_error",
                status_code=response.status_code,
                retryable=True,
            )
        raise GitHubAPIError(
            message,
            status_code=response.status_code,
            retryable=False,
        )

    @staticmethod
    def _extract_message(response: httpx.Response) -> str:
        """只保留 GitHub 错误消息，避免记录完整响应。"""
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return f"GitHub API 返回 HTTP {response.status_code}"
        message = payload.get("message") if isinstance(payload, dict) else None
        if isinstance(message, str):
            return message[:500]
        return f"GitHub API 返回 HTTP {response.status_code}"

    @staticmethod
    def _build_cache_key(
        path: str,
        params: Mapping[str, str | int | bool] | None,
    ) -> str:
        """使用排序后的参数构造稳定缓存键。"""
        encoded_params = json.dumps(dict(params or {}), sort_keys=True, ensure_ascii=True)
        return f"github:{path.lstrip('/')}:{encoded_params}"
