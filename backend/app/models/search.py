"""搜索会话、阶段结果与执行轨迹模型。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


def generate_uuid() -> str:
    """生成适合 API 暴露的随机会话 ID。"""
    return str(uuid4())


class SearchSession(Base):
    """保存一次自然语言项目搜索的输入、计划与状态。"""

    __tablename__ = "search_sessions"
    __table_args__ = (Index("ix_search_sessions_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_query: Mapped[str] = mapped_column(Text)
    parsed_requirement: Mapped[dict[str, object] | None] = mapped_column(JSON)
    search_plan: Mapped[dict[str, object] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    results: Mapped[list["SearchResult"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    traces: Mapped[list["ExecutionTrace"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ExecutionTrace.created_at",
    )


class SearchResult(Base):
    """记录仓库在候选、初筛和研究目标阶段的分数与原因。"""

    __tablename__ = "search_results"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "repository_id",
            "stage",
            name="uq_search_results_session_repository_stage",
        ),
        Index("ix_search_results_session_stage_rank", "session_id", "stage", "rank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("search_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(32), index=True)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)
    rank: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SearchSession] = relationship(back_populates="results")


class ExecutionTrace(Base):
    """保存可解释的节点与工具执行记录，不保存模型思维过程。"""

    __tablename__ = "execution_traces"
    __table_args__ = (Index("ix_execution_traces_session_created", "session_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("search_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    node_name: Mapped[str] = mapped_column(String(100), index=True)
    event_type: Mapped[str] = mapped_column(String(32), default="node")
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage: Mapped[int | None] = mapped_column(Integer)
    tool_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SearchSession] = relationship(back_populates="traces")
