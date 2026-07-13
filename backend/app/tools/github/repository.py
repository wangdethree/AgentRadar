"""GitHub 仓库详情与文件工具。"""

from app.schemas.github import RepositorySummary
from app.tools.github.client import GitHubClient
from app.tools.github.content import GitHubFileContent, parse_file_content


async def get_repository(client: GitHubClient, owner: str, repo: str) -> RepositorySummary:
    """读取单个仓库最新信息。"""
    payload = await client.get_json(f"/repos/{owner}/{repo}")
    return RepositorySummary.from_github(payload)


async def get_file_content(
    client: GitHubClient,
    owner: str,
    repo: str,
    path: str,
    *,
    ref: str | None = None,
    max_bytes: int = 200_000,
) -> GitHubFileContent:
    """读取单个文本文件并限制交给模型的最大体积。"""
    params = {"ref": ref} if ref else None
    payload = await client.get_json(f"/repos/{owner}/{repo}/contents/{path}", params=params)
    return parse_file_content(payload, max_bytes=max_bytes)


async def get_languages(client: GitHubClient, owner: str, repo: str) -> dict[str, int]:
    """获取各语言对应的代码字节数。"""
    payload = await client.get_json(f"/repos/{owner}/{repo}/languages")
    return {str(language): int(bytes_count) for language, bytes_count in payload.items()}


async def get_contributors(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    limit: int = 10,
) -> list[dict[str, str | int]]:
    """获取贡献者摘要，不保留头像等无关字段。"""
    payload = await client.get_json(
        f"/repos/{owner}/{repo}/contributors",
        params={"per_page": min(max(limit, 1), 100)},
    )
    return [
        {
            "login": str(item.get("login", "")),
            "contributions": int(item.get("contributions", 0)),
            "html_url": str(item.get("html_url", "")),
        }
        for item in payload[:limit]
    ]


async def get_commit_activity(
    client: GitHubClient,
    owner: str,
    repo: str,
) -> list[dict[str, object]]:
    """获取 GitHub 聚合的最近 52 周提交活动。"""
    payload = await client.get_json(
        f"/repos/{owner}/{repo}/stats/commit_activity",
        cache_ttl_seconds=3600,
    )
    return [
        {
            "week": int(item.get("week", 0)),
            "total": int(item.get("total", 0)),
            "days": [int(value) for value in item.get("days", [])],
        }
        for item in payload
    ]

