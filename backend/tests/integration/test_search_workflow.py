"""智能搜索基础工作流集成测试。"""

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agents.graph import SearchWorkflow
from app.core.config import Settings
from app.models import Base, ExecutionTrace, SearchResult, SearchSession
from app.tools.github.client import GitHubClient


def repository_payload() -> dict[str, object]:
    """构造与需求高度匹配的 GitHub 仓库。"""
    return {
        "id": 99,
        "full_name": "example/langgraph-fastapi-agent",
        "name": "langgraph-fastapi-agent",
        "owner": {"login": "example"},
        "description": "LangGraph FastAPI agent with tool calling and state management",
        "html_url": "https://github.com/example/langgraph-fastapi-agent",
        "language": "Python",
        "topics": ["langgraph", "fastapi", "agent"],
        "stargazers_count": 200,
        "forks_count": 20,
        "open_issues_count": 3,
        "default_branch": "main",
        "fork": False,
        "archived": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2026-07-10T00:00:00Z",
        "pushed_at": "2026-07-10T00:00:00Z",
    }


@pytest.mark.anyio
async def test_search_workflow_runs_full_foundation_chain() -> None:
    """自然语言输入应经过搜索、去重、初筛并留下完整轨迹。"""
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [repository_payload()],
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
            state = await SearchWorkflow(session, client).run(
                "寻找 Python LangGraph FastAPI 项目，包含工具调用和状态管理，适合简历",
                prefer_langgraph=False,
            )

        search_session = session.get(SearchSession, state["session_id"])
        assert search_session is not None
        assert search_session.status == "completed"
        assert len(state["discovered_repositories"]) >= 3
        assert len(state["filtered_repositories"]) == 1
        assert len(state["research_targets"]) == 1
        assert state["research_targets"][0].research_level == "deep"
        assert session.scalar(select(func.count()).select_from(ExecutionTrace)) == 7
        assert session.scalar(select(func.count()).select_from(SearchResult)) == 2

