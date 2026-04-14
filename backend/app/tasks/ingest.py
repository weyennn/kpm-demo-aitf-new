"""
Task ingest — membaca data mentah crawler dari PostgreSQL, melakukan embedding
dengan sentence-transformers, lalu meng-upsert vektor ke Qdrant.

Antrian:  ingest
Worker:   1 proses concurrent (berat di CPU/RAM untuk model embedding)

Dua task tersedia:
  embed_pending_content  — job batch, memproses semua baris yang belum diproses (Celery Beat)
  embed_single_content   — job real-time, memproses satu baris segera setelah crawl
"""
from __future__ import annotations

import uuid
import logging
from typing import Optional

from celery import Task
from sqlalchemy import create_engine, text

from app.celery_app import celery
from app.database import SessionLocal
from app.settings import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATABASE_URL,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    INGEST_BATCH_SIZE,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    QDRANT_PORT,
)

logger = logging.getLogger(__name__)

# ── Singleton level modul — dimuat sekali per proses worker ──────────────────
_embedding_model = None
_qdrant_client = None


def _get_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Memuat model embedding: %s", EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def _get_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _qdrant_client


def _ensure_collection(qdrant):
    """Buat koleksi Qdrant jika belum ada."""
    from qdrant_client.models import Distance, VectorParams
    existing = {c.name for c in qdrant.get_collections().collections}
    if QDRANT_COLLECTION not in existing:
        qdrant.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info("Koleksi Qdrant dibuat: %s", QDRANT_COLLECTION)


def _chunk_text(raw: str) -> list[str]:
    """Pecah dokumen menjadi potongan teks bertumpang-tindih berbasis karakter."""
    if not raw or len(raw) <= CHUNK_SIZE:
        return [raw] if raw else []
    chunks, start = [], 0
    while start < len(raw):
        chunks.append(raw[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _embed_rows(rows: list, task_id: str) -> tuple[int, int]:
    """
    Logika embedding inti yang digunakan oleh kedua task.

    Mengembalikan (processed_count, failed_count).
    Menulis entri ingest_log ke database backend.
    """
    from qdrant_client.models import PointStruct

    model = _get_model()
    qdrant = _get_qdrant()
    _ensure_collection(qdrant)

    processed = 0
    failed = 0

    with SessionLocal() as db:
        for row in rows:
            content_id = row.content_id
            raw_text = row.raw_text or ""

            try:
                chunks = _chunk_text(raw_text)
                if not chunks:
                    continue

                vectors = model.encode(
                    chunks,
                    batch_size=EMBEDDING_BATCH_SIZE,
                    show_progress_bar=False,
                )

                points = [
                    PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{content_id}_{i}")),
                        vector=vec.tolist(),
                        payload={
                            "content_id": content_id,
                            "chunk_index": i,
                            "platform": row.platform,
                            "taxonomy_category": row.taxonomy_category,
                            "keyword_refs": row.keyword_refs or [],
                            "url_source": row.url_source,
                            "text": chunk,
                            "crawl_timestamp": str(row.crawl_timestamp),
                        },
                    )
                    for i, (chunk, vec) in enumerate(zip(chunks, vectors))
                ]

                qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)

                db.execute(
                    text("""
                        INSERT INTO ingest_log
                            (content_id, batch_id, qdrant_point_id, chunk_count, status)
                        VALUES
                            (:cid, :bid, :pid, :cc, 'success')
                        ON CONFLICT (content_id) DO NOTHING
                    """),
                    {
                        "cid": content_id,
                        "bid": task_id,
                        "pid": points[0].id if points else None,
                        "cc": len(chunks),
                    },
                )
                processed += 1

            except Exception as exc:
                failed += 1
                logger.error("Embedding gagal untuk %s: %s", content_id, exc)
                db.execute(
                    text("""
                        INSERT INTO ingest_log
                            (content_id, batch_id, status, error_msg)
                        VALUES
                            (:cid, :bid, 'failed', :err)
                        ON CONFLICT (content_id) DO UPDATE
                            SET status='failed', error_msg=EXCLUDED.error_msg
                    """),
                    {
                        "cid": content_id,
                        "bid": task_id,
                        "err": str(exc),
                    },
                )

        db.commit()

    return processed, failed


