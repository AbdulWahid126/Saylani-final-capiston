"""initial_schema_setup

Revision ID: d02be136d042
Revises:
Create Date: 2026-10-16 21:20:33.547838

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d02be136d042"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("base_currency", sa.String(length=10), server_default="USD", nullable=False),
        sa.Column("timezone", sa.String(length=50), server_default="UTC", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. trading_accounts
    op.create_table(
        "trading_accounts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("broker_name", sa.String(length=100), nullable=False),
        sa.Column("server_name", sa.String(length=100), nullable=False),
        sa.Column("account_number", sa.String(length=50), nullable=False),
        sa.Column("account_type", sa.String(length=30), server_default="DEMO", nullable=False),
        sa.Column("encrypted_investor_pwd", sa.Text(), nullable=True),
        sa.Column("balance", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("equity", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("initial_balance", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="USD", nullable=False),
        sa.Column("leverage", sa.Integer(), server_default="100", nullable=False),
        sa.Column(
            "sync_status", sa.String(length=20), server_default="DISCONNECTED", nullable=False
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. raw_mt5_deals
    op.create_table(
        "raw_mt5_deals",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("trading_accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("deal_ticket", sa.BigInteger(), nullable=False),
        sa.Column("order_ticket", sa.BigInteger(), nullable=True),
        sa.Column("position_ticket", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("deal_type", sa.String(length=20), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("profit", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("commission", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("swap", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("fee", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("deal_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_raw_mt5_deals_deal_ticket", "raw_mt5_deals", ["deal_ticket"], unique=True)
    op.create_index("ix_raw_mt5_deals_position_ticket", "raw_mt5_deals", ["position_ticket"])
    op.create_index("ix_raw_mt5_deals_symbol", "raw_mt5_deals", ["symbol"])
    op.create_index("ix_raw_mt5_deals_deal_time", "raw_mt5_deals", ["deal_time"])

    # 4. strategies
    op.create_table(
        "strategies",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("timeframe", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. journal_entries
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("trading_accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("broker_position_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("gross_profit", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("commission", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("swap", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("net_pnl", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("risk_amount", sa.Float(), nullable=True),
        sa.Column("risk_percentage", sa.Float(), nullable=True),
        sa.Column("rr_ratio", sa.Float(), nullable=True),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
        sa.Column("session", sa.String(length=20), nullable=True),
        sa.Column(
            "strategy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("setup_tag", sa.String(length=50), nullable=True),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("emotional_state", sa.String(length=50), nullable=True),
        sa.Column("idempotency_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_journal_entries_broker_position_id", "journal_entries", ["broker_position_id"]
    )
    op.create_index("ix_journal_entries_symbol", "journal_entries", ["symbol"])
    op.create_index("ix_journal_entries_open_time", "journal_entries", ["open_time"])
    op.create_index("ix_journal_entries_close_time", "journal_entries", ["close_time"])
    op.create_index(
        "ix_journal_entries_idempotency_hash", "journal_entries", ["idempotency_hash"], unique=True
    )

    # 6. deal_journal_mappings
    op.create_table(
        "deal_journal_mappings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "journal_entry_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("journal_entries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "raw_deal_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("raw_mt5_deals.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. user_rules
    op.create_table(
        "user_rules",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rule_name", sa.String(length=100), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. document_knowledge
    op.create_table(
        "document_knowledge",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("doc_type", sa.String(length=50), server_default="PLAYBOOK", nullable=False),
        sa.Column("file_size", sa.Integer(), server_default="0", nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("document_knowledge.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=True),
        sa.Column("chunk_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    conn = op.get_bind()
    op.drop_table("document_chunks")
    op.drop_table("document_knowledge")
    op.drop_table("user_rules")
    op.drop_table("deal_journal_mappings")
    op.drop_table("journal_entries")
    op.drop_table("strategies")
    op.drop_table("raw_mt5_deals")
    op.drop_table("trading_accounts")
    op.drop_table("users")
    if conn.dialect.name == "postgresql":
        op.execute("DROP EXTENSION IF EXISTS vector;")
