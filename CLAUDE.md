# TIM KPM 4 — RAG + MVP
> AITF 2026 · Komdigi · Use Case Komunikasi Publik & Media
> Repo: https://github.com/setiazizah/kpm

---

## Tim & Peran

| Nama | Peran |
|------|-------|
| Setia Mukti Azizah | Team Lead |
| Tengku Syaid Farhan | Frontend Engineer |
| Ichsan Setiawan | ML Engineer |
| Yayang Matira | ML Engineer |
| Surya Karunia Ramadhan | Backend Engineer |
| Aswin Asrianto | Backend Engineer |

---

## Struktur Folder Repo

```
kpm/
├── backend/
│   └── app/
│       ├── main.py                      # FastAPI entrypoint (uvicorn app.main:app)
│       ├── celery_app.py                # Celery config & task definitions
│       ├── core/__init__.py
│       ├── core/settings.py             # Konfigurasi app (membaca .env)
│       ├── db/__init__.py
│       ├── db/session.py                # Koneksi PostgreSQL async
│       ├── mocks/__init__.py
│       ├── mocks/mock_responses.py      # Template hardcoded (fallback offline)
│       ├── routers/orchestrator.py      # Endpoint pipeline utama
│       ├── routers/tim2.py              # Mock router Tim 2 (/mock/v1/tim2)
│       ├── routers/tim3.py              # Mock router Tim 3 (/mock/v1/tim3)
│       ├── routers/dashboard.py         # Dashboard stats
│       ├── routers/monitoring.py        # Monitoring isu
│       ├── services/orchestrator_service.py  # Pipeline RAG (Qdrant → Tim2/3 → OpenRouter)
│       ├── services/qdrant_service.py   # Operasi Qdrant
│       ├── services/embedder.py         # multilingual-e5-small wrapper
│       ├── services/export_service.py   # PDF/DOCX export
│       └── tasks/ingestion.py           # Celery task: PostgreSQL → Qdrant
├── frontend/                   # React 18 + Vite + Tailwind CSS + TypeScript
│   ├── src/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.cjs
│   └── tsconfig.json
├── team1-crawler/              # Modul crawler Tim 1 (ada di repo ini)
├── .env                        # ← buat sendiri, jangan di-commit
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Tech Stack (Versi Aktual dari requirements.txt)

### Backend

| Package | Versi |
|---------|-------|
| fastapi | 0.115.0 |
| uvicorn[standard] | 0.30.6 |
| celery | 5.4.0 |
| redis | 5.0.8 |
| psycopg[binary] | 3.2.1 |
| sqlalchemy | 2.0.34 |
| qdrant-client | 1.11.1 |
| python-dotenv | 1.0.1 |
| pydantic | 2.9.2 |
| httpx | 0.27.2 |
| sentence-transformers | 3.0.1 |

> ⚠️ `sentence-transformers` download ~470MB pertama kali (model multilingual-e5)

### Frontend

| Layer | Teknologi |
|-------|-----------|
| Framework | React 18 |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Language | TypeScript |

---

## Docker Compose Services (6 Container)

| Container | Port Host | Port Container | Fungsi |
|-----------|-----------|----------------|--------|
| `tim4_postgres` | `55432` | `5432` | PostgreSQL 16 |
| `tim4_pgadmin` | `8080` | `80` | pgAdmin UI |
| `tim4_qdrant` | `6333` | `6333` | Vector DB |
| `tim4_redis` | `6379` | `6379` | Redis 7-alpine (broker) |
| `tim4_api` | `8000` | `8000` | FastAPI (--reload) |
| `tim4_worker` | — | — | Celery worker |

> ⚠️ PostgreSQL di-expose port **55432** (bukan 5432) untuk hindari konflik lokal.

### Credentials Default

| Service | Credential |
|---------|------------|
| PostgreSQL | user: `tim4` / pass: `tim4pass` / db: `tim4db` |
| pgAdmin | email: `tim4@ugm.com` / pass: `tim4pass` |

### Docker Volumes
- `pgdata` → PostgreSQL data persistence
- `pgadmindata` → pgAdmin config persistence
- `qdrantdata` → Qdrant vector storage

### Commands di Container
```bash
# API service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Worker service
celery -A app.celery_app.celery worker --loglevel=INFO
```

---

## Setup & Menjalankan

### 1. Clone repo
```bash
git clone https://github.com/setiazizah/kpm.git
cd kpm
```

### 2. Buat file `.env` di root `kpm/`
```env
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=tim4db
POSTGRES_USER=tim4
POSTGRES_PASSWORD=tim4pass

