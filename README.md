# KPM — Tim 4: RAG + MVP
**AITF 2026 · Komdigi · Use Case Komunikasi Publik & Media**

Sistem RAG (Retrieval-Augmented Generation) end-to-end untuk monitoring isu publik, analisis narasi, dan rekomendasi strategi komunikasi berbasis AI.

---

## Struktur Folder

```
kpm/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI entrypoint
│       ├── core/            # Settings & konfigurasi
│       ├── routers/         # Endpoint API
│       ├── services/        # Business logic & RAG pipeline
│       └── db/              # Model & migrasi database
├── frontend/                # React + Vite + Tailwind CSS + TypeScript
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Tech Stack

### Backend
| Layer | Teknologi |
|---|---|
| API Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 16 |
| Vector DB | Qdrant |
| ORM | SQLAlchemy + Psycopg |
| LLM | Groq API |
| HTTP Client | HTTPX |
| Runtime | Python 3.11 |

### Frontend
| Layer | Teknologi |
|---|---|
| Framework | React 18 |
| Build tool | Vite |
| Styling | Tailwind CSS |
| Language | TypeScript |

---

## Services (Docker Compose)

| Container | Port | Fungsi |
|---|---|---|
| `tim4_postgres` | `5432` | Database utama |
| `tim4_qdrant` | `6333` | Vector database untuk RAG semantic search |
| `tim4_api` | `8000` | FastAPI REST API + Swagger UI |

---

## Setup & Menjalankan

### 1. Clone repo

```bash
git clone https://github.com/weyennn/kpm-demo-aitf-new.git
cd kpm
```

### 2. Buat file `.env`

Buat file `.env` di folder `backend/` berdasarkan contoh di `.env.example`.
Variabel yang wajib diisi:

```
DATABASE_URL=
GROQ_API_KEY=
QDRANT_URL=
```

> **Jangan pernah commit file `.env` ke repository.**

### 3. Jalankan backend

```bash
docker compose up --build -d
```

### 4. Jalankan frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## Verifikasi

| URL | Yang Diharapkan |
|---|---|
| http://localhost:8000/docs | Swagger UI FastAPI |
| http://localhost:8000/health | `{"status": "ok"}` |
| http://localhost:6333/dashboard | Qdrant Web UI |
| http://localhost:3000 | Frontend React |

---

## Arsitektur Pipeline

```
PostgreSQL (raw content dari crawler)
        │
   Tim 4 RAG
   ├─ semantic search → Qdrant
   ├─ analisis narasi → Tim 2 / Groq
   └─ strategi komunikasi → Tim 3 / Groq
                │
          MVP Frontend
   (monitoring · chat · narasi · stratkom)
```

### MODEL_MODE

| Mode | Fungsi |
|---|---|
| `groq` | Pakai Groq API (default) |
| `custom` | Pakai API real Tim 2 & Tim 3 |
| `mock` | Template hardcoded (offline/fallback) |

---

## Kontak Tim 4
1. Aswin Asrianto
2. Setia Mukti Azizah
3. Tengku Syaid Farhan
4. Ichsan Setiawan
5. Surya Karunia Ramadhan
6. Yayang Matira

---

*AITF 2026 · Komdigi · Direktorat Jenderal KPM*
