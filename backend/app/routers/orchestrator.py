import io
import logging
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.services.orchestrator_service import run_pipeline, get_session
from app.services.qdrant_service import search_filtered, collection_info
from app.services.export_service import generate_pdf, generate_docx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/workflow", tags=["Orchestrator"])


# ── Schemas ─────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    query          : str
    session_id     : Optional[str] = None
    top_k          : int           = 5
    issue_category : Optional[str] = None
    sentiment      : Optional[str] = None
    region         : Optional[str] = None

class GenerateStratkomRequest(BaseModel):
    session_id     : str
    issue_summary  : Optional[str] = None
    extra          : Optional[dict] = None

class ReviseRequest(BaseModel):
    session_id     : str
    user_edits     : Optional[str] = None

class ExportRequest(BaseModel):
    session_id     : str
    content_type   : Optional[str] = "stratkom"
    format         : Optional[str] = "pdf"


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/analyze", summary="Pipeline RAG penuh: Qdrant → Tim 2 → Tim 3")
def analyze(req: AnalyzeRequest):
    return run_pipeline(
        prompt=req.query,
        context=[],
        top_k=req.top_k,
        issue_category=req.issue_category,
        sentiment=req.sentiment,
        region=req.region,
    )


@router.post("/generate-stratkom", summary="Generate strategi komunikasi")
def generate_stratkom(req: GenerateStratkomRequest):
    # Jalankan pipeline dengan issue_summary sebagai prompt
    return run_pipeline(
        prompt=req.issue_summary or "Generate strategi komunikasi",
        context=[],
        top_k=3,
    )


@router.post("/revise", summary="Revisi draft stratkom")
def revise(req: ReviseRequest):
    return run_pipeline(
        prompt=req.user_edits or "Revisi strategi komunikasi",
        context=[],
        top_k=3,
    )


@router.post("/export", summary="Export hasil ke PDF/DOCX")
def export_content(req: ExportRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan. Jalankan analisis terlebih dahulu.")

    fmt = (req.format or "pdf").lower()
    if fmt not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Format tidak didukung. Gunakan 'pdf' atau 'docx'.")

    content_type = (req.content_type or "stratkom").lower()
    if content_type not in ("narasi", "stratkom", "draft"):
        raise HTTPException(status_code=400, detail="content_type harus 'narasi', 'stratkom', atau 'draft'.")

    download_url = f"/v1/workflow/download/{req.session_id}/{content_type}.{fmt}"
    return {
        "status"      : "success",
        "session_id"  : req.session_id,
        "content_type": content_type,
        "format"      : fmt,
        "export_url"  : download_url,
        "message"     : None,
    }


@router.get("/download/{session_id}/{filename}", summary="Download file PDF/DOCX")
def download_file(session_id: str, filename: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan atau sudah kedaluwarsa.")

    parts = filename.rsplit(".", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Nama file tidak valid.")

    content_type, fmt = parts[0], parts[1].lower()
    if fmt not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Format tidak didukung.")
    if content_type not in ("narasi", "stratkom", "draft"):
        raise HTTPException(status_code=400, detail="Tipe konten tidak valid.")

    try:
        if fmt == "pdf":
            data = generate_pdf(session, content_type)
            media_type = "application/pdf"
        else:
            data = generate_docx(session, content_type)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    except Exception as e:
        logger.error(f"[export/download] generate error: {e}")
        raise HTTPException(status_code=500, detail="Gagal membuat file. Coba lagi.")

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{session_id}-{content_type}.{fmt}"'},
    )


# ── Debug endpoints ──────────────────────────────────────────────────────────

@router.get("/search", summary="Debug: langsung search Qdrant")
def debug_search(
    query          : str           = Query(...),
    top_k          : int           = Query(5),
    issue_category : Optional[str] = Query(None),
    sentiment      : Optional[str] = Query(None),
    region         : Optional[str] = Query(None),
):
    try:
        results = search_filtered(
            query=query, top_k=top_k,
            issue_category=issue_category,
            sentiment=sentiment, region=region,
        )
        return {"query": query, "count": len(results), "results": results}
    except Exception as e:
        return {"error": str(e), "hint": "Pastikan Qdrant running di localhost:6333"}


@router.get("/qdrant/info", summary="Info jumlah vector di Qdrant")
def qdrant_status():
    try:
        return collection_info()
    except Exception as e:
        return {
            "error" : str(e),
            "hint"  : "Qdrant belum running atau collection belum dibuat.",
            "action": "Jalankan: python scripts/init_vector_db.py",
        }