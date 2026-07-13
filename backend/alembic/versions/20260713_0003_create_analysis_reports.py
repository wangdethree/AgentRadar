"""创建分析报告表。

Revision ID: 20260713_0003
Revises: 20260713_0002
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260713_0003"
down_revision: str | None = "20260713_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建证据化分析报告表。"""
    op.create_table(
        "analysis_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(length=32), nullable=False),
        sa.Column("project_summary", sa.Text(), nullable=False),
        sa.Column("agent_capabilities", sa.JSON(), nullable=False),
        sa.Column("engineering_analysis", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("weaknesses", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("reading_path", sa.JSON(), nullable=False),
        sa.Column("wrapper_risk", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name=op.f("fk_analysis_reports_repository_id_repositories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_reports")),
    )
    op.create_index(op.f("ix_analysis_reports_report_type"), "analysis_reports", ["report_type"])
    op.create_index(
        op.f("ix_analysis_reports_repository_id"),
        "analysis_reports",
        ["repository_id"],
    )
    op.create_index(
        "ix_analysis_reports_repository_type_created",
        "analysis_reports",
        ["repository_id", "report_type", "created_at"],
    )


def downgrade() -> None:
    """移除分析报告表。"""
    op.drop_table("analysis_reports")
