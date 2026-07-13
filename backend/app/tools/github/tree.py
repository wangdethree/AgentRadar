"""GitHub 仓库目录树读取工具。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.tools.github.client import GitHubClient


class RepositoryTreeEntry(BaseModel):
    """目录树中对研究有用的最小字段集合。"""

    model_config = ConfigDict(frozen=True)

    path: str
    type: str
    sha: str
    size: int | None = None


class RepositoryTree(BaseModel):
    """裁剪后的目录树及 GitHub 截断标记。"""

    model_config = ConfigDict(frozen=True)

    entries: list[RepositoryTreeEntry] = Field(default_factory=list)
    truncated: bool = False


async def get_repository_tree(
    client: GitHubClient,
    owner: str,
    repo: str,
    ref: str,
    *,
    depth: int = 3,
    max_entries: int = 1000,
) -> RepositoryTree:
    """递归读取目录后按深度和数量裁剪，避免超长上下文。"""
    if depth < 0:
        raise ValueError("目录深度不能小于 0")
    payload: dict[str, Any] = await client.get_json(
        f"/repos/{owner}/{repo}/git/trees/{ref}",
        params={"recursive": 1},
    )
    entries = [
        RepositoryTreeEntry(
            path=str(item.get("path", "")),
            type=str(item.get("type", "")),
            sha=str(item.get("sha", "")),
            size=int(item["size"]) if item.get("size") is not None else None,
        )
        for item in payload.get("tree", [])
        if str(item.get("path", "")).count("/") <= depth
    ][:max_entries]
    source_count = len(payload.get("tree", []))
    return RepositoryTree(
        entries=entries,
        truncated=bool(payload.get("truncated", False)) or source_count > len(entries),
    )

