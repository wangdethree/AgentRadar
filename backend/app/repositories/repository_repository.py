"""仓库与指标快照的数据访问实现。"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository, RepositorySnapshot
from app.schemas.github import RepositorySnapshotData, RepositorySummary


class RepositoryRepository:
    """封装仓库数据读写，避免业务层直接拼装 ORM 查询。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_full_name(self, full_name: str) -> Repository | None:
        """按不区分大小写的 owner/repo 查询仓库。"""
        statement = select(Repository).where(Repository.full_name.ilike(full_name))
        return self.session.scalar(statement)

    def upsert(self, summary: RepositorySummary) -> Repository:
        """存在时更新最新指标，不存在时创建仓库。"""
        statement = select(Repository).where(
            (Repository.github_id == summary.github_id)
            | (Repository.full_name.ilike(summary.full_name))
        )
        repository = self.session.scalar(statement)
        values = summary.model_dump()
        values["synced_at"] = datetime.now(UTC)

        if repository is None:
            repository = Repository(**values)
            self.session.add(repository)
        else:
            for field, value in values.items():
                setattr(repository, field, value)

        self.session.commit()
        self.session.refresh(repository)
        return repository

    def save_snapshot(
        self,
        repository: Repository,
        data: RepositorySnapshotData | None = None,
    ) -> RepositorySnapshot:
        """保存指标快照；未传数据时直接使用仓库最新指标。"""
        snapshot_data = data or RepositorySnapshotData(
            stars=repository.stars,
            forks=repository.forks,
            open_issues=repository.open_issues,
        )
        snapshot = RepositorySnapshot(
            repository_id=repository.id,
            stars=snapshot_data.stars,
            forks=snapshot_data.forks,
            open_issues=snapshot_data.open_issues,
        )
        if snapshot_data.captured_at is not None:
            snapshot.captured_at = snapshot_data.captured_at
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def list_snapshots(
        self,
        repository_id: int,
        *,
        captured_after: datetime,
        limit: int = 500,
    ) -> list[RepositorySnapshot]:
        """按时间正序读取指定窗口内的指标快照。"""
        statement = (
            select(RepositorySnapshot)
            .where(
                RepositorySnapshot.repository_id == repository_id,
                RepositorySnapshot.captured_at >= captured_after,
            )
            .order_by(RepositorySnapshot.captured_at.asc(), RepositorySnapshot.id.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
