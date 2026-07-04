"""add_logged_date_to_logs

Revision ID: g7b8c9d0e1f2
Revises: a7b8c9d0e1f2
Create Date: 2026-07-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("logs", sa.Column("logged_date", sa.Date(), nullable=True))
    op.add_column(
        "logs",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("logs", "updated_at")
    op.drop_column("logs", "logged_date")
