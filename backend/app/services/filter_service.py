"""仓库去重、确定性过滤与低成本候选初筛。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.github import RepositorySummary
from app.schemas.search import ParsedRequirement, ScreenedRepository


class FilterOutcome(BaseModel):
    """过滤后的仓库及各规则移除数量。"""

    model_config = ConfigDict(frozen=True)

    repositories: list[RepositorySummary] = Field(default_factory=list)
    removed_counts: dict[str, int] = Field(default_factory=dict)


def normalize_and_filter(
    repositories: list[RepositorySummary],
    *,
    ignored_full_names: set[str] | None = None,
    updated_after: datetime | None = None,
    max_candidates: int = 60,
) -> FilterOutcome:
    """按照 full_name 去重，并应用无需模型参与的硬规则。"""
    ignored = {name.lower() for name in (ignored_full_names or set())}
    removed = {"duplicate": 0, "fork": 0, "archived": 0, "no_readme": 0, "stale": 0, "ignored": 0}
    deduplicated: dict[str, RepositorySummary] = {}

    for repository in repositories:
        key = repository.full_name.lower()
        existing = deduplicated.get(key)
        if existing is not None:
            removed["duplicate"] += 1
            if repository.github_updated_at > existing.github_updated_at:
                deduplicated[key] = repository
            continue
        deduplicated[key] = repository

    kept: list[RepositorySummary] = []
    for repository in deduplicated.values():
        if repository.is_fork:
            removed["fork"] += 1
        elif repository.is_archived:
            removed["archived"] += 1
        elif repository.has_readme is False:
            removed["no_readme"] += 1
        elif repository.full_name.lower() in ignored:
            removed["ignored"] += 1
        elif (
            updated_after is not None
            and (repository.pushed_at or repository.github_updated_at) < updated_after
        ):
            removed["stale"] += 1
        else:
            kept.append(repository)

    kept.sort(key=lambda item: (item.stars, item.github_updated_at), reverse=True)
    return FilterOutcome(repositories=kept[:max_candidates], removed_counts=removed)


def screen_candidates(
    repositories: list[RepositorySummary],
    requirement: ParsedRequirement,
) -> list[ScreenedRepository]:
    """用元数据和关键词做低成本初筛，决定后续调查深度。"""
    screened = [_screen_repository(repository, requirement) for repository in repositories]
    return sorted(screened, key=lambda item: item.relevance_score, reverse=True)


def _screen_repository(
    repository: RepositorySummary,
    requirement: ParsedRequirement,
) -> ScreenedRepository:
    """计算单个仓库与需求的可解释相关度。"""
    haystack = " ".join(
        [
            repository.name,
            repository.description or "",
            repository.language or "",
            *repository.topics,
        ]
    ).lower()
    score = 10.0
    reasons: list[str] = []

    topic_matches = [topic for topic in requirement.topics if topic.lower() in haystack]
    if topic_matches:
        score += min(len(topic_matches) * 15, 30)
        reasons.append(f"主题匹配：{', '.join(topic_matches)}")

    technology_matches = [
        technology
        for technology in requirement.preferred_technologies
        if technology.lower() in haystack
    ]
    if technology_matches:
        score += min(len(technology_matches) * 12, 24)
        reasons.append(f"技术栈匹配：{', '.join(technology_matches)}")

    capability_matches = [
        capability
        for capability in requirement.required_capabilities
        if capability.replace("-", " ").lower() in haystack.replace("-", " ")
    ]
    if capability_matches:
        score += min(len(capability_matches) * 8, 16)
        reasons.append(f"能力关键词匹配：{', '.join(capability_matches)}")

    if requirement.languages and repository.language in requirement.languages:
        score += 20
        reasons.append(f"主要语言为 {repository.language}")

    excluded_matches = [
        feature for feature in requirement.excluded_features if feature.lower() in haystack
    ]
    if excluded_matches:
        score -= 35
        reasons.append(f"命中排除项：{', '.join(excluded_matches)}")

    final_score = min(max(score, 0), 100)
    if final_score >= 60:
        research_level = "deep"
    elif final_score >= 30:
        research_level = "shallow"
    else:
        research_level = "skip"
    if not reasons:
        reasons.append("仅基础 Agent 关键词相关，需进一步核验")
    return ScreenedRepository(
        repository=repository,
        relevance_score=final_score,
        research_level=research_level,
        reasons=reasons,
    )
