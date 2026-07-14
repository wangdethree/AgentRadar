"""GitHub 仓库同步与持久化服务。"""

from sqlalchemy.orm import Session

from app.repositories.repository_repository import RepositoryRepository
from app.schemas.github import (
    RepositorySearchPage,
    RepositorySnapshotData,
    RepositorySummary,
    SnapshotSource,
)
from app.tools.github.client import GitHubClient
from app.tools.github.repository import get_repository
from app.tools.github.search import search_repositories


class RepositoryService:
    """协调 GitHub 工具与数据库，保持 API 层轻量。"""

    def __init__(self, session: Session, github_client: GitHubClient) -> None:
        self.store = RepositoryRepository(session)
        self.github_client = github_client

    async def search_and_persist(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 30,
        snapshot_source: SnapshotSource = "search",
    ) -> RepositorySearchPage:
        """搜索仓库，并为每个候选保存最新数据和指标快照。"""
        result = await search_repositories(
            self.github_client,
            query,
            page=page,
            per_page=per_page,
        )
        for summary in result.items:
            repository = self.store.upsert(summary)
            self.store.save_snapshot(
                repository,
                RepositorySnapshotData(
                    stars=repository.stars,
                    forks=repository.forks,
                    open_issues=repository.open_issues,
                    source=snapshot_source,
                ),
            )
        return result

    async def sync_repository(self, owner: str, repo: str) -> RepositorySummary:
        """读取单个仓库详情，并同步最新指标。"""
        summary = await get_repository(self.github_client, owner, repo)
        repository = self.store.upsert(summary)
        self.store.save_snapshot(
            repository,
            RepositorySnapshotData(
                stars=repository.stars,
                forks=repository.forks,
                open_issues=repository.open_issues,
                source="repository",
            ),
        )
        return summary

