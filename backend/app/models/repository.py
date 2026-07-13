"""GitHub 仓库及指标快照模型。"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utc_now


class Repository(TimestampMixin, Base):
    """保存仓库的最新基础信息，使用 GitHub ID 和 full_name 双重防重。"""

    __tablename__ = "repositories"
    __table_args__ = (
        Index("ix_repositories_language_archived", "language", "is_archived"),
        Index("ix_repositories_pushed_at", "pushed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    owner: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    html_url: Mapped[str] = mapped_column(String(500))
    language: Mapped[str | None] = mapped_column(String(100), index=True)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    stars: Mapped[int] = mapped_column(default=0)
    forks: Mapped[int] = mapped_column(default=0)
    open_issues: Mapped[int] = mapped_column(default=0)
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    has_readme: Mapped[bool | None] = mapped_column(Boolean)
    github_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    github_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    snapshots: Mapped[list["RepositorySnapshot"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="RepositorySnapshot.captured_at",
    )


class RepositorySnapshot(Base):
    """保存某个时间点的仓库指标，为趋势计算提供原始数据。"""

    __tablename__ = "repository_snapshots"
    __table_args__ = (Index("ix_repository_snapshots_repo_time", "repository_id", "captured_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
    )
    stars: Mapped[int]
    forks: Mapped[int]
    open_issues: Mapped[int]
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )

    repository: Mapped[Repository] = relationship(back_populates="snapshots")
