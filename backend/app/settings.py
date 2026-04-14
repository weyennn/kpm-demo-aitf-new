import os
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────────
# PostgreSQL bersama — tabel crawler (raw_content, dll.) dan tabel backend
# (ingest_log, task_results) semuanya berada di database yang sama.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://tim4:tim4pass@postgres:5432/tim4db",
)

# ── Celery / Redis ────────────────────────────────────────────────────────────
CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

# ── Penyimpanan vektor Qdrant ─────────────────────────────────────────────────
QDRANT_HOST: str = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "kpm_content")

# ── Model embedding ───────────────────────────────────────────────────────────
# Multilingual MiniLM — ringan, mendukung teks Bahasa Indonesia, output 384-dim.
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))
EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

# ── Pengaturan ingest ─────────────────────────────────────────────────────────
# Jumlah baris raw_content yang diproses per satu kali pemanggilan task ingest.
INGEST_BATCH_SIZE: int = int(os.getenv("INGEST_BATCH_SIZE", "100"))

# Pemecahan teks berbasis karakter untuk artikel panjang.
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "64"))
