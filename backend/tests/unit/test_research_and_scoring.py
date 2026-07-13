"""证据化研究、阅读路径和混合评分测试。"""

import base64
from datetime import UTC, datetime

from app.schemas.github import RepositorySummary
from app.services.filter_service import screen_candidates
from app.services.requirement_service import parse_requirement
from app.services.research_service import build_research_report
from app.services.scoring_service import calculate_recommendation_score
from app.tools.github.content import GitHubFileContent, parse_file_content
from app.tools.github.tree import RepositoryTree, RepositoryTreeEntry


def make_repository() -> RepositorySummary:
    """构造深度研究测试仓库。"""
    return RepositorySummary(
        github_id=500,
        full_name="example/complete-agent",
        name="complete-agent",
        owner="example",
        description="LangGraph FastAPI research agent",
        html_url="https://github.com/example/complete-agent",
        language="Python",
        topics=["langgraph", "fastapi", "agent"],
        stars=300,
        forks=30,
        open_issues=5,
        github_created_at=datetime(2025, 1, 1, tzinfo=UTC),
        github_updated_at=datetime(2026, 7, 10, tzinfo=UTC),
        pushed_at=datetime(2026, 7, 10, tzinfo=UTC),
    )


def make_file(path: str, content: str) -> GitHubFileContent:
    """构造已解码的 GitHub 文本文件。"""
    return parse_file_content(
        {
            "type": "file",
            "path": path,
            "sha": f"sha-{path}",
            "size": len(content.encode()),
            "content": base64.b64encode(content.encode()).decode(),
        },
        max_bytes=10_000,
    )


def test_report_uses_only_real_paths_and_generates_score() -> None:
    """报告应识别能力，且阅读路径必须来自真实目录。"""
    repository = make_repository()
    readme = make_file(
        "README.md",
        "# Complete Agent\nA production research agent built with LangGraph StateGraph, "
        "bind_tools, checkpointer, memory and evaluation.",
    )
    paths = [
        "app/main.py",
        "app/graph/graph.py",
        "app/graph/state.py",
        "app/tools/search.py",
        "app/api/routes.py",
        "tests/test_graph.py",
        "Dockerfile",
        "pyproject.toml",
    ]
    tree = RepositoryTree(
        entries=[
            RepositoryTreeEntry(path=path, type="blob", sha=f"sha-{index}")
            for index, path in enumerate(paths)
        ]
    )
    dependency = make_file(
        "pyproject.toml",
        "dependencies = ['fastapi', 'sqlalchemy', 'langgraph']",
    )

    report = build_research_report(
        repository,
        report_type="deep",
        readme=readme,
        tree=tree,
        dependency_files=[dependency],
        release_count=2,
        issue_count=4,
    )
    requirement = parse_requirement("Python LangGraph FastAPI 工具调用 状态管理 简历项目")
    screened = screen_candidates([repository], requirement)[0]
    score = calculate_recommendation_score(
        screened,
        report,
        requirement,
        now=datetime(2026, 7, 13, tzinfo=UTC),
    )

    assert report.agent_capabilities.tool_calling is True
    assert report.agent_capabilities.state_management is True
    assert report.engineering_analysis.has_api is True
    assert report.engineering_analysis.has_tests is True
    assert report.wrapper_risk == "low"
    assert report.reading_path
    assert all(item.path in paths for item in report.reading_path)
    assert score.total >= 70
