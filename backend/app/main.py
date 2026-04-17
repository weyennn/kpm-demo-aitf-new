from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.settings import MODEL_MODE
from app.routers.tim2 import router as tim2_router
from app.routers.tim3 import router as tim3_router
from app.routers.orchestrator import router as orchestrator_router
from app.routers.dashboard import router as dashboard_router
from app.routers.monitoring import router as monitoring_router
from app.routers.sentimen import router as sentimen_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    log = logging.getLogger(__name__)
    try:
        from app.db.migrate import run_migrations
        run_migrations()
    except Exception as e:
        log.warning(f"Migration gagal (lanjut): {e}")
    try:
        from app.services.qdrant_service import setup_collection
        setup_collection()
    except Exception as e:
        log.warning(f"Qdrant setup gagal (lanjut): {e}")
    yield

app = FastAPI(
    lifespan=lifespan,
    title="Tim 4 RAG + MVP Backend",
    description=(
        "Backend orkestrator Tim 4. "
        "Prefix /mock/v1/tim2 dan /mock/v1/tim3 adalah simulasi "
        "API Tim 2 & Tim 3 untuk development paralel."
    ),
    version="0.2.0",
)

# CORS harus didaftarkan SEBELUM router agar header terbawa ke semua endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tim2_router)
app.include_router(tim3_router)
app.include_router(orchestrator_router)
app.include_router(dashboard_router)
app.include_router(monitoring_router)
app.include_router(sentimen_router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": "0.2.0", "mode": MODEL_MODE}
