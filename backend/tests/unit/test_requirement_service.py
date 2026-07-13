"""需求结构化和搜索计划测试。"""

from datetime import UTC, datetime

from app.services.requirement_service import build_search_plan, parse_requirement


def test_parse_requirement_extracts_chinese_constraints() -> None:
    """常见中文需求应被转换为稳定字段。"""
    requirement = parse_requirement(
        "帮我找适合 Python 后端学习的 LangGraph 项目，包含 FastAPI、工具调用和状态管理，"
        "适合改造成简历项目，不要 CrewAI，难度不要太高。"
    )

    assert requirement.topics == ["LangGraph"]
    assert requirement.languages == ["Python"]
    assert requirement.preferred_technologies == ["FastAPI", "LangGraph", "CrewAI"]
    assert requirement.required_capabilities == ["tool calling", "state management"]
    assert requirement.excluded_features == ["CrewAI"]
    assert requirement.difficulty == "intermediate"
    assert requirement.goal == "resume_project"


def test_build_search_plan_produces_complementary_queries() -> None:
    """搜索计划应生成至少三条查询并带有限流预算。"""
    requirement = parse_requirement("Python LangGraph FastAPI 工具调用 简历项目")
    plan = build_search_plan(requirement, now=datetime(2026, 7, 13, tzinfo=UTC))

    assert 3 <= len(plan.queries) <= 5
    assert all("fork:false" in item.query for item in plan.queries)
    assert all("language:Python" in item.query for item in plan.queries)
    assert plan.queries[0].purpose
    assert plan.max_research_targets == 5

