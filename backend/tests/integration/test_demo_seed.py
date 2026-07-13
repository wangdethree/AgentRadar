"""稳定演示数据集成测试。"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.demo import load_demo_dataset, seed_demo_data
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
        daily = TrendService(session).list_cards("daily", now=now)
        weekly = TrendService(session).list_cards("weekly", now=now)
        potential = TrendService(session).list_cards("potential", now=now)

    assert len(daily) == len(weekly) == len(potential) == 3
    assert daily[0].repository.full_name == "agentradar-demo/langgraph-research-agent"
    assert daily[0].metrics.stars_24h == 100
    assert weekly[0].metrics.stars_7d == 600
    assert daily[0].quality_score == 100
