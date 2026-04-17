"""
Dashboard API — stats & trend untuk halaman utama.
Mengambil data real dari PostgreSQL (Tim 1):
  - GET /v1/dashboard/stats  → total konten, crawled hari ini, sentimen, batch terakhir
  - GET /v1/dashboard/trend  → tren konten per platform 7 hari terakhir
"""
import logging
from datetime import date, timedelta
from fastapi import APIRouter
from app.db.session import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/dashboard", tags=["Dashboard"])


@router.get("/stats", summary="Statistik utama dashboard")
async def get_stats():
    try:
        async with get_conn() as conn:
            # Total konten & crawled hari ini
            total, crawled_today = await (await conn.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (WHERE DATE(crawl_timestamp) = CURRENT_DATE)
                FROM raw_content
            """)).fetchone()

            # Sentimen dari labeled_content
            positif, negatif, netral, total_labeled = await (await conn.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE sentiment = 'positif'),
                    COUNT(*) FILTER (WHERE sentiment = 'negatif'),
                    COUNT(*) FILTER (WHERE sentiment = 'netral'),
                    COUNT(*)
                FROM labeled_content
            """)).fetchone()

            # Batch terakhir
            batch = await (await conn.execute("""
                SELECT batch_id, status, success_rate_pct, records_error, raw_data_count
                FROM batch_manifest
                ORDER BY start_time DESC
                LIMIT 1
            """)).fetchone()

            # Keyword aktif
            kw_row = await (await conn.execute("""
                SELECT COUNT(*) FROM keyword_corpus WHERE is_active = true
            """)).fetchone()
            active_keywords = kw_row[0] if kw_row else 0

            return {
                "total_content":   total,
                "crawled_today":   crawled_today,
                "active_keywords": active_keywords,
                "isu_aktif":       0,
                "sentiment": {
                    "positif":       round(positif / total_labeled * 100, 1) if total_labeled else 0,
                    "negatif":       round(negatif / total_labeled * 100, 1) if total_labeled else 0,
                    "netral":        round(netral  / total_labeled * 100, 1) if total_labeled else 0,
                    "total_labeled": total_labeled,
                },
                "latest_batch": {
                    "batch_id":         batch[0],
                    "status":           batch[1],
                    "success_rate_pct": float(batch[2]) if batch[2] is not None else 0.0,
                    "records_error":    batch[3],
                    "raw_data_count":   batch[4],
                } if batch else None,
            }
    except Exception as e:
        logger.error(f"[dashboard/stats] DB error: {e}")
        return _dummy_stats()


@router.get("/trend", summary="Tren konten per platform 7 hari terakhir")
async def get_trend():
    try:
        async with get_conn() as conn:
            rows = await (await conn.execute("""
                SELECT
                    DATE(crawl_timestamp)                                        AS day,
                    COUNT(*) FILTER (WHERE platform = 'media_online')            AS media,
                    COUNT(*) FILTER (WHERE platform = 'tiktok')                  AS tiktok,
                    COUNT(*) FILTER (WHERE platform = 'youtube_shorts')          AS youtube
                FROM raw_content
                WHERE crawl_timestamp >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(crawl_timestamp)
                ORDER BY day ASC
            """)).fetchall()

            return {
                "data": [
                    {
                        "date":    str(r[0]),
                        "media":   r[1],
                        "tiktok":  r[2],
                        "youtube": r[3],
                    }
                    for r in rows
                ]
            }
    except Exception as e:
        logger.error(f"[dashboard/trend] DB error: {e}")
        return {"data": _dummy_trend()}


# ---------------------------------------------------------------------------
# Fallback dummy — dikembalikan jika DB belum tersedia
# ---------------------------------------------------------------------------

def _dummy_stats():
    return {
        "total_content":   0,
        "crawled_today":   0,
        "active_keywords": 0,
        "isu_aktif":       0,
        "sentiment":       {"positif": 0, "negatif": 0, "netral": 0, "total_labeled": 0},
        "latest_batch":    None,
    }


def _dummy_trend():
    today = date.today()
    return [
        {"date": str(today - timedelta(days=6 - i)), "media": 0, "tiktok": 0, "youtube": 0}
        for i in range(7)
    ]
