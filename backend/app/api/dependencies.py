"""API 层共享依赖。"""

from collections.abc import AsyncIterator

from app.tools.github.client import GitHubClient


async def get_github_client() -> AsyncIterator[GitHubClient]:
    """为请求提供独立客户端并确保连接池关闭。"""
    async with GitHubClient() as client:
        yield client

