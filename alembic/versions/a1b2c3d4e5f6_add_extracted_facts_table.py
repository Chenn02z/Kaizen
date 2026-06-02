"""add_extracted_facts_table

Revision ID: a1b2c3d4e5f6
Revises: 08d2dfcf2870
Create Date: 2026-06-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "08d2dfcf2870"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extracted_facts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("log_id", sa.BigInteger(), nullable=False),
        sa.Column("habits", sa.JSON(), nullable=False),
        sa.Column("adherence", sa.Text(), nullable=True),
        sa.Column("mood", sa.Text(), nullable=True),
        sa.Column("trigger", sa.Text(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["log_id"], ["logs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("log_id"),
    )


def downgrade() -> None:
    op.drop_table("extracted_facts")
