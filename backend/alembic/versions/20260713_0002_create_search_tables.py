"""创建搜索会话、结果和执行轨迹表。

Revision ID: 20260713_0002
Revises: 20260713_0001
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260713_0002"
down_revision: str | None = "20260713_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建智能搜索基础链路的数据表。"""
    op.create_table(
        "search_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("parsed_requirement", sa.JSON(), nullable=True),
        sa.Column("search_plan", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_sessions")),
    )
    op.create_index(op.f("ix_search_sessions_status"), "search_sessions", ["status"])
    op.create_index(
        "ix_search_sessions_status_created",
        "search_sessions",
        ["status", "created_at"],
    )

    op.create_table(
        "search_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("reason", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name=op.f("fk_search_results_repository_id_repositories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["search_sessions.id"],
            name=op.f("fk_search_results_session_id_search_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_results")),
        sa.UniqueConstraint(
            "session_id",
            "repository_id",
            "stage",
            name="uq_search_results_session_repository_stage",
        ),
    )
    op.create_index(op.f("ix_search_results_repository_id"), "search_results", ["repository_id"])
    op.create_index(op.f("ix_search_results_session_id"), "search_results", ["session_id"])
    op.create_index(op.f("ix_search_results_stage"), "search_results", ["stage"])
    op.create_index(
        "ix_search_results_session_stage_rank",
        "search_results",
        ["session_id", "stage", "rank"],
    )

    op.create_table(
        "execution_traces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", sa.Integer(), nullable=True),
        sa.Column("tool_names", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["search_sessions.id"],
            name=op.f("fk_execution_traces_session_id_search_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_execution_traces")),
    )
    op.create_index(
        op.f("ix_execution_traces_node_name"),
        "execution_traces",
        ["node_name"],
    )
    op.create_index(
        op.f("ix_execution_traces_session_id"),
        "execution_traces",
        ["session_id"],
    )
    op.create_index(
        "ix_execution_traces_session_created",
        "execution_traces",
        ["session_id", "created_at"],
    )


def downgrade() -> None:
    """移除智能搜索基础链路的数据表。"""
    op.drop_table("execution_traces")
    op.drop_table("search_results")
    op.drop_table("search_sessions")
