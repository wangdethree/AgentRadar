"""为本地和面试环境写入可重复的热门榜单演示数据。"""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import create_database_engine, init_database
from app.models.analysis import AnalysisReport
from app.models.repository import RepositorySnapshot
from app.repositories.analysis_repository import AnalysisReportRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.analysis import (
    AgentCapabilities,
    EngineeringAnalysis,
    EvidenceItem,
    ReadingPathItem,
    ResearchReportData,
)
from app.schemas.github import RepositorySnapshotData, RepositorySummary


class DemoSnapshotValues(BaseModel):
    """三个固定时间窗口的仓库指标。"""

    model_config = ConfigDict(frozen=True)

    stars_7d: int
    stars_24h: int
    stars_now: int
    forks_7d: int
    forks_24h: int
    forks_now: int
    open_issues: int = 0


class DemoRepositoryCase(BaseModel):
    """一个热门榜单演示仓库。"""

    model_config = ConfigDict(frozen=True)

    github_id: int
    full_name: str
    description: str
    language: str
    topics: list[str] = Field(default_factory=list)
    created_days_ago: int = Field(ge=1)
    snapshots: DemoSnapshotValues
    capabilities: AgentCapabilities
    engineering: EngineeringAnalysis
    reading_path: list[str] = Field(default_factory=list)


class DemoDataset(BaseModel):
    """版本化的稳定演示数据集。"""

    model_config = ConfigDict(frozen=True)

    version: str
    repositories: list[DemoRepositoryCase] = Field(min_length=3)


def default_dataset_path() -> Path:
    """返回仓库内置演示数据路径。"""
    return Path(__file__).parents[2] / "demo" / "demo_data.json"


def load_demo_dataset(path: Path | None = None) -> DemoDataset:
    """读取并校验演示数据。"""
    source = path or default_dataset_path()
    return DemoDataset.model_validate_json(source.read_text(encoding="utf-8"))


def _build_summary(item: DemoRepositoryCase, now: datetime) -> RepositorySummary:
    owner, name = item.full_name.split("/", maxsplit=1)
    return RepositorySummary(
        github_id=item.github_id,
        full_name=item.full_name,
        name=name,
        owner=owner,
        description=item.description,
        html_url=f"https://github.com/{item.full_name}",
        language=item.language,
        topics=item.topics,
        stars=item.snapshots.stars_now,
        forks=item.snapshots.forks_now,
        open_issues=item.snapshots.open_issues,
        has_readme=True,
        github_created_at=now - timedelta(days=item.created_days_ago),
        github_updated_at=now,
        pushed_at=now - timedelta(hours=2),
    )


def _save_snapshots(
    store: RepositoryRepository,
    item: DemoRepositoryCase,
    now: datetime,
) -> None:
    """使用 8 天、25 小时和当前三个快照保证两个窗口都有基线。"""
    repository = store.get_by_full_name(item.full_name)
    if repository is None:  # pragma: no cover - upsert 后的数据一致性保护
        raise RuntimeError(f"演示仓库保存失败：{item.full_name}")
    values = item.snapshots
    snapshots = (
        (values.stars_7d, values.forks_7d, now - timedelta(days=8)),
        (values.stars_24h, values.forks_24h, now - timedelta(hours=25)),
        (values.stars_now, values.forks_now, now),
    )
    for stars, forks, captured_at in snapshots:
        store.save_snapshot(
            repository,
            RepositorySnapshotData(
                stars=stars,
                forks=forks,
                open_issues=values.open_issues,
                captured_at=captured_at,
            ),
        )


def _save_analysis(
    store: AnalysisReportRepository,
    summary: RepositorySummary,
    item: DemoRepositoryCase,
) -> None:
    """保存用于质量分和详情展示的规则分析报告。"""
    store.save(
        ResearchReportData(
            repository=summary,
            report_type="deep",
            project_summary=item.description,
            agent_capabilities=item.capabilities,
            engineering_analysis=item.engineering,
            strengths=["具备可验证的 Agent 能力", "提供完整工程结构和部署资料"],
            weaknesses=["演示数据仅用于界面和趋势链路，不代表实时 GitHub 指标"],
            evidence=[
                EvidenceItem(source="demo_fixture", observation="来自版本化稳定演示数据")
            ],
            reading_path=[
                ReadingPathItem(path=path, reason="演示项目的推荐阅读入口")
                for path in item.reading_path
            ],
            wrapper_risk="low",
        )
    )


def seed_demo_data(
    session: Session,
    dataset: DemoDataset,
    *,
    now: datetime | None = None,
) -> int:
    """幂等覆盖演示仓库的快照和报告，返回写入仓库数。"""
    reference_time = now or datetime.now(UTC)
    repository_store = RepositoryRepository(session)
    analysis_store = AnalysisReportRepository(session)

    for item in dataset.repositories:
        summary = _build_summary(item, reference_time)
        repository = repository_store.upsert(summary)
        session.execute(
            delete(RepositorySnapshot).where(
                RepositorySnapshot.repository_id == repository.id
            )
        )
        session.execute(
            delete(AnalysisReport).where(AnalysisReport.repository_id == repository.id)
        )
        session.commit()
        _save_snapshots(repository_store, item, reference_time)
        _save_analysis(analysis_store, summary, item)
    return len(dataset.repositories)


def main() -> None:
    """向配置的数据库写入演示数据。"""
    parser = argparse.ArgumentParser(description="加载 AgentRadar 稳定演示数据")
    parser.add_argument("--dataset", type=Path, default=default_dataset_path())
    parser.add_argument("--database-url", default=get_settings().database_url)
    args = parser.parse_args()
    engine = create_database_engine(args.database_url)
    init_database(engine)
    with Session(engine) as session:
        count = seed_demo_data(session, load_demo_dataset(args.dataset))
    print(f"已写入 {count} 个演示仓库及其趋势快照和分析报告")


if __name__ == "__main__":
    main()
