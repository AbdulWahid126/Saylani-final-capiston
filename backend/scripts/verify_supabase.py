"""Supabase & pgvector Connectivity Diagnostics Script.

Verifies database connectivity and pgvector extension availability
while strictly masking credentials and secrets according to RULES.md.
"""

import asyncio
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg

from app.core.config import settings


def mask_url(url: str) -> str:
    """Mask password and credentials in database URL for safe diagnostic output."""
    try:
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***REDACTED***@", url)
    except Exception:
        return "***MASKED_DATABASE_URL***"


async def verify_connectivity() -> bool:
    print("=" * 60)
    print("Supabase PostgreSQL & pgvector Connectivity Verification")
    print("=" * 60)

    raw_url = settings.DATABASE_URL
    masked = mask_url(raw_url)
    print(f"[*] Target Database URI (Masked): {masked}")

    # 1. Check for unresolved placeholder password
    if "[YOUR-PASSWORD]" in raw_url or "YOUR-PASSWORD" in raw_url:
        print("\n[!] CONFIGURATION ISSUE DETECTED:")
        print("    Your backend/.env contains the placeholder string '[YOUR-PASSWORD]'.")
        print("    Please replace '[YOUR-PASSWORD]' with your actual Supabase database password.")
        print("    Example: postgresql+asyncpg://postgres:YourActualPassword@...")
        return False

    # 2. Extract connection components
    # Convert SQLAlchemy dialect scheme to standard postgresql scheme for asyncpg
    asyncpg_url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw_url)
    asyncpg_url = re.sub(r"^postgres://", "postgresql://", asyncpg_url)

    parsed = urlparse(asyncpg_url)
    host = parsed.hostname or "unknown"
    port = parsed.port or 5432

    print(f"[*] Target Host: {host}")
    print(f"[*] Target Port: {port}")

    # 3. Direct connection IPv6 vs Pooler IPv4 Advisory
    if host.endswith(".supabase.co") and not host.startswith("aws-0-"):
        print("\n[i] NETWORK NOTICE (Supabase Direct vs Pooler):")
        print(f"    Targeting direct Supabase endpoint: '{host}'")
        print("    Supabase direct endpoints (*.supabase.co:5432) utilize IPv6.")
        print("    If your current ISP or local network lacks IPv6 routing, this direct")
        print("    handshake may encounter a DNS or socket resolution error.")
        print("    In such cases, Supabase connection pooler (IPv4) should be configured:")
        print(
            "    Format: postgresql+asyncpg://postgres.<PROJECT_REF>:[PASSWORD]@<POOLER_HOST>:5432/postgres?ssl=require"
        )

    print("\n[*] Initiating secure asyncpg handshake with SSL (timeout: 10s)...")
    start = time.perf_counter()

    try:
        # Connect with SSL required (Supabase standard)
        # Disable statement cache if connecting to connection pooler
        statement_cache = 0 if ("pooler.supabase.com" in host or port == 6543) else 100
        conn = await asyncpg.connect(
            asyncpg_url,
            timeout=10.0,
            ssl="require",
            statement_cache_size=statement_cache,
        )
        latency = round((time.perf_counter() - start) * 1000, 2)
        print(f"[+] Connection Established Successfully! (Latency: {latency} ms)")

        # 4. Check PostgreSQL version
        pg_version = await conn.fetchval("SELECT version();")
        print(f"[+] PostgreSQL Version: {pg_version.split(',')[0]}")

        # 5. Check pgvector extension status
        print("\n[*] Checking 'vector' extension status...")
        vector_installed = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector';"
        )

        if vector_installed and vector_installed > 0:
            version = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
            )
            print(f"[+] pgvector extension is ENABLED (Version: {version})")
        else:
            print("[-] pgvector extension is NOT currently enabled.")
            print(
                "[*] Attempting to enable pgvector via 'CREATE EXTENSION IF NOT EXISTS vector;'..."
            )
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                print("[+] pgvector extension successfully enabled!")
            except Exception as ext_err:
                print(f"[!] Failed to enable vector extension: {ext_err}")
                await conn.close()
                return False

        # 6. Verify vector operations
        test_vec = await conn.fetchval("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector;")
        print(f"[+] Vector distance calculation operational (L2 distance: {test_vec})")

        await conn.close()
        print("\n" + "=" * 60)
        print("[SUCCESS] All Supabase PostgreSQL & pgvector checks passed!")
        print("=" * 60)
        return True

    except asyncpg.exceptions.InvalidPasswordError:
        print("\n[!] AUTHENTICATION ERROR:")
        print("    Password authentication failed for the specified database user.")
        print("    Please check the password in backend/.env.")
        return False
    except (asyncpg.exceptions.CannotConnectNowError, OSError) as os_err:
        err_str = str(os_err)
        print("\n[!] NETWORK / CONNECTION ERROR:")
        print(f"    Details: {type(os_err).__name__}: {err_str}")
        if "IPv4 or IPv6 address" in err_str or "getaddrinfo" in err_str or "timed out" in err_str:
            print("\n[!] ROOT CAUSE ANALYSIS:")
            print(
                "    The Supabase direct domain 'db.<project-ref>.supabase.co' only resolves to IPv6."
            )
            print("    Your local network does not support IPv6 DNS resolution for this host.")
            print("    RECOMMENDED ACTION:")
            print("    Use the Supabase IPv4 Connection Pooler (Session mode, port 5432):")
            print(
                "    1. Go to Supabase Dashboard -> Project Settings -> Database -> Connection string."
            )
            print("    2. Select 'Connection Pooler' with Mode: 'Session' (port 5432).")
            print("    3. Update backend/.env DATABASE_URL to:")
            print(
                "       postgresql+asyncpg://postgres.yttnejtokrzdbeitftog:[YOUR_PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?ssl=require"
            )
        return False
    except Exception as e:
        print(f"\n[!] UNEXPECTED CONNECTION ERROR: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_connectivity())
    sys.exit(0 if success else 1)
