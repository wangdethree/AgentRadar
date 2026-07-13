"""GitHub 仓库搜索工具。"""

from app.schemas.github import RepositorySearchPage, RepositorySummary
from app.tools.github.client import GitHubClient


async def search_repositories(
    client: GitHubClient,
    query: str,
    *,
    page: int = 1,
    per_page: int = 30,
) -> RepositorySearchPage:
    """执行仓库搜索并裁剪为标准化摘要列表。"""
    if not query.strip():
        raise ValueError("GitHub 搜索语句不能为空")
    if page < 1:
        raise ValueError("页码必须大于等于 1")
    if not 1 <= per_page <= 100:
        raise ValueError("每页数量必须在 1 到 100 之间")

    payload = await client.get_json(
        "/search/repositories",
        params={"q": query, "page": page, "per_page": per_page},
    )
    return RepositorySearchPage(
        total_count=int(payload.get("total_count", 0)),
        incomplete_results=bool(payload.get("incomplete_results", False)),
        items=[RepositorySummary.from_github(item) for item in payload.get("items", [])],
    )
