"""Async SQLAlchemy engine and session factory (ADR-003: PostgreSQL + PostGIS)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from routeopt.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.db_url, echo=settings.debug, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped async session."""
    async with SessionLocal() as session:
        yield session
