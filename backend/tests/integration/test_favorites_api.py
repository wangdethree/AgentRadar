"""收藏与忽略 API 集成测试。"""

from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, Repository


def test_favorite_and_ignore_lifecycle() -> None:
    """用户应能收藏、忽略并恢复已同步仓库。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    repository = Repository(
        github_id=77,
        full_name="example/agent",
        name="agent",
        owner="example",
        html_url="https://github.com/example/agent",
        topics=["agent"],
        stars=10,
        forks=1,
        open_issues=0,
        github_created_at=datetime(2025, 1, 1, tzinfo=UTC),
        github_updated_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    session.add(repository)
    session.commit()

    def override_database() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_database
    try:
        with TestClient(app) as client:
            favorite_response = client.post(
                "/api/v1/favorites",
                json={"full_name": "example/agent", "note": "适合学习"},
            )
            ignored_response = client.post(
                "/api/v1/ignored-repositories",
                json={"full_name": "example/agent", "reason": "暂不推荐"},
            )
            favorites_response = client.get("/api/v1/favorites")
            ignored_list_response = client.get("/api/v1/ignored-repositories")
            delete_response = client.delete(
                f"/api/v1/ignored-repositories/{ignored_response.json()['id']}"
            )

        assert favorite_response.status_code == 201
        assert favorite_response.json()["repository"]["full_name"] == "example/agent"
        assert favorites_response.json()[0]["note"] == "适合学习"
        assert ignored_list_response.json()[0]["reason"] == "暂不推荐"
        assert delete_response.status_code == 204
    finally:
        app.dependency_overrides.clear()
        session.close()

