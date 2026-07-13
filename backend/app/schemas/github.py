"""GitHub API 的标准化数据结构。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RepositorySummary(BaseModel):
    """屏蔽 GitHub 原始字段差异后的仓库摘要。"""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    github_id: int
    full_name: str
    name: str
    owner: str
    description: str | None = None
    html_url: str
    language: str | None = None
    topics: list[str] = Field(default_factory=list)
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    default_branch: str = "main"
    is_fork: bool = False
    is_archived: bool = False
    has_readme: bool | None = None
    github_created_at: datetime
    github_updated_at: datetime
    pushed_at: datetime | None = None

    @classmethod
    def from_github(cls, payload: dict[str, Any]) -> "RepositorySummary":
        """只提取业务需要的字段，避免保存无关的大段响应。"""
        owner_payload = payload.get("owner")
        owner = owner_payload.get("login", "") if isinstance(owner_payload, dict) else ""
        return cls(
            github_id=int(payload["id"]),
            full_name=str(payload["full_name"]),
            name=str(payload["name"]),
            owner=str(owner),
            description=str(payload["description"]) if payload.get("description") else None,
            html_url=str(payload["html_url"]),
            language=str(payload["language"]) if payload.get("language") else None,
            topics=[str(topic) for topic in payload.get("topics", [])],
            stars=int(payload.get("stargazers_count", 0)),
            forks=int(payload.get("forks_count", 0)),
            open_issues=int(payload.get("open_issues_count", 0)),
            default_branch=str(payload.get("default_branch", "main")),
            is_fork=bool(payload.get("fork", False)),
            is_archived=bool(payload.get("archived", False)),
            github_created_at=payload["created_at"],
            github_updated_at=payload["updated_at"],
            pushed_at=payload.get("pushed_at"),
        )


class RepositorySearchPage(BaseModel):
    """单页搜索结果和 GitHub 返回的总数量。"""

    model_config = ConfigDict(frozen=True)

    total_count: int
    incomplete_results: bool = False
    items: list[RepositorySummary] = Field(default_factory=list)


class RepositorySnapshotData(BaseModel):
    """创建仓库指标快照所需的数据。"""

    model_config = ConfigDict(frozen=True)

    stars: int
    forks: int
    open_issues: int
    captured_at: datetime | None = None


class RepositorySnapshotResponse(BaseModel):
    """供趋势图展示的只读指标快照。"""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    stars: int
    forks: int
    open_issues: int
    captured_at: datetime
