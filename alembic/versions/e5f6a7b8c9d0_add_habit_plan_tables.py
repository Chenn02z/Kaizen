"""add_habit_plan_tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "habit_categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id", "name"),
    )
    op.create_table(
        "habit_plans",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("habit_name", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("cadence_type", sa.Text(), nullable=False),
        sa.Column("cadence_value", sa.JSON(), nullable=True),
        sa.Column("success_condition", sa.Text(), nullable=False),
        sa.Column("habit_aliases", sa.JSON(), nullable=False),
        sa.Column("known_triggers", sa.JSON(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("fallback_checkin_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expected_evidence_window", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["habit_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id", "habit_name"),
    )
    op.create_index(
        "ix_habit_plans_user_category",
        "habit_plans",
        ["telegram_user_id", "category_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_habit_plans_user_category", table_name="habit_plans")
    op.drop_table("habit_plans")
    op.drop_table("habit_categories")
