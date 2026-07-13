"""创建仓库和指标快照表。

Revision ID: 20260713_0001
Revises:
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260713_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建阶段 1 所需的数据表和索引。"""
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("html_url", sa.String(length=500), nullable=False),
        sa.Column("language", sa.String(length=100), nullable=True),
        sa.Column("topics", sa.JSON(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("forks", sa.Integer(), nullable=False),
        sa.Column("open_issues", sa.Integer(), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=False),
        sa.Column("is_fork", sa.Boolean(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("has_readme", sa.Boolean(), nullable=True),
        sa.Column("github_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositories")),
        sa.UniqueConstraint("full_name", name=op.f("uq_repositories_full_name")),
        sa.UniqueConstraint("github_id", name=op.f("uq_repositories_github_id")),
    )
    op.create_index(op.f("ix_repositories_full_name"), "repositories", ["full_name"])
    op.create_index(op.f("ix_repositories_github_id"), "repositories", ["github_id"])
    op.create_index(op.f("ix_repositories_is_archived"), "repositories", ["is_archived"])
    op.create_index(op.f("ix_repositories_is_fork"), "repositories", ["is_fork"])
    op.create_index(op.f("ix_repositories_language"), "repositories", ["language"])
    op.create_index(op.f("ix_repositories_owner"), "repositories", ["owner"])
    op.create_index(
        "ix_repositories_language_archived", "repositories", ["language", "is_archived"]
    )
    op.create_index("ix_repositories_pushed_at", "repositories", ["pushed_at"])

    op.create_table(
        "repository_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("forks", sa.Integer(), nullable=False),
        sa.Column("open_issues", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name=op.f("fk_repository_snapshots_repository_id_repositories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repository_snapshots")),
    )
    op.create_index(
        op.f("ix_repository_snapshots_captured_at"),
        "repository_snapshots",
        ["captured_at"],
    )
    op.create_index(
        op.f("ix_repository_snapshots_repository_id"),
        "repository_snapshots",
        ["repository_id"],
    )
    op.create_index(
        "ix_repository_snapshots_repo_time",
        "repository_snapshots",
        ["repository_id", "captured_at"],
    )


def downgrade() -> None:
    """移除阶段 1 的数据表。"""
    op.drop_table("repository_snapshots")
    op.drop_table("repositories")