# Redis / Celery
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Qdrant
QDRANT_URL=http://qdrant:6333

# OpenRouter (aktif saat MODEL_MODE=openrouter)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL_TIM2=qwen/qwen-2.5-72b-instruct
OPENROUTER_MODEL_TIM3=qwen/qwen-2.5-72b-instruct

# Tim 2 & Tim 3 real API (aktif saat MODEL_MODE=custom)
TIM2_API_URL=http://host.docker.internal:9002/v1
TIM2_API_KEY=
TIM3_API_URL=http://host.docker.internal:9003/v1
TIM3_API_KEY=

# Mode model: 'openrouter' | 'custom' (Tim 2/3 real) | 'mock' (offline fallback)
MODEL_MODE=openrouter
```

### 3. Jalankan backend
```bash
docker compose up --build        # pertama kali
docker compose up --build -d     # background mode
```

### 4. Jalankan frontend (terpisah)
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## Verifikasi Setelah Up

| URL | Expected |
|-----|----------|
| http://localhost:8000/docs | Swagger UI FastAPI |
| http://localhost:8000/health | `{"status": "ok"}` |
| http://localhost:6333/dashboard | Qdrant Dashboard |
| http://localhost:8080 | pgAdmin UI |
| http://localhost:3000 | Frontend React |

### Test pipeline endpoint
```bash
# Pipeline utama (Qdrant → OpenRouter/Tim2 → OpenRouter/Tim3)
curl -X POST http://localhost:8000/v1/workflow/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Analisis isu kenaikan BBM", "top_k": 5}'

# Mock Tim 2 (untuk dev/testing)
curl -X POST http://localhost:8000/mock/v1/tim2/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analisis isu kenaikan BBM", "context": []}'

# Cek status Qdrant
curl http://localhost:8000/v1/workflow/qdrant/info
```

---

## Command Harian

```bash
docker compose up -d                      # start tanpa rebuild
docker compose down                       # stop
docker compose logs -f api                # log API real-time
docker compose logs -f worker             # log worker real-time
docker compose up --build -d api          # rebuild setelah ubah kode backend
docker compose down -v                    # reset total (hapus semua data)
```

---

## API Contract Antar Tim

### Tim 4 → Tim 2 (Analisis Narasi Isu)
- Base URL: `https://apicontract-tim2.netlify.app/`
- `POST /v1/completions` — Generate narasi isu
- `POST /v1/chat/completions` — Chatbot agentic multi-turn
- `GET /v1/models` → `indo-sft-v1`
- Auth: `Authorization: Bearer <API_KEY>` · Timeout: 30s

### Tim 4 → Tim 3 (Strategi Komunikasi)
- Base URL: `https://apicontract-tim3.netlify.app/`
- `POST /v1/completions` — Generate stratkom
- `POST /v1/chat/completions` — Chatbot StratKom
- `GET /v1/crawlers/status` — Monitor corpus regulasi
- Auth: `Authorization: Bearer <API_KEY>` · Timeout: 30s

### Tim 4 Internal Endpoints
- `POST /api/v1/query` — User query dari frontend
- `POST /v1/workflow/analyze` — Trigger orkestrasi
- `POST /v1/workflow/generate-stratkom` — Generate strategi
- `POST /v1/workflow/revise` — Revisi dokumen
- `POST /mock/v1/completions` — Mock saat `MODEL_MODE=mock`

---

## Workflow Orkestrasi (5 Steps)

```
Step 1: RETRIEVAL  → Qdrant (semantic) + BM25/PG FTS (lexical) — Hybrid Search
Step 2: NARASI     → POST /v1/completions ke Tim 2 (Indo-SFT-v1)
Step 3: STRATKOM   → POST /v1/chat/completions ke Tim 3 (StratKom-SFT)
Step 4: REVISION   → LLM Revision + python-docx
Step 5: EXPORT     → DOCX/PDF via Celery Async
```

### RAG Pipeline
- **Chunker:** 512–1024 token
- **Embedder:** `sentence-transformers` multilingual-e5 (multi-provider siap)
- **HybridRetriever:** Qdrant semantic + BM25/PG FTS, ratio 0.7:0.3 via RRF (ADR-003)
- **Reranker:** aktif Fase 3
- **PromptBuilder:** Jinja2 (`narasi_fallback.jinja2`, `stratkom_fallback.jinja2`, `revision_fallback.jinja2`)

