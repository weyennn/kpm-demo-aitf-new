"""
Engine SQLAlchemy sinkron untuk task Celery.

Worker Celery berjalan di pool proses/thread sendiri, sehingga digunakan
driver psycopg3 sinkron (postgresql+psycopg://) dan bukan asyncpg.
Route FastAPI yang membutuhkan akses DB asinkron sebaiknya menggunakan
session factory async tersendiri.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.settings import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # buang koneksi usang sebelum digunakan
    pool_recycle=300,     # daur ulang koneksi setiap 5 menit
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency FastAPI — menghasilkan sesi sinkron (untuk endpoint sederhana)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
