"""趋势指标、分类和三类热门榜单。"""

import math
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.analysis import AnalysisReport
from app.models.repository import Repository, RepositorySnapshot
from app.schemas.analysis import AgentCapabilities, EngineeringAnalysis
from app.schemas.github import RepositorySummary
from app.schemas.trending import TrendingCard, TrendMetrics

CATEGORIES = (
    "Agent Framework",
    "LangGraph",
    "Multi-Agent",
    "MCP",
    "Browser Agent",
    "Coding Agent",
    "Agent Memory",
    "Agent Evaluation",
    "RAG Agent",
    "Research Agent",
    "Workflow Automation",
)

CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("LangGraph", ("langgraph",)),
    ("MCP", ("model context protocol", "mcp")),
    ("Multi-Agent", ("multi-agent", "multi agent", "multiagent")),
    ("Browser Agent", ("browser agent", "browser-use", "playwright")),
    ("Coding Agent", ("coding agent", "code agent", "swe-agent")),
    ("Agent Memory", ("agent memory", "long-term memory", "mem0")),
    ("Agent Evaluation", ("agent evaluation", "agent eval", "evals")),
    ("RAG Agent", ("rag agent", "retrieval augmented")),
    ("Research Agent", ("research agent", "deep research")),
    ("Workflow Automation", ("workflow automation", "agent workflow")),
    ("Agent Framework", ("agent framework", "agents sdk", "agent sdk")),
)


def classify_repository(repository: RepositorySummary) -> str:
    """优先使用 Topics、名称和描述做低成本分类。"""
    text = " ".join([repository.name, repository.description or "", *repository.topics]).lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return "Agent Framework"


def calculate_window_metrics(
    repository: Repository,
    snapshots: list[RepositorySnapshot],
    *,
    now: datetime | None = None,
) -> dict[str, int | float | str | None]:
    """从快照中计算 24 小时与 7 天变化，缺数据时显式降低置信度。"""
    reference_time = now or datetime.now(UTC)
    ordered = sorted(snapshots, key=lambda item: _as_utc(item.captured_at))
    current = ordered[-1] if ordered else None
    if current is None:
        return {
            "stars_24h": None,
            "stars_7d": None,
            "forks_7d": None,
            "growth_rate_7d": None,
            "confidence": "low",
        }

    baseline_24h = _find_baseline(ordered, reference_time - timedelta(hours=24))
    baseline_7d = _find_baseline(ordered, reference_time - timedelta(days=7))
    stars_24h = current.stars - baseline_24h.stars if baseline_24h else None
    stars_7d = current.stars - baseline_7d.stars if baseline_7d else None
    forks_7d = current.forks - baseline_7d.forks if baseline_7d else None
    growth_rate = None
    if baseline_7d and baseline_7d.stars > 0:
        growth_rate = round((current.stars - baseline_7d.stars) / baseline_7d.stars * 100, 2)
    confidence = (
        "high"
        if baseline_24h and baseline_7d
        else "medium"
        if baseline_24h or baseline_7d
        else "low"
    )
    return {
        "stars_24h": stars_24h,
        "stars_7d": stars_7d,
        "forks_7d": forks_7d,
        "growth_rate_7d": growth_rate,
        "confidence": confidence,
    }


def _find_baseline(
    snapshots: list[RepositorySnapshot],
    cutoff: datetime,
) -> RepositorySnapshot | None:
    eligible = [item for item in snapshots if _as_utc(item.captured_at) <= cutoff]
    return eligible[-1] if eligible else None


