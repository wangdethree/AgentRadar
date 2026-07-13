"""API 层共享依赖。"""

from collections.abc import AsyncIterator

from app.core.config import get_settings
from app.providers.llm import LLMClient
from app.tools.github.client import GitHubClient


async def get_github_client() -> AsyncIterator[GitHubClient]:
    """为请求提供独立客户端并确保连接池关闭。"""
    async with GitHubClient() as client:
        yield client


async def get_llm_client() -> AsyncIterator[LLMClient | None]:
    """未配置模型时返回空依赖，工作流自动使用确定性规则。"""
    settings = get_settings()
    if not settings.llm_configured:
        yield None
        return
    async with LLMClient(settings) as client:
        yield client
