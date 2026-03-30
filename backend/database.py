"""Database session and initialization."""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from backend.config import settings
from backend.models import Base


def _async_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+asyncpg://", 1) \
              .replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)


def _sync_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


# Async engine — used by all FastAPI request handlers
async_engine = create_async_engine(
    _async_url(settings.DATABASE_URL),
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine — used only by init_db() and backup restore
sync_engine = create_engine(_sync_url(settings.DATABASE_URL))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        yield session


def init_db():
    """Initialize database tables and run migrations (synchronous)."""
    Base.metadata.create_all(bind=sync_engine)

    from alembic.config import Config
    from alembic import command

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))

    print("Running database migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("Database migrations applied successfully.")
    except Exception as e:
        print(f"Error applying migrations: {e}")
