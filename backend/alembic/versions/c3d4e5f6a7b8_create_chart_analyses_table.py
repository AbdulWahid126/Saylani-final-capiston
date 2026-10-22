"""Create chart_analyses table for TASK-014.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-20 21:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chart_analyses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("strategy_mode", sa.String(length=30), nullable=False, server_default="GENERAL"),
        sa.Column("symbol", sa.String(length=30), nullable=True),
        sa.Column("timeframe", sa.String(length=20), nullable=True),
        sa.Column("chart_type", sa.String(length=30), nullable=True),
        sa.Column("image_filename", sa.String(length=255), nullable=True),
        sa.Column("image_dimensions", sa.String(length=50), nullable=True),
        sa.Column("market_structure", sa.JSON(), nullable=False),
        sa.Column("key_levels", sa.JSON(), nullable=False),
        sa.Column("trade_setup", sa.JSON(), nullable=True),
        sa.Column("scenarios", sa.JSON(), nullable=False),
        sa.Column("playbook_citations", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("badges", sa.JSON(), nullable=False),
        sa.Column("uncertainty_rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chart_analyses_user_id", "chart_analyses", ["user_id"])
    op.create_index("ix_chart_analyses_symbol", "chart_analyses", ["symbol"])
    op.create_index("ix_chart_analyses_strategy_mode", "chart_analyses", ["strategy_mode"])


def downgrade() -> None:
    op.drop_index("ix_chart_analyses_strategy_mode", table_name="chart_analyses")
    op.drop_index("ix_chart_analyses_symbol", table_name="chart_analyses")
    op.drop_index("ix_chart_analyses_user_id", table_name="chart_analyses")
    op.drop_table("chart_analyses")
