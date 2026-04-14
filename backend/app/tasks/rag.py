"""
Task kueri RAG — memproses permintaan pencarian semantik + generasi secara asinkron.

Antrian:  high  (real-time, menghadap pengguna; diproses sebelum pekerjaan ingest)

Alur:
  1. Embed string kueri
  2. Cari top-k chunk terdekat di Qdrant
  3. Ambil baris raw_content yang cocok dari PostgreSQL untuk metadata
  4. Bangun blok konteks dan panggil API LLM Tim 2 / Tim 3
     (di-mock sampai layanan tersebut tersedia)
  5. Simpan hasil di task_results agar frontend dapat melakukan polling

Route pemanggil (POST /api/tasks/rag) membuat baris TaskResult terlebih dahulu,
lalu mengirimkan task ini. Pembaruan progres ditulis kembali ke baris yang sama.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text

from app.celery_app import celery
from app.database import SessionLocal
from app.settings import (
    DATABASE_URL,
    EMBEDDING_MODEL,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    QDRANT_PORT,
)

logger = logging.getLogger(__name__)

# ── Singleton yang sama dengan ingest — dimuat malas per proses ───────────────
_embedding_model = None
_qdrant_client = None


def _get_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def _get_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _qdrant_client


def _update_task(db, task_id: str, status: str, result=None, error_msg: str | None = None):
    db.execute(
        text("""
            UPDATE task_results
               SET status    = :status,
                   result    = :result,
                   error_msg = :error_msg,
                   updated_at = now()
             WHERE task_id = :task_id
        """),
        {
            "task_id": task_id,
            "status": status,
            "result": result,
            "error_msg": error_msg,
        },
    )
    db.commit()


# ── Task ──────────────────────────────────────────────────────────────────────

@celery.task(
    name="rag.run_query",
    bind=True,
    queue="high",
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
    time_limit=120,   # matikan paksa setelah 2 menit — cegah panggilan LLM tak berujung
    soft_time_limit=90,
    track_started=True,
)
def run_rag_query(
    self,
    task_id: str,
    query: str,
    top_k: int = 5,
    taxonomy_filter: Optional[str] = None,
) -> dict:
    """
    Jalankan kueri RAG dan simpan hasilnya di task_results.

    Parameter
    ----------
    task_id        : UUID yang sudah disisipkan ke task_results sebelumnya
    query          : Pertanyaan / deskripsi isu dari pengguna (Bahasa Indonesia OK)
    top_k          : Jumlah hasil Qdrant yang digunakan sebagai konteks
    taxonomy_filter: taxonomy_category opsional untuk mempersempit ruang pencarian
    """
    logger.info("[rag] run_query dimulai task_id=%s query=%.60s", task_id, query)

    with SessionLocal() as db:
        _update_task(db, task_id, "started")

    try:
        # ── 1. Embed kueri ────────────────────────────────────────────────────
        model = _get_model()
        query_vec = model.encode(query, show_progress_bar=False).tolist()

        # ── 2. Pencarian semantik di Qdrant ───────────────────────────────────
        qdrant = _get_qdrant()
        search_filter = None
        if taxonomy_filter:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            search_filter = Filter(
                must=[FieldCondition(
                    key="taxonomy_category",
                    match=MatchValue(value=taxonomy_filter),
                )]
            )

        hits = qdrant.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vec,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )

        # ── 3. Ambil baris yang cocok dari PostgreSQL ─────────────────────────
        from sqlalchemy import create_engine
        crawler_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

        content_ids = list({h.payload.get("content_id") for h in hits if h.payload})
        context_rows = []

        if content_ids:
            with crawler_engine.connect() as conn:
                rows = conn.execute(
                    text("""
                        SELECT content_id, raw_text, platform,
                               taxonomy_category, url_source, crawl_timestamp
                          FROM raw_content
                         WHERE content_id = ANY(:ids)
                    """),
                    {"ids": content_ids},
                ).fetchall()
            context_rows = [dict(r._mapping) for r in rows]

        # ── 4. Bangun blok konteks ────────────────────────────────────────────
        context_chunks = []
        for hit in hits:
            pl = hit.payload or {}
            context_chunks.append(
                f"[{pl.get('platform','?')} | skor={hit.score:.3f}]\n"
                f"{pl.get('text', '')}"
            )

        context_text = "\n\n---\n\n".join(context_chunks)

        # ── 5. Panggil LLM Tim 2 / Tim 3 (di-mock sampai tersedia) ───────────
        llm_response = _call_llm_mock(query, context_text)

        # ── 6. Simpan hasil ───────────────────────────────────────────────────
        result_payload = {
            "query": query,
            "answer": llm_response["answer"],
            "sources": [
                {
                    "content_id": h.payload.get("content_id"),
                    "platform": h.payload.get("platform"),
                    "url_source": h.payload.get("url_source"),
                    "score": round(h.score, 4),
                    "snippet": (h.payload.get("text") or "")[:200],
                }
                for h in hits
                if h.payload
            ],
            "context_rows": len(context_rows),
        }

        with SessionLocal() as db:
            _update_task(db, task_id, "success", result=result_payload)

        logger.info("[rag] run_query selesai task_id=%s", task_id)
        return result_payload

    except Exception as exc:
        logger.error("[rag] run_query gagal task_id=%s error=%s", task_id, exc)
        with SessionLocal() as db:
            _update_task(db, task_id, "failure", error_msg=str(exc))
        raise self.retry(exc=exc)


# ── Helper mock LLM (ganti dengan panggilan HTTP nyata ke Tim 2 / Tim 3) ─────

def _call_llm_mock(query: str, context: str) -> dict:
    """
    Placeholder sampai API Tim 2 (analisis isu) / Tim 3 (stratkom) aktif.
    Mengembalikan stub terstruktur agar pipeline frontend dapat diuji end-to-end.
    """
    snippet = context[:300].replace("\n", " ") if context else "(tidak ada konteks yang ditemukan)"
    return {
        "answer": (
            f"[MOCK] Berdasarkan {len(context.split(chr(10)))} baris konteks yang ditemukan, "
            f"analisis untuk pertanyaan '{query[:80]}' sedang diproses. "
            f"Konteks awal: {snippet}…"
        ),
        "model": "mock-v0",
    }
