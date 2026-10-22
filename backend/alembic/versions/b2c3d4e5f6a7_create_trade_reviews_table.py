"""Create trade_reviews table for TASK-013.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-20 19:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("journal_entry_id", sa.UUID(), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("risk_assessment", sa.JSON(), nullable=False),
        sa.Column("strategy_compliance", sa.JSON(), nullable=False),
        sa.Column("behavioral_flags", sa.JSON(), nullable=False),
        sa.Column("badges", sa.JSON(), nullable=False),
        sa.Column("uncertainty_rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("limitations", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trade_reviews_user_id", "trade_reviews", ["user_id"])
    op.create_index("ix_trade_reviews_account_id", "trade_reviews", ["account_id"])
    op.create_index("ix_trade_reviews_journal_entry_id", "trade_reviews", ["journal_entry_id"])
    op.create_index("ix_trade_reviews_symbol", "trade_reviews", ["symbol"])
    op.create_index("ix_trade_reviews_mode", "trade_reviews", ["mode"])


def downgrade() -> None:
    op.drop_index("ix_trade_reviews_mode", table_name="trade_reviews")
    op.drop_index("ix_trade_reviews_symbol", table_name="trade_reviews")
    op.drop_index("ix_trade_reviews_journal_entry_id", table_name="trade_reviews")
    op.drop_index("ix_trade_reviews_account_id", table_name="trade_reviews")
    op.drop_index("ix_trade_reviews_user_id", table_name="trade_reviews")
    op.drop_table("trade_reviews")
