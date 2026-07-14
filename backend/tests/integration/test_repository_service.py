"""仓库同步服务集成测试。"""

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.models import Base, Repository, RepositorySnapshot
from app.services.repository_service import RepositoryService
from app.tools.github.client import GitHubClient


def github_repository_payload() -> dict[str, object]:
    """构造 GitHub 搜索返回的仓库数据。"""
    return {
        "id": 7,
        "full_name": "example/research-agent",
        "name": "research-agent",
        "owner": {"login": "example"},
        "description": "Research agent",
        "html_url": "https://github.com/example/research-agent",
        "language": "Python",
        "topics": ["agent"],
        "stargazers_count": 80,
        "forks_count": 6,
        "open_issues_count": 2,
        "default_branch": "main",
        "fork": False,
        "archived": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2026-07-10T00:00:00Z",
        "pushed_at": "2026-07-10T00:00:00Z",
    }


@pytest.mark.anyio
async def test_search_and_persist_saves_repository_and_snapshot() -> None:
    """一次搜索应同时保存仓库最新值和趋势原始快照。"""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [github_repository_payload()],
            },
        )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    settings = Settings(
        _env_file=None,
        github_api_url="https://api.github.test",
        github_max_retries=0,
    )

    with Session(engine) as session:
        async with GitHubClient(settings, transport=httpx.MockTransport(handler)) as client:
            result = await RepositoryService(session, client).search_and_persist("agent")

        assert result.items[0].full_name == "example/research-agent"
        assert session.scalar(select(func.count()).select_from(Repository)) == 1
        assert session.scalar(select(func.count()).select_from(RepositorySnapshot)) == 1
        snapshot = session.scalar(select(RepositorySnapshot))
        assert snapshot is not None
        assert snapshot.source == "search"


@pytest.mark.anyio
async def test_search_and_persist_accepts_trending_snapshot_source() -> None:
    """定时热门采集必须把快照标记为 trending。"""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [github_repository_payload()],
            },
        )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    settings = Settings(
        _env_file=None,
        github_api_url="https://api.github.test",
        github_max_retries=0,
    )

    with Session(engine) as session:
        async with GitHubClient(settings, transport=httpx.MockTransport(handler)) as client:
            await RepositoryService(session, client).search_and_persist(
                "agent",
                snapshot_source="trending",
            )

        snapshot = session.scalar(select(RepositorySnapshot))
        assert snapshot is not None
        assert snapshot.source == "trending"

