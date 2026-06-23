"""add_habit_evidence_overrides_table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "habit_evidence_overrides",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("log_id", sa.BigInteger(), nullable=True),
        sa.Column("habit_name", sa.Text(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("override_status", sa.Text(), nullable=False),
        sa.Column("user_text", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["log_id"], ["logs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_habit_evidence_overrides_user_date_habit",
        "habit_evidence_overrides",
        ["telegram_user_id", "target_date", "habit_name"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_habit_evidence_overrides_user_date_habit",
        table_name="habit_evidence_overrides",
    )
    op.drop_table("habit_evidence_overrides")
