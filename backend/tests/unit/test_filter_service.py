"""仓库确定性过滤与初筛测试。"""

from datetime import UTC, datetime

from app.schemas.github import RepositorySummary
from app.services.filter_service import normalize_and_filter, screen_candidates
from app.services.requirement_service import parse_requirement


def make_repository(
    full_name: str,
    *,
    stars: int = 10,
    is_fork: bool = False,
    is_archived: bool = False,
    language: str | None = "Python",
    topics: list[str] | None = None,
) -> RepositorySummary:
    """构造过滤规则测试仓库。"""
    owner, name = full_name.split("/", maxsplit=1)
    return RepositorySummary(
        github_id=abs(hash(full_name)),
        full_name=full_name,
        name=name,
        owner=owner,
        description="LangGraph FastAPI agent with tool calling and state management",
        html_url=f"https://github.com/{full_name}",
        language=language,
        topics=topics or ["langgraph", "agent"],
        stars=stars,
        is_fork=is_fork,
        is_archived=is_archived,
        github_created_at=datetime(2025, 1, 1, tzinfo=UTC),
        github_updated_at=datetime(2026, 7, 1, tzinfo=UTC),
        pushed_at=datetime(2026, 7, 1, tzinfo=UTC),
    )


def test_normalize_and_filter_applies_hard_rules() -> None:
    """去重、Fork、归档和忽略规则应在模型调用前执行。"""
    repositories = [
        make_repository("a/good", stars=20),
        make_repository("A/GOOD", stars=10),
        make_repository("a/fork", is_fork=True),
        make_repository("a/archived", is_archived=True),
        make_repository("a/ignored"),
    ]

    outcome = normalize_and_filter(repositories, ignored_full_names={"a/ignored"})

    assert [item.full_name for item in outcome.repositories] == ["a/good"]
    assert outcome.removed_counts == {
        "duplicate": 1,
        "fork": 1,
        "archived": 1,
        "no_readme": 0,
        "stale": 0,
        "ignored": 1,
    }


def test_screen_candidates_selects_deep_research_target() -> None:
    """技术栈和能力高度匹配的仓库应进入深度调查。"""
    requirement = parse_requirement("Python LangGraph FastAPI 工具调用 状态管理")

    screened = screen_candidates([make_repository("a/good")], requirement)

    assert screened[0].research_level == "deep"
    assert screened[0].relevance_score >= 60
    assert any("技术栈匹配" in reason for reason in screened[0].reasons)

