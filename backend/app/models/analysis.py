"""仓库深度分析报告模型。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.repository import Repository


class AnalysisReport(Base):
    """保存可复用的证据化研究结果。"""

    __tablename__ = "analysis_reports"
    __table_args__ = (
        Index(
            "ix_analysis_reports_repository_type_created",
            "repository_id",
            "report_type",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
    )
    report_type: Mapped[str] = mapped_column(String(32), index=True)
    project_summary: Mapped[str] = mapped_column(Text)
    agent_capabilities: Mapped[dict[str, object]] = mapped_column(JSON)
    engineering_analysis: Mapped[dict[str, object]] = mapped_column(JSON)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    reading_path: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    wrapper_risk: Mapped[str] = mapped_column(String(32), default="unknown")
    model_name: Mapped[str | None] = mapped_column(String(255))
    prompt_version: Mapped[str] = mapped_column(String(50), default="rules-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    repository: Mapped["Repository"] = relationship()
