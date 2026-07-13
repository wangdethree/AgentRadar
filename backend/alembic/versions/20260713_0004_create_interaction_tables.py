"""创建收藏和忽略表。

Revision ID: 20260713_0004
Revises: 20260713_0003
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260713_0004"
down_revision: str | None = "20260713_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建单用户收藏和忽略表。"""
    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source_session_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name=op.f("fk_favorites_repository_id_repositories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_session_id"],
            ["search_sessions.id"],
            name=op.f("fk_favorites_source_session_id_search_sessions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_favorites")),
        sa.UniqueConstraint("repository_id", name="uq_favorites_repository_id"),
    )
    op.create_index(op.f("ix_favorites_repository_id"), "favorites", ["repository_id"])
    op.create_index(op.f("ix_favorites_source_session_id"), "favorites", ["source_session_id"])

    op.create_table(
        "ignored_repositories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name=op.f("fk_ignored_repositories_repository_id_repositories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ignored_repositories")),
        sa.UniqueConstraint("repository_id", name="uq_ignored_repositories_repository_id"),
    )
    op.create_index(
        op.f("ix_ignored_repositories_repository_id"),
        "ignored_repositories",
        ["repository_id"],
    )


def downgrade() -> None:
    """移除收藏和忽略表。"""
    op.drop_table("ignored_repositories")
    op.drop_table("favorites")

