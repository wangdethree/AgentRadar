"""智能搜索会话 API 集成测试。"""

from collections.abc import AsyncIterator, Iterator

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_github_client
from app.core.config import Settings
from app.core.database import get_db
from app.main import app
from app.models import Base
from app.tools.github.client import GitHubClient
from tests.integration.test_search_workflow import github_handler


def test_create_search_session_and_read_traces() -> None:
    """API 应完成搜索并允许随后读取会话和七个节点轨迹。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    github_client = GitHubClient(
        Settings(_env_file=None, github_api_url="https://api.github.test", github_max_retries=0),
        transport=httpx.MockTransport(github_handler),
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
            response = client.post(
                "/api/v1/search/sessions",
                json={
                    "query": "寻找 Python LangGraph FastAPI 项目，包含工具调用和状态管理，适合简历"
                },
            )
            session_id = response.json()["session"]["id"]
            traces_response = client.get(f"/api/v1/search/sessions/{session_id}/traces")
            results_response = client.get(
                f"/api/v1/search/sessions/{session_id}/results",
                params={"stage": "research_target"},
            )

        assert response.status_code == 201
        assert response.json()["filtered_count"] == 1
        assert len(response.json()["research_targets"]) == 1
        assert traces_response.status_code == 200
        assert len(response.json()["final_recommendations"]) == 1
        assert response.json()["final_recommendations"][0]["report"]["reading_path"]
        assert len(traces_response.json()) == 10
        assert results_response.status_code == 200
        assert results_response.json()[0]["repository"]["full_name"].startswith("example/")
    finally:
        app.dependency_overrides.clear()
        session.close()
