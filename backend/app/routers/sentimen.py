"""
Sentimen API — data real dari PostgreSQL untuk halaman Analisis Sentimen.

  GET /v1/sentimen/stats   → ringkasan sentimen, tren 7 hari, per platform, per isu
"""
import logging
from fastapi import APIRouter
from app.db.session import get_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/sentimen", tags=["Sentimen"])


@router.get("/stats")
async def get_sentimen_stats():
    try:
        async with get_conn() as conn:
            cur = conn.cursor()

            # 1. Ringkasan sentimen keseluruhan
            await cur.execute("""
                SELECT sentiment, COUNT(*) FROM labeled_content GROUP BY sentiment
            """)
            rows = await cur.fetchall()
            total = sum(r[1] for r in rows) or 1
            sent_map = {r[0]: r[1] for r in rows}
            pos = sent_map.get("positif", 0)
            neg = sent_map.get("negatif", 0)
            net = sent_map.get("netral",  0)

            # 2. Tren 7 hari
            await cur.execute("""
                SELECT
                    DATE(rc.crawl_timestamp) AS day,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'positif') AS pos,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'negatif') AS neg,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'netral')  AS net,
                    COUNT(*) AS total
                FROM labeled_content lc
                JOIN raw_content rc ON lc.source_id = rc.content_id
                WHERE rc.crawl_timestamp >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(rc.crawl_timestamp)
                ORDER BY day ASC
            """)
            trend_rows = await cur.fetchall()
            trend = [
                {
                    "date"   : str(r[0]),
                    "positif": round(r[1] / max(r[4], 1) * 100, 1),
                    "negatif": round(r[2] / max(r[4], 1) * 100, 1),
                    "netral" : round(r[3] / max(r[4], 1) * 100, 1),
                }
                for r in trend_rows
            ]

            # 3. Per platform
            await cur.execute("""
                SELECT
                    rc.platform,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'positif') AS pos,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'negatif') AS neg,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'netral')  AS net,
                    COUNT(*) AS total
                FROM labeled_content lc
                JOIN raw_content rc ON lc.source_id = rc.content_id
                GROUP BY rc.platform
                ORDER BY total DESC
            """)
            plat_rows = await cur.fetchall()
            PLAT_LABEL = {
                "media_online": "Media Online", "tiktok": "TikTok",
                "youtube_shorts": "YouTube Shorts", "instagram": "Instagram",
                "twitter": "Twitter/X",
            }
            platform = [
                {
                    "platform": PLAT_LABEL.get(r[0], r[0]),
                    "positif" : round(r[1] / max(r[4], 1) * 100, 1),
                    "negatif" : round(r[2] / max(r[4], 1) * 100, 1),
                    "netral"  : round(r[3] / max(r[4], 1) * 100, 1),
                }
                for r in plat_rows
            ]

            # 4. Per isu (keyword_corpus)
            await cur.execute("""
                SELECT
                    kc.keyword_text,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'positif') AS pos,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'negatif') AS neg,
                    COUNT(*) FILTER (WHERE lc.sentiment = 'netral')  AS net,
                    COUNT(*) AS total
                FROM keyword_corpus kc
                LEFT JOIN raw_content rc ON rc.keyword_refs @> ARRAY[kc.keyword_text::varchar]
                LEFT JOIN labeled_content lc ON lc.source_id = rc.content_id
                WHERE kc.is_active = true
                GROUP BY kc.keyword_text
                ORDER BY total DESC
                LIMIT 10
            """)
            isu_rows = await cur.fetchall()
            per_isu = [
                {
                    "isu": r[0],
                    "pos": round(r[1] / max(r[4], 1) * 100),
                    "neu": round(r[3] / max(r[4], 1) * 100),
                    "neg": round(r[2] / max(r[4], 1) * 100),
                }
                for r in isu_rows if r[4] > 0
            ]

            return {
                "ringkasan": {
                    "positif": round(pos / total * 100, 1),
                    "negatif": round(neg / total * 100, 1),
                    "netral" : round(net / total * 100, 1),
                    "total"  : total,
                },
                "trend"   : trend,
                "platform": platform,
                "per_isu" : per_isu,
            }

    except Exception as e:
        logger.error(f"[sentimen/stats] DB error: {e}")
        return _dummy()


def _dummy():
    return {
        "ringkasan": {"positif": 0, "negatif": 0, "netral": 0, "total": 0},
        "trend"    : [],
        "platform" : [],
        "per_isu"  : [],
    }
