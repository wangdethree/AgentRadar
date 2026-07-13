"""仓库数据访问集成测试。"""

from datetime import UTC, datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base, Repository, RepositorySnapshot
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.github import RepositorySummary


def build_summary(stars: int = 10) -> RepositorySummary:
    """构造测试使用的标准化仓库。"""
    return RepositorySummary(
        github_id=100,
        full_name="example/agent",
        name="agent",
        owner="example",
        description="Example agent",
        html_url="https://github.com/example/agent",
        language="Python",
        topics=["agent"],
        stars=stars,
        forks=2,
        open_issues=1,
        github_created_at=datetime(2025, 1, 1, tzinfo=UTC),
        github_updated_at=datetime(2026, 7, 1, tzinfo=UTC),
    )


def test_upsert_repository_and_save_snapshot() -> None:
    """重复同步应更新同一仓库，而不是创建重复记录。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository_store = RepositoryRepository(session)
        first = repository_store.upsert(build_summary(stars=10))
        second = repository_store.upsert(build_summary(stars=25))
        snapshot = repository_store.save_snapshot(second)

        assert first.id == second.id
        assert second.stars == 25
        assert snapshot.stars == 25
        assert session.scalar(select(func.count()).select_from(Repository)) == 1
        assert session.scalar(select(func.count()).select_from(RepositorySnapshot)) == 1