# ── Task: ingest batch (Celery Beat — setiap 6 jam) ──────────────────────────

@celery.task(
    name="ingest.embed_pending_content",
    bind=True,
    queue="ingest",
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
    rate_limit="4/h",  # maksimal 4 kali jalankan batch per jam
    track_started=True,
)
def embed_pending_content(self: Task, limit: int = INGEST_BATCH_SIZE) -> dict:
    """
    Memindai raw_content untuk baris yang belum ada di ingest_log, lalu embed.
    Aman dijalankan bersamaan — ON CONFLICT DO NOTHING mencegah pekerjaan ganda.
    """
    logger.info("[ingest] embed_pending_content dimulai (limit=%d)", limit)

    # Gunakan engine terpisah agar task ini tidak berbagi connection pool FastAPI.
    crawler_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    try:
        with crawler_engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT
                        rc.content_id,
                        rc.raw_text,
                        rc.platform,
                        rc.taxonomy_category,
                        rc.keyword_refs,
                        rc.url_source,
                        rc.crawl_timestamp
                    FROM raw_content rc
                    LEFT JOIN ingest_log il ON rc.content_id = il.content_id
                    WHERE il.content_id IS NULL
                      AND rc.raw_text IS NOT NULL
                      AND rc.raw_text <> ''
                    ORDER BY rc.crawl_timestamp DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()
    except Exception as exc:
        logger.error("[ingest] Gagal mengambil data dari DB: %s", exc)
        raise self.retry(exc=exc)

    if not rows:
        logger.info("[ingest] Tidak ada konten yang perlu diproses.")
        return {"status": "no_pending", "processed": 0, "failed": 0}

    logger.info("[ingest] %d baris akan di-embed", len(rows))
    processed, failed = _embed_rows(rows, task_id=self.request.id or "beat")

    result = {
        "status": "ok",
        "processed": processed,
        "failed": failed,
        "total_fetched": len(rows),
    }
    logger.info("[ingest] embed_pending_content selesai: %s", result)
    return result


# ── Task: ingest satu item (dipicu oleh API crawler setelah satu batch) ───────

@celery.task(
    name="ingest.embed_single_content",
    bind=True,
    queue="ingest",
    max_retries=5,
    default_retry_delay=30,
    acks_late=True,
    rate_limit="60/m",  # perlindungan dari lonjakan data crawler
    track_started=True,
)
def embed_single_content(self: Task, content_id: str) -> dict:
    """
    Embed satu baris raw_content berdasarkan content_id-nya.
    Dipanggil oleh layanan crawler tepat setelah menyisipkan baris baru.
    """
    logger.info("[ingest] embed_single_content: %s", content_id)

    crawler_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    try:
        with crawler_engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT
                        rc.content_id,
                        rc.raw_text,
                        rc.platform,
                        rc.taxonomy_category,
                        rc.keyword_refs,
                        rc.url_source,
                        rc.crawl_timestamp
                    FROM raw_content rc
                    WHERE rc.content_id = :cid
                      AND rc.raw_text IS NOT NULL
                      AND rc.raw_text <> ''
                """),
                {"cid": content_id},
            ).fetchall()
    except Exception as exc:
        raise self.retry(exc=exc)

    if not rows:
        logger.warning("[ingest] content_id tidak ditemukan atau kosong: %s", content_id)
        return {"status": "not_found", "content_id": content_id}

    processed, failed = _embed_rows(rows, task_id=self.request.id or "manual")
    return {
        "status": "ok" if processed else "failed",
        "content_id": content_id,
        "processed": processed,
        "failed": failed,
    }
