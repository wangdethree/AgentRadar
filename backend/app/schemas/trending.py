"""热门项目雷达数据结构。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.github import RepositorySummary

TrendConfidence = Literal["low", "medium", "high"]


class TrendMetrics(BaseModel):
    """仓库在 24 小时和 7 天窗口内的趋势指标。"""

    model_config = ConfigDict(frozen=True)

    stars_24h: int | None = None
    stars_7d: int | None = None
    forks_7d: int | None = None
    growth_rate_7d: float | None = None
    trend_score: float = Field(ge=0, le=100)
    confidence: TrendConfidence = "low"


class TrendingCard(BaseModel):
    """热门榜单中的项目卡。"""

    model_config = ConfigDict(frozen=True)

    repository: RepositorySummary
    category: str
    metrics: TrendMetrics
    quality_score: float = Field(ge=0, le=100)
    agent_completeness: float = Field(ge=0, le=100)
    trending_reason: str
