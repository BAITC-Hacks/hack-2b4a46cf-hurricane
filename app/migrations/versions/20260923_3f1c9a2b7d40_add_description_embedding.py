"""add description embedding

Revision ID: 3f1c9a2b7d40
Revises: d7cced6dbf39
Create Date: 2026-09-23 19:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3f1c9a2b7d40"
down_revision: str | None = "d7cced6dbf39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vendors",
        sa.Column("description_embedding", postgresql.ARRAY(sa.Float()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vendors", "description_embedding")
