"""
Model ORM SQLAlchemy milik backend Tim 4.

Tabel-tabel ini dibuat di database PostgreSQL yang sama dengan yang digunakan
crawler, sehingga query JOIN antara raw_content ↔ ingest_log dapat dilakukan
tanpa koneksi kedua.
"""
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Integer, JSON, String, Text
)
from sqlalchemy.sql import func

from app.database import Base


class IngestLog(Base):
    """
    Melacak setiap baris raw_content yang telah di-embed dan dikirim ke Qdrant.

    - content_id  sesuai dengan raw_content.content_id (PK milik crawler)
    - status      'success' | 'failed'
    - chunk_count jumlah potongan teks yang dibuat dari dokumen tersebut
    """
    __tablename__ = "ingest_log"

    content_id = Column(String, primary_key=True)
    batch_id = Column(String, nullable=False)       # task-id Celery atau id run beat
    qdrant_point_id = Column(String, nullable=True) # UUID titik pertama (untuk pencarian)
    chunk_count = Column(Integer, default=1)
    status = Column(String, nullable=False, default="success")
    error_msg = Column(Text, nullable=True)
    ingested_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TaskResult(Base):
    """
    Menyimpan status task Celery asinkron agar frontend dapat melakukan polling.

    Siklus hidup:  pending → started → success | failure
    Kolom 'result' menyimpan payload JSON yang dikembalikan task saat berhasil.
    """
    __tablename__ = "task_results"

    task_id = Column(String, primary_key=True)
    task_type = Column(String, nullable=False)  # 'rag_query' | 'stratkom' | dll.
    status = Column(String, nullable=False, default="pending")
    payload = Column(JSON, nullable=True)       # isi permintaan asli
    result = Column(JSON, nullable=True)        # output task saat berhasil
    error_msg = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
