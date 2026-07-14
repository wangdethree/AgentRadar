"""稳定演示数据集成测试。"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.demo import load_demo_dataset, remove_demo_data, seed_demo_data
from app.models import AnalysisReport, Base, Repository, RepositorySnapshot
from app.services.trend_service import TrendService


def test_seed_demo_data_is_repeatable_and_populates_trending() -> None:
    """重复加载演示数据不应累积快照，并应生成三个稳定榜单项目。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    dataset_path = Path(__file__).parents[2] / "demo" / "demo_data.json"
    now = datetime(2026, 7, 13, 12, tzinfo=UTC)

    with Session(engine) as session:
        dataset = load_demo_dataset(dataset_path)
        assert seed_demo_data(session, dataset, now=now) == 3
        assert seed_demo_data(session, dataset, now=now) == 3

        assert session.scalar(select(func.count()).select_from(Repository)) == 3
        assert session.scalar(select(func.count()).select_from(RepositorySnapshot)) == 9
        assert session.scalar(select(func.count()).select_from(AnalysisReport)) == 3
        assert TrendService(session).list_cards("daily", now=now) == []
        daily = TrendService(session).list_cards("daily", include_demo=True, now=now)
        weekly = TrendService(session).list_cards("weekly", include_demo=True, now=now)
        potential = TrendService(session).list_cards("potential", include_demo=True, now=now)

    assert len(daily) == len(weekly) == len(potential) == 3
    assert daily[0].repository.full_name == "agentradar-demo/langgraph-research-agent"
    assert daily[0].data_source == "demo"
    assert daily[0].metrics.stars_24h == 100
    assert weekly[0].metrics.stars_7d == 600
    assert daily[0].quality_score == 100


def test_remove_demo_data_preserves_real_repository() -> None:
    """清理命令只能删除内置演示命名空间。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    dataset_path = Path(__file__).parents[2] / "demo" / "demo_data.json"
    now = datetime(2026, 7, 13, 12, tzinfo=UTC)

    with Session(engine) as session:
        seed_demo_data(session, load_demo_dataset(dataset_path), now=now)
        session.add(
            Repository(
                github_id=999,
                full_name="real/agent-project",
                name="agent-project",
                owner="real",
                html_url="https://github.com/real/agent-project",
                stars=10,
                forks=1,
                open_issues=0,
                github_created_at=now,
                github_updated_at=now,
            )
        )
        session.commit()

        assert remove_demo_data(session) == 3
        repositories = list(session.scalars(select(Repository)))

        assert [item.full_name for item in repositories] == ["real/agent-project"]
        assert session.scalar(select(func.count()).select_from(RepositorySnapshot)) == 0
        assert session.scalar(select(func.count()).select_from(AnalysisReport)) == 0
