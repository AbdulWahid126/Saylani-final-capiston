from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Base,
    DealJournalMapping,
    DocumentChunk,
    DocumentKnowledge,
    JournalEntry,
    RawMT5Deal,
    Strategy,
    TenantMixin,
    TradingAccount,
    User,
    UserRule,
)


def test_metadata_contains_all_models():
    """Verify all 9 models are registered in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "users",
        "trading_accounts",
        "raw_mt5_deals",
        "strategies",
        "journal_entries",
        "deal_journal_mappings",
        "user_rules",
        "document_knowledge",
        "document_chunks",
    }
    assert expected_tables.issubset(table_names)


def test_tenant_mixin_inheritance():
    """Verify tenant models inherit from TenantMixin."""
    tenant_models = [
        TradingAccount,
        Strategy,
        JournalEntry,
        UserRule,
        DocumentKnowledge,
        DocumentChunk,
    ]
    for model in tenant_models:
        assert issubclass(model, TenantMixin)
        assert hasattr(model, "user_id")


@pytest.mark.asyncio
async def test_database_crud_lifecycle(db_session: AsyncSession):
    """Test full relational CRUD lifecycle across User, Account, Deal, Journal, and Vector Chunk."""
    # 1. Create User
    user = User(
        email="trader@example.com",
        password_hash="hashed_pw_test",
        display_name="Pro Trader",
        base_currency="USD",
        timezone="UTC",
    )
    db_session.add(user)
    await db_session.flush()
    assert user.id is not None

    # 2. Create Trading Account
    account = TradingAccount(
        user_id=user.id,
        broker_name="IC Markets",
        server_name="ICMarketsSC-Live01",
        account_number="982341",
        account_type="LIVE",
        balance=10000.0,
        equity=10000.0,
        initial_balance=10000.0,
        currency="USD",
        leverage=100,
        sync_status="IDLE",
    )
    db_session.add(account)
    await db_session.flush()
    assert account.id is not None

    # 3. Create Strategy
    strategy = Strategy(
        user_id=user.id,
        name="ICT Silver Bullet",
        description="London and NY session liquidity sweeps",
        timeframe="5m",
        is_active=True,
    )
    db_session.add(strategy)
    await db_session.flush()

    # 4. Create Raw Deal
    deal = RawMT5Deal(
        account_id=account.id,
        deal_ticket=10928374,
        position_ticket=554433,
        symbol="EURUSD",
        deal_type="BUY",
        entry_type="IN",
        volume=1.0,
        price=1.0850,
        profit=0.0,
        commission=-3.50,
        swap=0.0,
        deal_time=datetime.now(UTC),
    )
    db_session.add(deal)
    await db_session.flush()

    # 5. Create Journal Entry
    journal = JournalEntry(
        account_id=account.id,
        user_id=user.id,
        broker_position_id=554433,
        symbol="EURUSD",
        direction="BUY",
        volume=1.0,
        entry_price=1.0850,
        exit_price=1.0900,
        gross_profit=500.0,
        commission=-3.50,
        swap=0.0,
        net_pnl=496.50,
        open_time=datetime.now(UTC),
        close_time=datetime.now(UTC),
        status="CLOSED",
        strategy_id=strategy.id,
        idempotency_hash="hash_test_123",
    )
    db_session.add(journal)
    await db_session.flush()

    # 6. Map Deal to Journal
    mapping = DealJournalMapping(
        journal_entry_id=journal.id,
        raw_deal_id=deal.id,
    )
    db_session.add(mapping)
    await db_session.flush()

    # 7. Create User Rule
    rule = UserRule(
        user_id=user.id,
        rule_name="Max Daily Loss 5%",
        rule_type="MAX_DAILY_LOSS",
        parameters={"max_loss_percent": 5.0, "threshold_usd": 500.0},
        is_active=True,
    )
    db_session.add(rule)
    await db_session.flush()

    # 8. Create Document Knowledge & Vector Chunk
    doc = DocumentKnowledge(
        user_id=user.id,
        filename="ICT_Playbook.pdf",
        doc_type="PLAYBOOK",
        file_size=204800,
    )
    db_session.add(doc)
    await db_session.flush()

    mock_embedding = [0.01] * 1536
    chunk = DocumentChunk(
        document_id=doc.id,
        user_id=user.id,
        content="Look for liquidity sweeps above Asian high before London open.",
        embedding=mock_embedding,
        chunk_metadata={"chapter": 1, "page": 4},
    )
    db_session.add(chunk)
    await db_session.commit()

    # 9. Query and Validate
    result = await db_session.execute(select(JournalEntry).where(JournalEntry.id == journal.id))
    retrieved_journal = result.scalar_one()
    assert retrieved_journal.symbol == "EURUSD"
    assert retrieved_journal.net_pnl == 496.50

    chunk_result = await db_session.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk.id)
    )
    retrieved_chunk = chunk_result.scalar_one()
    assert "liquidity sweeps" in retrieved_chunk.content
    assert retrieved_chunk.embedding is not None
    assert len(retrieved_chunk.embedding) == 1536
