"""热门榜单 API 集成测试。"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, Repository, RepositorySnapshot


def test_daily_trending_returns_snapshot_growth() -> None:
    """今日热门 API 应返回真实快照增量和分类。"""
    now = datetime.now(UTC)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    repository = Repository(
        github_id=10,
        full_name="example/langgraph-agent",
        name="langgraph-agent",
        owner="example",
        description="LangGraph agent",
        html_url="https://github.com/example/langgraph-agent",
        language="Python",
        topics=["langgraph"],
        stars=150,
        forks=20,
        open_issues=2,
        github_created_at=now - timedelta(days=100),
        github_updated_at=now,
        pushed_at=now,
    )
    session.add(repository)
    session.flush()
    session.add_all(
        [
            RepositorySnapshot(
                repository_id=repository.id,
                stars=120,
                forks=15,
                open_issues=2,
                captured_at=now - timedelta(hours=25),
            ),
            RepositorySnapshot(
                repository_id=repository.id,
                stars=150,
                forks=20,
                open_issues=2,
                captured_at=now,
            ),
        ]
    )
    session.commit()

    def override_database() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_database
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/trending/daily")
            snapshots_response = client.get(
                "/api/v1/repositories/example/langgraph-agent/snapshots",
                params={"days": 30},
            )

        assert response.status_code == 200
        assert response.json()[0]["repository"]["full_name"] == "example/langgraph-agent"
        assert response.json()[0]["metrics"]["stars_24h"] == 30
        assert response.json()[0]["category"] == "LangGraph"
        assert snapshots_response.status_code == 200
        assert [item["stars"] for item in snapshots_response.json()] == [120, 150]
    finally:
        app.dependency_overrides.clear()
        session.close()
