"""Async SQLAlchemy engine and session factory."""

import os
import socket
import tempfile
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)


def is_postgres_running(host: str = "localhost", port: int = 5432) -> bool:
    """Quick check to see if local PostgreSQL server is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=0.15):
            return True
    except (OSError, TimeoutError):
        return False


def get_active_database_url() -> str:
    url = settings.DATABASE_URL

    # If on Vercel or explicitly testing, or localhost postgres is unreachable, fallback to SQLite
    is_vercel = bool(os.environ.get("VERCEL"))
    is_localhost = "localhost" in url or "127.0.0.1" in url

    if is_vercel or (is_localhost and not is_postgres_running()):
        temp_dir = tempfile.gettempdir().replace("\\", "/")
        sqlite_url = f"sqlite+aiosqlite:///{temp_dir}/nivaas.db"
        logger.info("Using SQLite fallback database: %s", sqlite_url)
        return sqlite_url

    return url


db_url = get_active_database_url()
is_sqlite = "sqlite" in db_url

async_engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    **({} if is_sqlite else {"pool_size": 5, "max_overflow": 10}),
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)



async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
