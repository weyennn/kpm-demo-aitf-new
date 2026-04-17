"""
Monitoring API — data real dari PostgreSQL untuk halaman Monitoring Isu.

  GET /v1/monitoring/stats   → distribusi sentimen, subtopik terpanas,
                               volume per platform, total percakapan
  GET /v1/monitoring/issues  → daftar isu aktif per keyword
"""

import logging
from fastapi import APIRouter
from app.db.session import get_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/monitoring", tags=["Monitoring"])

# Mapping nama panjang taxonomy → label pendek untuk frontend
CATEGORY_MAP = {
    "Integritas & Penegakan Hukum":       "Hukum",
    "Kebijakan & Layanan Publik":          "Kebijakan",
    "Kinerja Pemerintah":                  "Pemerintah",
    "Keamanan Siber & Ketertiban Digital": "Digital",
    "Kesejahteraan & Bantuan Sosial":      "Sosial",
    "Infrastruktur & Layanan Transportasi":"Infrastruktur",
    "Ekonomi Digital":                     "Digital",
    "Ketenagakerjaan":                     "Ekonomi",
    "Layanan Kesehatan":                   "Kesehatan",
    "Pendidikan dan Pengembangan SDM":     "Pendidikan",
    "Krisis Sosial & Kebencanaan":         "Bencana",
}

PLATFORM_LABEL = {
    "media_online":   "Media Online",
    "tiktok":         "TikTok",
    "youtube_shorts": "YouTube Shorts",
    "instagram":      "Instagram",
    "google_trends":  "Google Trends",
}

SENTIMENT_COLOR = {
    "positif": "bg-success",
    "negatif": "bg-danger",
    "netral":  "bg-warning",
}

PLATFORM_COLOR = {
    "media_online":   "bg-warning",
    "tiktok":         "bg-success",
    "youtube_shorts": "bg-primary",
    "instagram":      "bg-danger",
}


# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats", summary="Statistik untuk halaman Monitoring Isu")
async def get_monitoring_stats():
    try:
        async with get_conn() as conn:
            cur = conn.cursor()

            # 1. Distribusi sentimen
            await cur.execute("""
                SELECT sentiment, COUNT(*) FROM labeled_content GROUP BY sentiment
            """)
            sent_rows = await cur.fetchall()
            sent_total = sum(r[1] for r in sent_rows) or 1
            distribusi_sentimen = [
                {
                    "l": r[0].capitalize(),
                    "p": round(r[1] / sent_total * 100, 1),
                    "c": SENTIMENT_COLOR.get(r[0], "bg-surface"),
                }
                for r in sorted(sent_rows, key=lambda x: -x[1])
            ]

            # 2. Subtopik terpanas (keyword dengan volume terbanyak)
            await cur.execute("""
                SELECT kc.keyword_text, COUNT(rc.content_id) AS vol
                FROM keyword_corpus kc
                LEFT JOIN raw_content rc ON rc.keyword_refs @> ARRAY[kc.keyword_id]
                WHERE kc.is_active = true
                GROUP BY kc.keyword_id, kc.keyword_text
                ORDER BY vol DESC
                LIMIT 5
            """)
            topik_rows = await cur.fetchall()
            max_vol = topik_rows[0][1] if topik_rows else 1
            subtopik_terpanas = [
                {
                    "lbl": r[0],
                    "vol": f"{r[1] / 1000:.1f}K" if r[1] >= 1000 else str(r[1]),
                    "pct": round(r[1] / max(max_vol, 1) * 100),
                    "c":   "bg-danger" if i == 0 else ("bg-warning" if i == 1 else "bg-primary"),
                }
                for i, r in enumerate(topik_rows)
            ]

            # 3. Volume per platform
            await cur.execute("""
                SELECT platform, COUNT(*) AS vol
                FROM raw_content
                GROUP BY platform
                ORDER BY vol DESC
            """)
            plat_rows = await cur.fetchall()
            max_plat = plat_rows[0][1] if plat_rows else 1
            PLAT_COLORS = ["bg-primary", "bg-success", "bg-warning", "bg-danger"]
            volume_per_platform = [
                {
                    "lbl": PLATFORM_LABEL.get(r[0], r[0]),
                    "vol": f"{r[1] / 1000:.1f}K" if r[1] >= 1000 else str(r[1]),
                    "pct": round(r[1] / max(max_plat, 1) * 100),
                    "c":   PLAT_COLORS[i % len(PLAT_COLORS)],
                }
                for i, r in enumerate(plat_rows)
            ]

            # 4. Total percakapan & isu aktif
            total_row = await (await cur.execute("SELECT COUNT(*) FROM raw_content")).fetchone()
            isu_row   = await (await cur.execute(
                "SELECT COUNT(*) FROM keyword_corpus WHERE is_active = true"
            )).fetchone()

            # 5. Subtopik trending tags
            await cur.execute(
                "SELECT keyword_text FROM keyword_corpus WHERE is_active = true ORDER BY keyword_text"
            )
            trending_tags = [r[0] for r in await cur.fetchall()]

            return {
                "distribusi_sentimen":  distribusi_sentimen,
                "subtopik_terpanas":    subtopik_terpanas,
                "volume_per_platform":  volume_per_platform,
                "isu_aktif":            isu_row[0] if isu_row else 0,
                "total_percakapan":     total_row[0] if total_row else 0,
                "subtopik_trending":    trending_tags,
            }

    except Exception as e:
        logger.error(f"[monitoring/stats] DB error: {e}")
        return _dummy_stats()


