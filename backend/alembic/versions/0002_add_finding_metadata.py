"""add finding metadata column

Revision ID: 0002_add_finding_metadata
Revises: 0001_initial
Create Date: 2026-05-08 10:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_finding_metadata"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vulnerabilities",
        sa.Column("finding_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vulnerabilities", "finding_metadata")
