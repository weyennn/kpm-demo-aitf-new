"""
settings.py
-----------
Konfigurasi aplikasi Tim 4 dibaca dari environment variable (.env).
Semua nilai punya default agar server tetap bisa jalan tanpa .env lengkap.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Database ────────────────────────────────────────────────────────────────
POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT     = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "tim4db")
POSTGRES_USER     = os.getenv("POSTGRES_USER", "tim4")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "tim4pass")

# Prioritaskan DATABASE_URL dari env (Railway/Supabase inject langsung)
# Fallback ke build dari POSTGRES_* vars
_db_url = os.getenv("DATABASE_URL")
if _db_url:
    # Normalisasi ke format psycopg
    DATABASE_URL = (
        _db_url
        .replace("postgresql+asyncpg://", "postgresql+psycopg://")
        .replace("postgresql://", "postgresql+psycopg://")
    )
else:
    DATABASE_URL = (
        f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

# ── Redis / Celery ───────────────────────────────────────────────────────────
REDIS_HOST            = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT            = os.getenv("REDIS_PORT", "6379")
CELERY_BROKER_URL     = os.getenv("CELERY_BROKER_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", f"redis://{REDIS_HOST}:{REDIS_PORT}/1")

# ── Qdrant ──────────────────────────────────────────────────────────────────
QDRANT_URL     = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# ── External AI Services (Tim 2 & Tim 3 real API) ───────────────────────────
TIM2_BASE_URL  = os.getenv("TIM2_API_URL",  "")
TIM2_API_KEY   = os.getenv("TIM2_API_KEY",  "")
TIM2_MODEL_ID  = os.getenv("TIM2_MODEL_ID", "indo-sft-v1")

TIM3_BASE_URL  = os.getenv("TIM3_API_URL",  "")
TIM3_API_KEY   = os.getenv("TIM3_API_KEY",  "")
TIM3_MODEL_ID  = os.getenv("TIM3_MODEL_ID", "team3-comm-strategy-sft-v1")

# ── OpenRouter (fallback saat Tim 2/Tim 3 belum siap) ───────────────────────
OPENROUTER_API_KEY    = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL   = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL_TIM2 = os.getenv("OPENROUTER_MODEL_TIM2", "meta-llama/llama-3.1-8b-instruct:free")
OPENROUTER_MODEL_TIM3 = os.getenv("OPENROUTER_MODEL_TIM3", "meta-llama/llama-3.1-8b-instruct:free")

# ── App ─────────────────────────────────────────────────────────────────────
APP_ENV     = os.getenv("APP_ENV", "development")
# "mock" | "openrouter" | "custom" (Tim 2/Tim 3 real)
MODEL_MODE  = os.getenv("MODEL_MODE", "openrouter")
DEBUG       = os.getenv("DEBUG", "false").lower() == "true"