@router.get("/issues", summary="Daftar isu aktif per keyword")
async def get_monitoring_issues():
    try:
        async with get_conn() as conn:
            cur = conn.cursor()

            # Ambil semua keyword aktif + volume + platform
            await cur.execute("""
                SELECT
                    kc.keyword_id,
                    kc.keyword_text,
                    kc.taxonomy_category,
                    COUNT(rc.content_id)                        AS vol,
                    string_agg(DISTINCT rc.platform::text, ',') AS platforms,
                    COUNT(rc.content_id) FILTER (
                        WHERE rc.crawl_timestamp >= CURRENT_DATE - INTERVAL '7 days'
                    )                                           AS recent_vol,
                    COUNT(rc.content_id) FILTER (
                        WHERE rc.crawl_timestamp >= CURRENT_DATE - INTERVAL '14 days'
                        AND   rc.crawl_timestamp <  CURRENT_DATE - INTERVAL '7 days'
                    )                                           AS prev_vol
                FROM keyword_corpus kc
                LEFT JOIN raw_content rc ON (
                    rc.keyword_refs @> ARRAY[kc.keyword_id::varchar]
                    OR rc.keyword_refs @> ARRAY[kc.keyword_text::varchar]
                )
                WHERE kc.is_active = true
                GROUP BY kc.keyword_id, kc.keyword_text, kc.taxonomy_category
                ORDER BY vol DESC
            """)
            kw_rows = await cur.fetchall()

            issues = []
            for idx, row in enumerate(kw_rows):
                kw_id, kw_text, taxonomy, vol, platforms_str, recent, prev = row

                # Sentimen: ambil dari labeled_content yang source_id-nya
                # ada di raw_content dengan keyword ini
                await cur.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE lc.sentiment = 'positif') AS pos,
                        COUNT(*) FILTER (WHERE lc.sentiment = 'negatif') AS neg,
                        COUNT(*) FILTER (WHERE lc.sentiment = 'netral')  AS net,
                        COUNT(*)                                          AS total
                    FROM labeled_content lc
                    WHERE lc.source_id IN (
                        SELECT content_id FROM raw_content
                        WHERE keyword_refs @> ARRAY[%s::varchar]
                           OR keyword_refs @> ARRAY[%s::varchar]
                    )
                """, [kw_id, kw_text])
                pct_row = await cur.fetchone()
                pos, neg, net, total_lbl = pct_row if pct_row else (0, 0, 0, 0)

                if total_lbl > 0:
                    if pos >= neg and pos >= net:
                        dominant_sent = "positif"
                        sent_pct = f"+{round(pos / total_lbl * 100)}%"
                    elif neg >= pos and neg >= net:
                        dominant_sent = "negatif"
                        sent_pct = f"-{round(neg / total_lbl * 100)}%"
                    else:
                        dominant_sent = "netral"
                        sent_pct = f"{round(net / total_lbl * 100)}%"
                else:
                    dominant_sent = "netral"
                    sent_pct = "–"

                # Trend: % perubahan volume minggu ini vs minggu lalu
                if prev and prev > 0:
                    trend_val = round((recent - prev) / prev * 100)
                elif recent and recent > 0:
                    trend_val = 100
                else:
                    trend_val = 0
                trend_up   = trend_val >= 0
                trend_str  = f"+{trend_val}%" if trend_up else f"{trend_val}%"

                # Platform labels — platforms_str: "tiktok,media_online,youtube_shorts"
                plat_labels = [
                    PLATFORM_LABEL.get(p.strip(), p.strip())
                    for p in (platforms_str or "").split(",")
                    if p.strip()
                ]

                # Subtopik: keyword lain dalam kategori yang sama
                await cur.execute("""
                    SELECT keyword_text FROM keyword_corpus
                    WHERE is_active = true
                      AND taxonomy_category = %s
                      AND keyword_id != %s
                    LIMIT 2
                """, [taxonomy, kw_id])
                related = [r[0] for r in await cur.fetchall()]
                subtopik = [kw_text] + related

                kat_short = CATEGORY_MAP.get(taxonomy or "", taxonomy or "Umum")

                issues.append({
                    "id":      str(idx + 1).zfill(2),
                    "nama":    kw_text.title(),
                    "kat":     kat_short,
                    "subtopik": subtopik,
                    "vol":     vol or 0,
                    "sent":    dominant_sent,
                    "sentPct": sent_pct,
                    "platform": plat_labels,
                    "trend":   trend_str,
                    "up":      trend_up,
                })

            return issues

    except Exception as e:
        logger.error(f"[monitoring/issues] DB error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Fallback
# ─────────────────────────────────────────────────────────────────────────────

def _dummy_stats():
    return {
        "distribusi_sentimen":  [],
        "subtopik_terpanas":    [],
        "volume_per_platform":  [],
        "isu_aktif":            0,
        "total_percakapan":     0,
        "subtopik_trending":    [],
    }
