"""GitHub 数据标准化测试。"""

from app.schemas.github import RepositorySummary


def test_repository_summary_from_github() -> None:
    """原始响应应被裁剪并映射为稳定字段。"""
    summary = RepositorySummary.from_github(
        {
            "id": 42,
            "full_name": "example/agent",
            "name": "agent",
            "owner": {"login": "example", "avatar_url": "ignored"},
            "description": "A useful agent",
            "html_url": "https://github.com/example/agent",
            "language": "Python",
            "topics": ["agent", "langgraph"],
            "stargazers_count": 120,
            "forks_count": 15,
            "open_issues_count": 3,
            "default_branch": "main",
            "fork": False,
            "archived": False,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2026-07-01T00:00:00Z",
            "pushed_at": "2026-07-01T00:00:00Z",
            "watchers": 999,
        }
    )

    assert summary.github_id == 42
    assert summary.owner == "example"
    assert summary.stars == 120
    assert summary.topics == ["agent", "langgraph"]
    assert "watchers" not in summary.model_dump()

