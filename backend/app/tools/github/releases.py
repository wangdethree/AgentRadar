"""GitHub Release 读取工具。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.tools.github.client import GitHubClient


class ReleaseSummary(BaseModel):
    """用于升温原因分析的 Release 摘要。"""

    model_config = ConfigDict(frozen=True)

    tag_name: str
    name: str | None = None
    body: str | None = None
    html_url: str
    published_at: datetime | None = None
    prerelease: bool = False


async def get_releases(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    limit: int = 5,
) -> list[ReleaseSummary]:
    """获取最近 Release，并裁剪过长说明。"""
    payload = await client.get_json(
        f"/repos/{owner}/{repo}/releases",
        params={"per_page": min(max(limit, 1), 100)},
    )
    return [
        ReleaseSummary(
            tag_name=str(item.get("tag_name", "")),
            name=str(item["name"]) if item.get("name") else None,
            body=str(item["body"])[:5000] if item.get("body") else None,
            html_url=str(item.get("html_url", "")),
            published_at=item.get("published_at"),
            prerelease=bool(item.get("prerelease", False)),
        )
        for item in payload[:limit]
    ]

