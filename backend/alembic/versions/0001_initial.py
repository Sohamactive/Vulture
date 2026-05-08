"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("repo_full_name", sa.String(length=255), nullable=False),
        sa.Column("repo_url", sa.String(length=512), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("security_score", sa.Integer(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scans_user_id", "scans", ["user_id"])
    op.create_index("ix_scans_repo_full_name", "scans", ["repo_full_name"])
    op.create_index("ix_scans_status", "scans", ["status"])

    op.create_table(
        "vulnerabilities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("scan_id", sa.String(length=36), sa.ForeignKey(
            "scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("detection_source", sa.String(length=128), nullable=False),
        sa.Column("owasp_category", sa.String(length=128), nullable=True),
        sa.Column("cwe_id", sa.String(length=32), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("remediation", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vulnerabilities_scan_id",
                    "vulnerabilities", ["scan_id"])
    op.create_index("ix_vulnerabilities_severity",
                    "vulnerabilities", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_vulnerabilities_severity", table_name="vulnerabilities")
    op.drop_index("ix_vulnerabilities_scan_id", table_name="vulnerabilities")
    op.drop_table("vulnerabilities")

    op.drop_index("ix_scans_status", table_name="scans")
    op.drop_index("ix_scans_repo_full_name", table_name="scans")
    op.drop_index("ix_scans_user_id", table_name="scans")
    op.drop_table("scans")
