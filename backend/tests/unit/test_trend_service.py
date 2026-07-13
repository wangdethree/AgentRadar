"""趋势指标和项目分类测试。"""

from datetime import UTC, datetime, timedelta

from app.models.repository import Repository, RepositorySnapshot
from app.schemas.github import RepositorySummary
from app.services.trend_service import calculate_window_metrics, classify_repository


def test_calculate_window_metrics_uses_real_snapshots() -> None:
    """24 小时与 7 天增量应来自对应时间窗口快照。"""
    now = datetime(2026, 7, 13, 12, tzinfo=UTC)
    repository = Repository(
        github_id=1,
        full_name="example/agent",
        name="agent",
        owner="example",
        html_url="https://github.com/example/agent",
        stars=150,
        forks=20,
        open_issues=3,
        github_created_at=now - timedelta(days=100),
        github_updated_at=now,
    )
    snapshots = [
        RepositorySnapshot(stars=100, forks=10, open_issues=2, captured_at=now - timedelta(days=8)),
        RepositorySnapshot(
            stars=130, forks=15, open_issues=3, captured_at=now - timedelta(hours=25)
        ),
        RepositorySnapshot(stars=150, forks=20, open_issues=3, captured_at=now),
    ]

    metrics = calculate_window_metrics(repository, snapshots, now=now)

    assert metrics["stars_24h"] == 20
    assert metrics["stars_7d"] == 50
    assert metrics["forks_7d"] == 10
    assert metrics["growth_rate_7d"] == 50.0
    assert metrics["confidence"] == "high"


def test_classify_repository_prefers_specific_category() -> None:
    """明确的 LangGraph 项目不应落入通用框架分类。"""
    summary = RepositorySummary(
        github_id=1,
        full_name="example/langgraph-agent",
        name="langgraph-agent",
        owner="example",
        html_url="https://github.com/example/langgraph-agent",
        topics=["langgraph", "agent"],
        github_created_at=datetime(2025, 1, 1, tzinfo=UTC),
        github_updated_at=datetime(2026, 7, 1, tzinfo=UTC),
    )

    assert classify_repository(summary) == "LangGraph"
