"""
Endpoint pengiriman dan polling task.

POST /api/tasks/rag           — kirim kueri RAG, langsung mengembalikan task_id
POST /api/tasks/ingest        — picu jalankan ingest secara manual
GET  /api/tasks/{task_id}     — polling status + hasil task
GET  /api/tasks               — daftar task terbaru (untuk halaman riwayat frontend)
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.tasks.ingest import embed_pending_content
from app.tasks.rag import run_rag_query

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ── Model request / response ──────────────────────────────────────────────────

class RagQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    taxonomy_filter: Optional[str] = None   # contoh: "health", "economy"


class IngestTriggerRequest(BaseModel):
    limit: int = 100  # jumlah baris yang akan diproses


class TaskStatusResponse(BaseModel):
    task_id: str
    task_type: str
    status: str          # pending | started | success | failure
    result: Optional[dict] = None
    error_msg: Optional[str] = None
    created_at: str
    updated_at: str


# ── Fungsi pembantu ───────────────────────────────────────────────────────────

def _create_task_row(db: Session, task_id: str, task_type: str, payload: dict):
    db.execute(
        text("""
            INSERT INTO task_results (task_id, task_type, status, payload)
            VALUES (:tid, :ttype, 'pending', :payload::jsonb)
        """),
        {"tid": task_id, "ttype": task_type, "payload": str(payload)},
    )
    db.commit()


def _fetch_task(db: Session, task_id: str) -> dict | None:
    row = db.execute(
        text("""
            SELECT task_id, task_type, status, result, error_msg,
                   created_at, updated_at
              FROM task_results
             WHERE task_id = :tid
        """),
        {"tid": task_id},
    ).fetchone()
    return dict(row._mapping) if row else None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/rag", status_code=202)
def submit_rag_query(body: RagQueryRequest, db: Session = Depends(get_db)):
    """
    Kirim kueri RAG untuk diproses secara asinkron.

    Mengembalikan task_id yang harus di-poll frontend di GET /api/tasks/{task_id}.
    Respons HTTP 202 menandakan task telah diterima — belum selesai diproses.
    """
    task_id = str(uuid.uuid4())
    _create_task_row(
        db,
        task_id,
        "rag_query",
        {
            "query": body.query,
            "top_k": body.top_k,
            "taxonomy_filter": body.taxonomy_filter,
        },
    )

    # Kirim ke antrian prioritas tinggi — tidak memblokir
    run_rag_query.apply_async(
        kwargs={
            "task_id": task_id,
            "query": body.query,
            "top_k": body.top_k,
            "taxonomy_filter": body.taxonomy_filter,
        },
        task_id=task_id,
        queue="high",
    )

    return {"task_id": task_id, "status": "pending"}


@router.post("/ingest", status_code=202)
def trigger_ingest(body: IngestTriggerRequest, db: Session = Depends(get_db)):
    """
    Picu jalankan ingest secara manual (berguna untuk pengujian atau setelah crawl besar).
    Job beat terjadwal berjalan otomatis setiap 6 jam — ini untuk penggunaan on-demand.
    """
    task_id = str(uuid.uuid4())
    _create_task_row(db, task_id, "ingest", {"limit": body.limit})

    embed_pending_content.apply_async(
        kwargs={"limit": body.limit},
        task_id=task_id,
        queue="ingest",
    )

    return {"task_id": task_id, "status": "pending", "limit": body.limit}


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """
    Poll task berdasarkan ID-nya. Terus poll sampai status 'success' atau 'failure'.

    Interval polling frontend yang disarankan: 2 detik untuk 30 detik pertama, lalu 5 detik.
    """
    row = _fetch_task(db, task_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} tidak ditemukan")
    return TaskStatusResponse(
        task_id=row["task_id"],
        task_type=row["task_type"],
        status=row["status"],
        result=row["result"],
        error_msg=row["error_msg"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.get("", response_model=list[TaskStatusResponse])
def list_tasks(
    limit: int = Query(default=20, le=100),
    task_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Tampilkan task terbaru, terbaru duluan. Berguna untuk halaman riwayat."""
    query = """
        SELECT task_id, task_type, status, result, error_msg, created_at, updated_at
          FROM task_results
    """
    params: dict = {"limit": limit}
    if task_type:
        query += " WHERE task_type = :task_type"
        params["task_type"] = task_type
    query += " ORDER BY created_at DESC LIMIT :limit"

    rows = db.execute(text(query), params).fetchall()
    return [
        TaskStatusResponse(
            task_id=r["task_id"],
            task_type=r["task_type"],
            status=r["status"],
            result=r["result"],
            error_msg=r["error_msg"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )
        for r in rows
    ]
