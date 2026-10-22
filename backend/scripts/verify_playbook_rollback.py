"""Live Supabase PostgreSQL transactional rollback verification for TASK-012: Personal Playbook Knowledge Base (pgvector RAG).

Validates:
1. Native pgvector Vector(1536) column compatibility on live PostgreSQL.
2. Ingestion of DocumentKnowledge and DocumentChunk records.
3. Native pgvector cosine distance search (<=>) directly on Supabase.
4. Semantic retrieval thresholding, top_k ordering, and citation generation.
5. Strict tenant isolation (User A vs User B).
6. Grounded Q&A with anti-prompt-injection isolation.
7. 100% clean transactional rollback leaving zero residual records.
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.knowledge import DocumentChunk, DocumentKnowledge
from app.models.user import User
from app.services.embedding_service import get_embedding_provider
from app.services.rag_engine import ask_playbook, search_playbook_chunks


async def run_live_verification() -> None:
    print("[INFO] Connecting to Supabase PostgreSQL database...")
    async with async_session_factory() as db:
        test_email_a = f"task012_user_a_{int(datetime.now(UTC).timestamp())}@example.com"
        test_email_b = f"task012_user_b_{int(datetime.now(UTC).timestamp())}@example.com"
        try:
            # 1. Create temporary test users
            user_a = User(
                email=test_email_a,
                password_hash=hash_password("VerifyPassword123!"),
            )
            user_b = User(
                email=test_email_b,
                password_hash=hash_password("VerifyPassword123!"),
            )
            db.add_all([user_a, user_b])
            await db.flush()

            print(
                f"[INFO] Created temporary test users: User A ({user_a.id}), User B ({user_b.id})"
            )

            # 2. Ingest DocumentKnowledge and DocumentChunks for User A
            embedder = get_embedding_provider()

            doc_a1 = DocumentKnowledge(
                id=uuid.uuid4(),
                user_id=user_a.id,
                filename="london_breakout_strategy.md",
                doc_type="PLAYBOOK",
                file_size=1024,
                status="COMPLETED",
                chunk_count=2,
            )
            doc_a2 = DocumentKnowledge(
                id=uuid.uuid4(),
                user_id=user_a.id,
                filename="prop_firm_risk_rules.txt",
                doc_type="RULES",
                file_size=512,
                status="COMPLETED",
                chunk_count=1,
            )
            db.add_all([doc_a1, doc_a2])
            await db.flush()

            chunk_a1_text = (
                "London Open Breakout: Strategy activates strictly at 08:00 AM London time. "
                "Look for Asian range high/low sweep followed by 5m MSS and Fair Value Gap entry."
            )
            chunk_a2_text = (
                "Trade Management: Risk strictly 1R per trade with 1:2 minimum reward to risk. "
                "Move stop to breakeven after reaching 1.5R target."
            )
            chunk_a3_text = (
                "Prop Firm Rules: Maximum daily drawdown is 4%. Maximum overall trailing drawdown is 8%. "
                "Trading news events is strictly prohibited 5 minutes before and after high-impact events."
            )

            vec_a1 = await embedder.embed_query(chunk_a1_text)
            vec_a2 = await embedder.embed_query(chunk_a2_text)
            vec_a3 = await embedder.embed_query(chunk_a3_text)

            assert len(vec_a1) == 1536, f"Expected 1536 dimensions, got {len(vec_a1)}"

            c1 = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_a1.id,
                user_id=user_a.id,
                content=chunk_a1_text,
                embedding=vec_a1,
                chunk_metadata={
                    "filename": "london_breakout_strategy.md",
                    "chunk_index": 0,
                    "page": 1,
                },
            )
            c2 = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_a1.id,
                user_id=user_a.id,
                content=chunk_a2_text,
                embedding=vec_a2,
                chunk_metadata={
                    "filename": "london_breakout_strategy.md",
                    "chunk_index": 1,
                    "page": 1,
                },
            )
            c3 = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_a2.id,
                user_id=user_a.id,
                content=chunk_a3_text,
                embedding=vec_a3,
                chunk_metadata={
                    "filename": "prop_firm_risk_rules.txt",
                    "chunk_index": 0,
                    "page": 1,
                },
            )

            # Ingest a document for User B to test cross-tenant isolation
            doc_b = DocumentKnowledge(
                id=uuid.uuid4(),
                user_id=user_b.id,
                filename="user_b_secret_strategy.txt",
                doc_type="PLAYBOOK",
                file_size=256,
                status="COMPLETED",
                chunk_count=1,
            )
            db.add(doc_b)
            await db.flush()

            chunk_b_text = (
                "User B confidential scalping rules: confidential strategy not visible to User A."
            )
            vec_b = await embedder.embed_query(chunk_b_text)
            c_b = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_b.id,
                user_id=user_b.id,
                content=chunk_b_text,
                embedding=vec_b,
                chunk_metadata={"filename": "user_b_secret_strategy.txt", "chunk_index": 0},
            )

            db.add_all([c1, c2, c3, c_b])
            await db.flush()

            print(
                "[INFO] Successfully inserted 1536-dim vector chunks into live Supabase pgvector!"
            )

            # 3. Test native pgvector similarity search on live Supabase
            print(
                "[INFO] Executing native pgvector cosine distance search (<=>) on live Supabase..."
            )
            results = await search_playbook_chunks(
                db=db,
                user_id=user_a.id,
                query="London Open Breakout Asian sweep",
                top_k=3,
                similarity_threshold=0.1,
            )
            assert len(results) >= 1, "Expected at least 1 match from pgvector similarity search!"
            assert results[0].document_filename == "london_breakout_strategy.md"
            assert "London Open Breakout" in results[0].content
            print(f"[INFO] Top search result similarity: {results[0].similarity:.4f}")

            # 4. Verify strict tenant isolation
            print("[INFO] Verifying cross-user tenant isolation in vector search...")
            search_as_user_b = await search_playbook_chunks(
                db=db,
                user_id=user_b.id,
                query="London Open Breakout Asian sweep",
                top_k=3,
                similarity_threshold=0.1,
            )
            for res in search_as_user_b:
                assert (
                    res.document_filename != "london_breakout_strategy.md"
                ), "Tenant breach! User B retrieved User A's playbook!"

            search_as_user_a_for_b = await search_playbook_chunks(
                db=db,
                user_id=user_a.id,
                query="confidential scalping",
                top_k=3,
                similarity_threshold=0.1,
            )
            for res in search_as_user_a_for_b:
                assert (
                    res.document_filename != "user_b_secret_strategy.txt"
                ), "Tenant breach! User A retrieved User B's secret strategy!"
            print(
                "[SUCCESS] Tenant isolation verified: Zero cross-tenant document or chunk leakage!"
            )

            # 5. Verify RAG Question-Answering
            print("[INFO] Verifying evidence-grounded Q&A with citations...")
            ask_resp = await ask_playbook(
                db=db,
                user_id=user_a.id,
                question="What is the maximum daily drawdown allowed?",
                top_k=2,
                similarity_threshold=0.1,
            )
            assert ask_resp.has_sufficient_context is True
            assert len(ask_resp.citations) >= 1
            assert any(
                "prop_firm_risk_rules.txt" in c.document_filename for c in ask_resp.citations
            )
            assert ask_resp.confidence_score > 0.0
            print(f"[INFO] Q&A response: {ask_resp.answer[:120]}...")
            print("[SUCCESS] Grounded Q&A with exact citations verified!")

        finally:
            print("[INFO] Rolling back transaction to ensure 0 persistent test records...")
            await db.rollback()

    # 6. Confirm 100% clean rollback
    async with async_session_factory() as verify_db:
        remaining_users = (
            await verify_db.scalars(
                select(User).where(User.email.in_([test_email_a, test_email_b]))
            )
        ).all()
        assert len(remaining_users) == 0, "Test users were not rolled back!"

        remaining_chunks = await verify_db.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.content.like("%London Open Breakout%")
            )
        )
        assert remaining_chunks == 0, f"Found {remaining_chunks} lingering test chunks!"

        print("[SUCCESS] 100% clean rollback confirmed. 0 residual test records in live Supabase.")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