def _as_utc(value: datetime) -> datetime:
    """兼容 SQLite 返回的无时区时间。"""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class TrendService:
    """从数据库快照生成可解释热门榜单。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_cards(
        self,
        kind: str,
        *,
        limit: int = 20,
        category: str | None = None,
        now: datetime | None = None,
    ) -> list[TrendingCard]:
        """生成今日热门、本周上升或新项目潜力榜。"""
        reference_time = now or datetime.now(UTC)
        repositories = list(
            self.session.scalars(
                select(Repository)
                .options(selectinload(Repository.snapshots))
                .where(Repository.is_fork.is_(False), Repository.is_archived.is_(False))
            )
        )
        analysis_by_repository = self._latest_analyses()
        raw_items: list[tuple[Repository, dict[str, int | float | str | None], str]] = []
        for repository in repositories:
            summary = RepositorySummary.model_validate(repository)
            repository_category = classify_repository(summary)
            if category and repository_category != category:
                continue
            metrics = calculate_window_metrics(
                repository,
                repository.snapshots,
                now=reference_time,
            )
            if kind == "potential":
                age_days = (reference_time - _as_utc(repository.github_created_at)).days
                if age_days > 365 or repository.stars > 5000:
                    continue
            raw_items.append((repository, metrics, repository_category))

        maximum_daily = max((int(item[1]["stars_24h"] or 0) for item in raw_items), default=0)
        maximum_weekly = max((int(item[1]["stars_7d"] or 0) for item in raw_items), default=0)
        maximum_rate = max((float(item[1]["growth_rate_7d"] or 0) for item in raw_items), default=0)
        cards: list[TrendingCard] = []
        for repository, raw, repository_category in raw_items:
            score = _calculate_trend_score(
                repository,
                raw,
                maximum_daily=maximum_daily,
                maximum_weekly=maximum_weekly,
                maximum_rate=maximum_rate,
                now=reference_time,
            )
            quality, completeness = _calculate_quality(analysis_by_repository.get(repository.id))
            metrics = TrendMetrics(
                stars_24h=raw["stars_24h"],
                stars_7d=raw["stars_7d"],
                forks_7d=raw["forks_7d"],
                growth_rate_7d=raw["growth_rate_7d"],
                trend_score=score,
                confidence=raw["confidence"],
            )
            cards.append(
                TrendingCard(
                    repository=RepositorySummary.model_validate(repository),
                    category=repository_category,
                    metrics=metrics,
                    quality_score=quality,
                    agent_completeness=completeness,
                    trending_reason=_build_trending_reason(metrics),
                )
            )

        if kind == "daily":
            cards.sort(
                key=lambda item: (item.metrics.stars_24h or -1, item.metrics.trend_score),
                reverse=True,
            )
        elif kind == "weekly":
            cards.sort(
                key=lambda item: (item.metrics.stars_7d or -1, item.metrics.trend_score),
                reverse=True,
            )
        else:
            cards.sort(
                key=lambda item: (item.metrics.trend_score, item.quality_score), reverse=True
            )
        return cards[:limit]

    def _latest_analyses(self) -> dict[int, AnalysisReport]:
        """每个仓库只使用最新分析报告计算质量。"""
        records = list(
            self.session.scalars(select(AnalysisReport).order_by(AnalysisReport.created_at.desc()))
        )
        latest: dict[int, AnalysisReport] = {}
        for record in records:
            latest.setdefault(record.repository_id, record)
        return latest


def _normalized(value: float, maximum: float, weight: float) -> float:
    if value <= 0 or maximum <= 0:
        return 0
    return min(math.log1p(value) / math.log1p(maximum), 1) * weight


def _calculate_trend_score(
    repository: Repository,
    raw: dict[str, int | float | str | None],
    *,
    maximum_daily: int,
    maximum_weekly: int,
    maximum_rate: float,
    now: datetime,
) -> float:
    """按计划书权重计算趋势分，暂无数据的维度记零。"""
    daily = _normalized(float(raw["stars_24h"] or 0), maximum_daily, 25)
    weekly = _normalized(float(raw["stars_7d"] or 0), maximum_weekly, 25)
    rate = _normalized(float(raw["growth_rate_7d"] or 0), maximum_rate, 15)
    activity_days = max(
        (now - _as_utc(repository.pushed_at or repository.github_updated_at)).days, 0
    )
    activity = max(15 - min(activity_days, 180) / 180 * 15, 0)
    age_days = max((now - _as_utc(repository.github_created_at)).days, 0)
    freshness = max(5 - min(age_days, 365) / 365 * 5, 0)
    # Issue/PR 与 Release 活跃度将在采集相应快照后补足；当前权重保持为空，不用总 Star 代替。
    return round(min(daily + weekly + rate + activity + freshness, 100), 1)


def _calculate_quality(report: AnalysisReport | None) -> tuple[float, float]:
    if report is None:
        return 0.0, 0.0
    capabilities = AgentCapabilities.model_validate(report.agent_capabilities)
    engineering = EngineeringAnalysis.model_validate(report.engineering_analysis)
    capability_score = sum(capabilities.model_dump().values()) / 8 * 100
    engineering_values = engineering.model_dump(exclude={"dependency_files", "file_count"})
    engineering_score = sum(bool(value) for value in engineering_values.values()) / 6 * 100
    return round(capability_score * 0.55 + engineering_score * 0.45, 1), round(capability_score, 1)


def _build_trending_reason(metrics: TrendMetrics) -> str:
    if metrics.stars_24h is not None and metrics.stars_24h > 0:
        return f"最近 24 小时新增 {metrics.stars_24h} Star，短期关注度上升"
    if metrics.stars_7d is not None and metrics.stars_7d > 0:
        return f"最近 7 天新增 {metrics.stars_7d} Star，保持上升趋势"
    return "快照数据仍在积累，当前主要依据项目活跃度与新鲜度"
