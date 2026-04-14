"""
Aplikasi Celery untuk backend Tim 4 KPM.

Tiga antrian bernama memisahkan beban kerja yang berbeda:

  high    — kueri RAG real-time dari frontend (butuh latensi rendah)
  ingest  — embedding batch / upsert Qdrant (berat di CPU, boleh ditunda)
  default — antrian cadangan untuk task tanpa antrian eksplisit

Worker dapat dijalankan dengan konkurensi yang disesuaikan per antrian:
  celery -A app.celery_app.celery worker -Q high    -c 4 --loglevel=INFO
  celery -A app.celery_app.celery worker -Q ingest  -c 1 --loglevel=INFO
  celery -A app.celery_app.celery worker -Q default -c 2 --loglevel=INFO

Celery Beat menjalankan ingest terjadwal setiap 6 jam (sesuai jadwal crawler).
"""
import os
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

broker  = os.getenv("CELERY_BROKER_URL",     "redis://redis:6379/0")
backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery = Celery("tim4", broker=broker, backend=backend)

# ── Temukan task secara otomatis di sub-paket tasks ──────────────────────────
celery.autodiscover_tasks(["app.tasks"])

# ── Definisi antrian ──────────────────────────────────────────────────────────
default_exchange = Exchange("default", type="direct")
high_exchange    = Exchange("high",    type="direct")
ingest_exchange  = Exchange("ingest",  type="direct")

celery.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("high",    high_exchange,    routing_key="high"),
    Queue("ingest",  ingest_exchange,  routing_key="ingest"),
)
celery.conf.task_default_queue       = "default"
celery.conf.task_default_exchange    = "default"
celery.conf.task_default_routing_key = "default"

# ── Routing task eksplisit (menimpa argumen queue= sebagai fallback) ─────────
celery.conf.task_routes = {
    "rag.*":    {"queue": "high"},
    "ingest.*": {"queue": "ingest"},
    "tasks.*":  {"queue": "ingest"},
}

# ── Perilaku worker ───────────────────────────────────────────────────────────
celery.conf.worker_prefetch_multiplier  = 1     # satu task per slot worker
celery.conf.task_acks_late              = True  # masukkan ulang ke antrian jika worker mati
celery.conf.task_reject_on_worker_lost  = True

# ── Serialisasi ───────────────────────────────────────────────────────────────
celery.conf.task_serializer   = "json"
celery.conf.result_serializer = "json"
celery.conf.accept_content    = ["json"]

# ── TTL hasil task ────────────────────────────────────────────────────────────
celery.conf.result_expires = 3600  # simpan hasil task di Redis selama 1 jam

# ── Zona waktu ────────────────────────────────────────────────────────────────
celery.conf.timezone       = "Asia/Jakarta"
celery.conf.enable_utc     = True
celery.conf.task_track_started = True

# ── Jadwal Celery Beat ────────────────────────────────────────────────────────
# Menjalankan embed_pending_content setiap 6 jam, sesuai batch berita crawler.
celery.conf.beat_schedule = {
    "embed-pending-every-6h": {
        "task":    "ingest.embed_pending_content",
        "schedule": crontab(minute=30, hour="*/6"),  # menit ke-30 setiap 6 jam
        "options": {"queue": "ingest"},
        "kwargs":  {"limit": int(os.getenv("INGEST_BATCH_SIZE", "100"))},
    },
}
