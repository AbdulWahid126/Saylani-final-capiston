from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# SQLAlchemy 2.0 Async Engine
engine_kwargs = {
    "echo": settings.DEBUG and not settings.is_production,
    "future": True,
}

# Add pool pre-ping and pooler configurations for network databases
connect_args: dict[str, Any] = {}
if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
    )
    # Supabase Transaction Pooler (port 6543) requires statement_cache_size=0
    if "pooler.supabase.com" in settings.DATABASE_URL or ":6543" in settings.DATABASE_URL:
        connect_args["statement_cache_size"] = 0

if connect_args:
    engine_kwargs["connect_args"] = connect_args

async_engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing a transactional async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
