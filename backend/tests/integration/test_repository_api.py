"""仓库 API 集成测试。"""

from collections.abc import AsyncIterator, Iterator

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_github_client
from app.core.config import Settings
from app.core.database import get_db
from app.main import app
from app.models import Base, Repository
from app.tools.github.client import GitHubClient
from tests.integration.test_repository_service import github_repository_payload


def test_search_repository_candidates_api() -> None:
    """API 搜索应返回标准化结果并完成数据库持久化。"""
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
    session = Session(engine)
    github_client = GitHubClient(
        Settings(_env_file=None, github_api_url="https://api.github.test", github_max_retries=0),
        transport=httpx.MockTransport(handler),
    )

    def override_database() -> Iterator[Session]:
        yield session

    async def override_github_client() -> AsyncIterator[GitHubClient]:
        try:
            yield github_client
        finally:
            await github_client.aclose()

    app.dependency_overrides[get_db] = override_database
    app.dependency_overrides[get_github_client] = override_github_client
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/repositories/search", params={"q": "agent"})

        assert response.status_code == 200
        assert response.json()["items"][0]["full_name"] == "example/research-agent"
        assert session.scalar(select(func.count()).select_from(Repository)) == 1
    finally:
        app.dependency_overrides.clear()
        session.close()
