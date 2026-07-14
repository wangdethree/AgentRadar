"""区分搜索、定时采集和演示快照来源。

Revision ID: 20260714_0005
Revises: 20260713_0004
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260714_0005"
down_revision: str | None = "20260713_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加来源字段，并识别已经写入的稳定演示快照。"""
    op.add_column(
        "repository_snapshots",
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="search",
        ),
    )
    op.create_index(
        op.f("ix_repository_snapshots_source"),
        "repository_snapshots",
        ["source"],
    )
    op.execute(
        sa.text(
            """
            UPDATE repository_snapshots
            SET source = 'demo'
            WHERE repository_id IN (
                SELECT id FROM repositories
                WHERE full_name LIKE 'agentradar-demo/%'
            )
            """
        )
    )


def downgrade() -> None:
    """移除快照来源字段。"""
    op.drop_index(op.f("ix_repository_snapshots_source"), table_name="repository_snapshots")
    op.drop_column("repository_snapshots", "source")
