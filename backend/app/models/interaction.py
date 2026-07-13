"""单用户收藏与忽略模型。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.search import SearchSession


class Favorite(Base):
    """保存用户收藏、备注和来源搜索会话。"""

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("repository_id", name="uq_favorites_repository_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text)
    source_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("search_sessions.id", ondelete="SET NULL"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    repository: Mapped["Repository"] = relationship()
    source_session: Mapped["SearchSession | None"] = relationship()


class IgnoredRepository(Base):
    """保存不希望再次推荐的仓库。"""

    __tablename__ = "ignored_repositories"
    __table_args__ = (
        UniqueConstraint("repository_id", name="uq_ignored_repositories_repository_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    repository: Mapped["Repository"] = relationship()

