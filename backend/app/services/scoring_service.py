"""个性化推荐混合评分。"""

from datetime import UTC, datetime

from app.schemas.analysis import RecommendationCard, ResearchReportData, ScoreBreakdown
from app.schemas.search import ParsedRequirement, ScreenedRepository


def calculate_recommendation_score(
    screened: ScreenedRepository,
    report: ResearchReportData,
    requirement: ParsedRequirement,
    *,
    now: datetime | None = None,
) -> ScoreBreakdown:
    """按照计划书六个维度计算总分 100 的评分。"""
    relevance = round(screened.relevance_score * 0.3, 1)
    repository = report.repository
    searchable = " ".join(
        [
            repository.name,
            repository.description or "",
            *repository.topics,
            *(item.path for item in report.reading_path),
            *report.engineering_analysis.dependency_files,
        ]
    ).lower()

    language_score = (
        8 if requirement.languages and repository.language in requirement.languages else 0
    )
    if not requirement.languages:
        language_score = 8
    technologies = requirement.preferred_technologies
    matched_technologies = [item for item in technologies if item.lower() in searchable]
    technology_score = (
        12 if not technologies else 12 * len(matched_technologies) / len(technologies)
    )

    capability_count = sum(report.agent_capabilities.model_dump().values())
    engineering_values = report.engineering_analysis.model_dump(
        exclude={"dependency_files", "file_count"}
    )
    engineering_count = sum(bool(value) for value in engineering_values.values())

    reference_time = _as_utc(now or datetime.now(UTC))
    activity_time = _as_utc(repository.pushed_at or repository.github_updated_at)
    days_since_update = max((reference_time - activity_time).days, 0)
    if days_since_update <= 30:
        activity = 10
    elif days_since_update <= 90:
        activity = 8
    elif days_since_update <= 365:
        activity = 5
    else:
        activity = 2

    file_count = report.engineering_analysis.file_count
    if requirement.difficulty == "beginner":
        difficulty = 5 if file_count <= 100 else 2
    elif requirement.difficulty == "intermediate":
        difficulty = 5 if 30 <= file_count <= 500 else 3
    elif requirement.difficulty == "advanced":
        difficulty = 5 if file_count >= 150 else 2
    else:
        difficulty = 5

    return ScoreBreakdown(
        relevance=relevance,
        technology_match=round(language_score + technology_score, 1),
        agent_completeness=round(capability_count / 8 * 20, 1),
        engineering_completeness=round(engineering_count / 6 * 15, 1),
        activity=activity,
        difficulty_match=difficulty,
    )


def _as_utc(value: datetime) -> datetime:
    """兼容 SQLite 恢复的无时区时间。"""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def build_recommendations(
    screened_items: list[ScreenedRepository],
    reports: list[ResearchReportData],
    requirement: ParsedRequirement,
) -> list[RecommendationCard]:
    """按总分排序并输出最多三个推荐卡。"""
    screened_by_name = {item.repository.full_name.lower(): item for item in screened_items}
    cards: list[RecommendationCard] = []
    for report in reports:
        screened = screened_by_name.get(report.repository.full_name.lower())
        if screened is None:
            continue
        score = calculate_recommendation_score(screened, report, requirement)
        if score.total >= 80:
            level = "strong"
        elif score.total >= 65:
            level = "recommended"
        else:
            level = "consider"
        cards.append(
            RecommendationCard(
                repository=report.repository,
                score=score,
                total_score=score.total,
                recommendation_level=level,
                match_points=screened.reasons,
                report=report,
            )
        )
    return sorted(cards, key=lambda item: item.total_score, reverse=True)[:3]
