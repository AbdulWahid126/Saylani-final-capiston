"""Add status, chunk_count, and error_message to document_knowledge.

Revision ID: a1b2c3d4e5f6
Revises: d02be136d042
Create Date: 2026-10-20 02:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "d02be136d042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_knowledge",
        sa.Column("status", sa.String(length=30), server_default="COMPLETED", nullable=False),
    )
    op.add_column(
        "document_knowledge",
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "document_knowledge",
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_knowledge", "error_message")
    op.drop_column("document_knowledge", "chunk_count")
    op.drop_column("document_knowledge", "status")