### Fallback Engine
Trigger: HTTP 500 / Timeout >60s / API key tidak diset / Exception
```
Priority: OpenRouter (atau Custom Tim2/3) → Mock template hardcoded
```
State: `fallback_used: true` di `step_meta.tim2 / step_meta.tim3` → dicatat di response.

### Celery Workers
- Ingestion Worker — schedule tiap 6 jam
- Export Worker
- Monitoring Worker
- Broker: `redis://redis:6379/0`

---

## Database Schema

### PostgreSQL — Tabel `raw_content`
```sql
content_id          VARCHAR(64) PRIMARY KEY
platform            platform_enum       -- tiktok | youtube_shorts | media_online
content_type        content_type_enum   -- article | video | audio | post_comment
url_source          TEXT UNIQUE
author_id           VARCHAR(64)
batch_id            VARCHAR
raw_text            TEXT
media_urls          JSONB               -- { images: [], videos: [] }
keyword_refs        TEXT[]
taxonomy_category   TEXT
taxonomy_confidence FLOAT
extra_metadata      JSONB               -- view_count, editor, dll
publish_date        DATE
crawl_timestamp     TIMESTAMPTZ
updated_at          TIMESTAMPTZ
ingestion_status    TEXT                -- 'done' | 'pending' | 'failed'
```

### Tabel Lainnya (total 11 tabel)
`batch_manifest`, `keyword_corpus`, `keyword_status_log`, `keyword_trend_history`,
`taxonomy_category`, `labeled_content`, `post_comment`, `audio_manifest`,
`image_manifest`, `crawler_config`, `rag_queries`

Skema lengkap: `docs/SkemaDB_Tim4_v2.docx`

### Qdrant — Collection `vector_chunks`
```json
{
  "id": "chunk_001",
  "vector": [0.23, -0.71, 0.88, "..."],
  "payload": {
    "content_id": "cnt-mo-20260309-a8f12c",
    "chunk_index": 1,
    "platform": "media_online",
    "content_type": "article",
    "taxonomy_category": "Layanan Kesehatan",
    "publish_date": "2026-03-09"
  }
}
```

---

## ADR (Architecture Decision Records)

| ADR | Keputusan | Status |
|-----|-----------|--------|
| ADR-001 | Fallback LLM: GPT-4o → Gemini → Dummy jika Tim 2/3 error/timeout | ✅ Accepted |
| ADR-002 | Benchmark 3 embedding: OpenAI / Google / intfloat (multilingual-e5) | 🔲 Proposed |
| ADR-003 | Hybrid search semantic + BM25, ratio 0.7:0.3 via RRF | ✅ Accepted |
| ADR-005 | Batch embedding tiap 6 jam via Celery + Redis | ✅ Accepted |

---

## Status

- [x] Arsitektur end-to-end & diagram flow antar tim
- [x] API Contract Tim 4 ↔ Tim 2 (v0.2)
- [x] API Contract Tim 4 ↔ Tim 3 (v0.2)
- [x] Dev environment — 6 service via Docker Compose (+ pgAdmin)
- [x] Skema DB PostgreSQL v0.2 (disesuaikan Tim 1)
- [x] Struktur metadata Qdrant
- [x] Mock endpoint Tim 2 & Tim 3 (`/mock/v1/tim2`, `/mock/v1/tim3`)
- [x] RAG ingestion pipeline (Celery task: PostgreSQL → embed → Qdrant)
- [x] Integrasi OpenRouter sebagai pengganti mock (MODEL_MODE=openrouter)
- [x] Qdrant retrieval aktif di pipeline (`search_filtered` dipanggil di Step 1)
- [ ] Data contract final dengan Tim 1
- [ ] Konfirmasi base URL & API key Tim 2 dan Tim 3 (untuk MODEL_MODE=custom)
- [ ] Benchmark embedding model (ADR-002)
- [ ] Hybrid search BM25 + Qdrant (ADR-003)

---

## Konvensi Kode

- Backend: Python 3.11-slim (Docker), working dir: `/app/backend`
- Import app: `from app.main import app` | Celery: `from app.celery_app import celery`
- Config via `.env` → dibaca `app/settings.py` (python-dotenv)
- Semua LLM call: retry 3x + fallback ADR-001
- Response format: OpenAI-compatible (`choices[].message.content`)
- DOCX export: `python-docx` + Jinja2 template

---

*CLAUDE.md — Knowledge base Claude Code. Source: https://github.com/setiazizah/kpm*
