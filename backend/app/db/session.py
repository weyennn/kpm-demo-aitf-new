from contextlib import asynccontextmanager
import psycopg
from app.core.settings import DATABASE_URL as _SETTINGS_URL

# psycopg pakai format postgresql:// bukan postgresql+psycopg://
DATABASE_URL = _SETTINGS_URL.replace("postgresql+psycopg://", "postgresql://")


@asynccontextmanager
async def get_conn():
    """Async context manager untuk koneksi database."""
    conn = await psycopg.AsyncConnection.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()
