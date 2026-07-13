"""GitHub Issue 读取工具。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.tools.github.client import GitHubClient


class IssueSummary(BaseModel):
    """用于维护质量分析的 Issue 摘要。"""

    model_config = ConfigDict(frozen=True)

    number: int
    title: str
    state: str
    body: str | None = None
    html_url: str
    comments: int = 0
    labels: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


async def get_issues(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    limit: int = 10,
    state: str = "all",
) -> list[IssueSummary]:
    """获取最近 Issue，并排除同一接口返回的 Pull Request。"""
    payload = await client.get_json(
        f"/repos/{owner}/{repo}/issues",
        params={"per_page": min(max(limit, 1), 100), "state": state, "sort": "updated"},
    )
    issues: list[IssueSummary] = []
    for item in payload:
        if "pull_request" in item:
            continue
        labels = [
            str(label.get("name", ""))
            for label in item.get("labels", [])
            if isinstance(label, dict)
        ]
        issues.append(
            IssueSummary(
                number=int(item["number"]),
                title=str(item["title"]),
                state=str(item["state"]),
                body=str(item["body"])[:5000] if item.get("body") else None,
                html_url=str(item["html_url"]),
                comments=int(item.get("comments", 0)),
                labels=labels,
                created_at=item["created_at"],
                updated_at=item["updated_at"],
            )
        )
        if len(issues) >= limit:
            break
    return issues

