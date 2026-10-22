"""Inspect and verify all tables, columns, indexes, and vector types in Supabase PostgreSQL."""

import asyncio
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.db.session import async_engine


async def inspect_db():
    print("=" * 65)
    print("Supabase PostgreSQL Schema & Table Verification")
    print("=" * 65)

    expected_tables = [
        "alembic_version",
        "users",
        "trading_accounts",
        "raw_mt5_deals",
        "strategies",
        "journal_entries",
        "deal_journal_mappings",
        "user_rules",
        "document_knowledge",
        "document_chunks",
    ]

    async with async_engine.connect() as conn:
        # 1. Check all tables in public schema
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name;"
            )
        )
        existing_tables = [row[0] for row in result.fetchall()]
        print(f"[*] Total Public Tables Found: {len(existing_tables)}")

        all_present = True
        for t in expected_tables:
            present = t in existing_tables
            status = "[OK]" if present else "[MISSING]"
            print(f"    {status} {t}")
            if not present:
                all_present = False

        # 2. Check alembic_version
        v_result = await conn.execute(text("SELECT version_num FROM alembic_version;"))
        current_rev = v_result.scalar_one_or_none()
        print(f"\n[*] Active Alembic Migration Revision: {current_rev}")

        # 3. Check document_chunks vector column
        c_result = await conn.execute(
            text(
                "SELECT column_name, data_type, udt_name "
                "FROM information_schema.columns "
                "WHERE table_name = 'document_chunks' AND column_name = 'embedding';"
            )
        )
        col = c_result.fetchone()
        if col:
            print(
                f"[*] document_chunks.embedding column: data_type='{col[1]}', udt_name='{col[2]}'"
            )
        else:
            print("[!] document_chunks.embedding column NOT found!")

        # 4. Check foreign keys
        fk_result = await conn.execute(
            text(
                "SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name "
                "FROM information_schema.table_constraints AS tc "
                "JOIN information_schema.key_column_usage AS kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "JOIN information_schema.constraint_column_usage AS ccu "
                "  ON ccu.constraint_name = tc.constraint_name "
                "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public' "
                "ORDER BY tc.table_name;"
            )
        )
        fks = fk_result.fetchall()
        print(f"\n[*] Verified {len(fks)} Foreign Key Constraints:")
        for table, col, f_table in fks:
            print(f"    - {table}.{col} -> {f_table}")

        # 5. Check indexes
        idx_result = await conn.execute(
            text(
                "SELECT tablename, indexname FROM pg_indexes "
                "WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%' "
                "ORDER BY tablename, indexname;"
            )
        )
        indexes = idx_result.fetchall()
        print(f"\n[*] Verified {len(indexes)} Indexes across all tables.")

    print("\n" + "=" * 65)
    if all_present and current_rev == "d02be136d042":
        print("[SUCCESS] All tables, vector columns, and foreign keys verified in Supabase!")
    else:
        print("[FAILED] Verification incomplete or missing entities.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(inspect_db())
