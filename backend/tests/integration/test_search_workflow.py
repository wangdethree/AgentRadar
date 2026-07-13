"""智能搜索基础工作流集成测试。"""

import base64

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


def github_handler(request: httpx.Request) -> httpx.Response:
    """为搜索与深度研究端点提供稳定模拟响应。"""
    path = request.url.path
    if path == "/search/repositories":
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [repository_payload()],
            },
        )
    if path.endswith("/readme"):
        content = (
            "# LangGraph FastAPI Agent\nA research agent with StateGraph, bind_tools, "
            "memory, checkpointer and evaluation."
        )
        return httpx.Response(
            200,
            json={
                "type": "file",
                "path": "README.md",
                "sha": "readme-sha",
                "size": len(content.encode()),
                "content": base64.b64encode(content.encode()).decode(),
            },
        )
    if "/git/trees/" in path:
        tree_paths = [
            "app/main.py",
            "app/graph/state.py",
            "app/graph/nodes.py",
            "app/tools/search.py",
            "app/api/routes.py",
            "tests/test_graph.py",
            "Dockerfile",
            "pyproject.toml",
        ]
        return httpx.Response(
            200,
            json={
                "tree": [
                    {"path": item, "type": "blob", "sha": f"sha-{index}", "size": 100}
                    for index, item in enumerate(tree_paths)
                ],
                "truncated": False,
            },
        )
    if "/contents/" in path:
        content = "dependencies = ['fastapi', 'sqlalchemy', 'langgraph']"
        return httpx.Response(
            200,
            json={
                "type": "file",
                "path": "pyproject.toml",
                "sha": "dependency-sha",
                "size": len(content.encode()),
                "content": base64.b64encode(content.encode()).decode(),
            },
        )
    if path.endswith(("/releases", "/issues")):
        return httpx.Response(200, json=[])
    return httpx.Response(404, json={"message": "Not Found"})


@pytest.mark.anyio
async def test_search_workflow_runs_full_foundation_chain() -> None:
    """自然语言输入应经过搜索、去重、初筛并留下完整轨迹。"""
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
        async with GitHubClient(settings, transport=httpx.MockTransport(github_handler)) as client:
            workflow = SearchWorkflow(session, client)
            state = await workflow.run(
                "寻找 Python LangGraph FastAPI 项目，包含工具调用和状态管理，适合简历",
                prefer_langgraph=False,
            )
            refined_state = await workflow.refine(
                state["session_id"], "只保留 Python 项目，不要 CrewAI"
            )

        search_session = session.get(SearchSession, state["session_id"])
        assert search_session is not None
        assert search_session.status == "completed"
        assert len(state["discovered_repositories"]) >= 3
        assert len(state["filtered_repositories"]) == 1
        assert len(state["research_targets"]) == 1
        assert state["research_targets"][0].research_level == "deep"
        assert len(state["final_recommendations"]) == 1
        assert state["final_recommendations"][0].report.reading_path
        assert refined_state["session_id"] == state["session_id"]
        assert refined_state["parsed_requirement"].excluded_features == ["CrewAI"]
        assert session.scalar(select(func.count()).select_from(ExecutionTrace)) == 11
        assert session.scalar(select(func.count()).select_from(SearchResult)) == 3
