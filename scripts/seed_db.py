"""
seed_db.py
----------
Mengisi tabel yang kosong agar frontend dapat menampilkan semua data:

  1. labeled_content     — sentimen untuk raw_content yang ada
  2. raw_content (seed)  — tambah data tiktok & youtube untuk grafik trend
  3. keyword_trend_history — riwayat tren keyword 7 hari
  4. post_comment        — komentar sample per konten

Jalankan:
  cd kpm
  python scripts/seed_db.py
"""

import os
import uuid
import random
from datetime import datetime, timedelta, timezone, date
from dotenv import load_dotenv
import psycopg

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../backend/.env"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://team4:team4pass@127.0.0.1:55432/team4db"
).replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")

SENTIMENTS   = ["positif", "negatif", "netral"]
PLATFORMS    = ["tiktok", "youtube_shorts", "media_online"]
CATEGORIES   = [
    "Integritas & Penegakan Hukum",
    "Kebijakan & Layanan Publik",
    "Kinerja Pemerintah",
    "Keamanan Siber & Ketertiban Digital",
    "Kesejahteraan & Bantuan Sosial",
    "Infrastruktur & Layanan Transportasi",
    "Ekonomi Digital",
    "Ketenagakerjaan",
    "Layanan Kesehatan",
    "Pendidikan dan Pengembangan SDM",
    "Krisis Sosial & Kebencanaan",
]

NOW = datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# 1. labeled_content — sentimen untuk semua raw_content
# ─────────────────────────────────────────────────────────────────────────────

def seed_labeled_content(conn):
    existing = conn.cursor().execute("SELECT COUNT(*) FROM labeled_content").fetchone()[0]
    if existing > 0:
        print(f"  [labeled_content] sudah ada {existing} rows, skip.")
        return

    rows = conn.cursor().execute(
        "SELECT content_id, taxonomy_category, batch_id FROM raw_content WHERE success = true LIMIT 1000"
    ).fetchall()

    # Distribusi sentimen: 40% netral, 35% negatif, 25% positif
    weights = [0.25, 0.35, 0.40]
    batch_id = rows[0][2] if rows else "batch-seed"

    data = [
        (
            f"lbl-{uuid.uuid4().hex[:12]}",
            "post",
            row[0],
            "auto",
            row[1] or random.choice(CATEGORIES),
            random.choices(SENTIMENTS, weights=weights)[0],
            round(random.uniform(0.65, 0.98), 4),
            False,
            "seeder",
            NOW - timedelta(hours=random.randint(1, 72)),
            batch_id,
        )
        for row in rows
    ]

    conn.cursor().executemany("""
        INSERT INTO labeled_content
            (label_id, source_type, source_id, label_type, taxonomy_category,
             sentiment, confidence_score, is_verified, labeled_by, labeled_at, batch_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, data)

    print(f"  [labeled_content] insert {len(data)} rows ✓")


# ─────────────────────────────────────────────────────────────────────────────
# 2. raw_content — tambah data tiktok & youtube untuk grafik trend 7 hari
# ─────────────────────────────────────────────────────────────────────────────

def seed_raw_content_platforms(conn):
    existing_tiktok = conn.cursor().execute(
        "SELECT COUNT(*) FROM raw_content WHERE platform = 'tiktok'"
    ).fetchone()[0]

    if existing_tiktok > 0:
        print(f"  [raw_content tiktok] sudah ada {existing_tiktok} rows, skip.")
        return

    keywords = conn.cursor().execute(
        "SELECT keyword_id, keyword_text, taxonomy_category FROM keyword_corpus WHERE is_active = true"
    ).fetchall()
    batch_id = conn.cursor().execute(
        "SELECT batch_id FROM batch_manifest ORDER BY start_time DESC LIMIT 1"
    ).fetchone()
    batch_id = batch_id[0] if batch_id else "batch-seed"

    sample_texts = {
        "tiktok": [
            "Isu ini lagi rame banget di TikTok, banyak yang komen",
            "Video viral soal kebijakan baru pemerintah",
            "Netizen ramai bahas ini di FYP hari ini",
            "Trending di TikTok! Banyak yang setuju dan tidak setuju",
        ],
        "youtube_shorts": [
            "Shorts tentang isu terkini yang perlu kamu tahu",
            "Penjelasan singkat kebijakan pemerintah terbaru",
            "Reaksi warganet terhadap kebijakan baru",
            "Update terbaru yang viral di YouTube Shorts",
        ],
    }

    sample_texts["media_online"] = [
        "Pemerintah umumkan kebijakan baru terkait isu terkini",
        "Analisis mendalam situasi nasional yang perlu diperhatikan",
        "Laporan khusus: perkembangan isu publik minggu ini",
        "Pakar sebut kebijakan perlu segera ditindaklanjuti",
    ]

    data = []
    today = date.today()
    for days_ago in range(7):
        crawl_date = today - timedelta(days=days_ago)
        for platform in ["tiktok", "youtube_shorts", "media_online"]:
            count = random.randint(15, 40) if platform != "media_online" else random.randint(80, 150)
            content_type = "video" if platform != "media_online" else "article"
            for _ in range(count):
                kw = random.choice(keywords)
                text = random.choice(sample_texts[platform])
                data.append((
                    f"cnt-{platform[:2]}-{crawl_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
                    platform,
                    content_type,
                    f"{text} #{kw[1]}",
                    None,
                    f"https://{platform}.com/watch/{uuid.uuid4().hex[:8]}",
                    f"user_{uuid.uuid4().hex[:6]}",
                    [kw[0]],
                    kw[2] or random.choice(CATEGORIES),
                    round(random.uniform(0.6, 0.95), 4),
                    None,
                    crawl_date,
                    datetime.combine(crawl_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                    + timedelta(hours=random.randint(6, 22)),
                    True,
                    batch_id,
                ))

    conn.cursor().executemany("""
        INSERT INTO raw_content
            (content_id, platform, content_type, raw_text, media_urls, url_source,
             author_id, keyword_refs, taxonomy_category, taxonomy_confidence,
             extra_metadata, publish_date, crawl_timestamp, success, batch_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, data)

    print(f"  [raw_content tiktok+youtube+media] insert {len(data)} rows ✓")


# ─────────────────────────────────────────────────────────────────────────────
# 3. keyword_trend_history — riwayat tren 7 hari per keyword
# ─────────────────────────────────────────────────────────────────────────────

def seed_keyword_trend_history(conn):
    existing = conn.cursor().execute("SELECT COUNT(*) FROM keyword_trend_history").fetchone()[0]
    if existing > 0:
        print(f"  [keyword_trend_history] sudah ada {existing} rows, skip.")
        return

    keywords = conn.cursor().execute(
        "SELECT keyword_id FROM keyword_corpus WHERE is_active = true"
    ).fetchall()

    data = []
    today = date.today()
    for kw in keywords:
        base_score = random.randint(40, 80)
        for days_ago in range(7):
            snap_date = datetime.combine(
                today - timedelta(days=days_ago),
                datetime.min.time()
            ).replace(tzinfo=timezone.utc)
            score = max(0, min(100, base_score + random.randint(-10, 10)))
            data.append((
                f"hist-{uuid.uuid4().hex[:12]}",
                kw[0],
                snap_date,
                score,
                '{"jawa": 45, "sumatera": 30, "kalimantan": 15, "lainnya": 10}',
                '[]',
                '[]',
            ))

    conn.cursor().executemany("""
        INSERT INTO keyword_trend_history
            (history_id, keyword_id, snapshot_date, interest_score,
             region_breakdown, related_queries, related_topics)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
        ON CONFLICT DO NOTHING
    """, data)

    print(f"  [keyword_trend_history] insert {len(data)} rows ✓")


# ─────────────────────────────────────────────────────────────────────────────
# 4. post_comment — komentar sample
# ─────────────────────────────────────────────────────────────────────────────

def seed_post_comment(conn):
    existing = conn.cursor().execute("SELECT COUNT(*) FROM post_comment").fetchone()[0]
    if existing > 0:
        print(f"  [post_comment] sudah ada {existing} rows, skip.")
        return

    posts = conn.cursor().execute(
        "SELECT content_id, platform, batch_id FROM raw_content WHERE platform IN ('tiktok','youtube_shorts') LIMIT 50"
    ).fetchall()

    if not posts:
        print("  [post_comment] belum ada konten tiktok/youtube, skip.")
        return

    sample_comments = [
        "Setuju banget sama ini!",
        "Kok bisa kayak gini ya?",
        "Pemerintah harus segera bertindak",
        "Sudah dari dulu harusnya dibenahi",
        "Semoga cepat ada solusinya",
        "Ini penting banget buat kita semua",
        "Gak heran sih, udah ketahuan dari lama",
        "Masih banyak yang belum paham nih",
    ]

    data = []
    for post in posts:
        for _ in range(random.randint(2, 6)):
            data.append((
                f"cmt-{uuid.uuid4().hex[:12]}",
                post[0],
                post[1],
                random.choice(sample_comments),
                f"user_{uuid.uuid4().hex[:6]}",
                random.randint(0, 500),
                False,
                None,
                NOW - timedelta(hours=random.randint(1, 48)),
                NOW - timedelta(hours=random.randint(0, 24)),
                post[2],
            ))

    conn.cursor().executemany("""
        INSERT INTO post_comment
            (comment_id, post_content_id, platform, comment_text, author_id,
             likes_count, is_reply, parent_comment_id, created_at, crawl_timestamp, batch_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, data)

    print(f"  [post_comment] insert {len(data)} rows ✓")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"Connecting to: {DATABASE_URL}")
    with psycopg.connect(DATABASE_URL) as conn:
        print("\n--- Seeding database ---")
        seed_raw_content_platforms(conn)
        seed_labeled_content(conn)
        seed_keyword_trend_history(conn)
        seed_post_comment(conn)
        conn.commit()
        print("\n✅ Seeding selesai!")

        # Ringkasan akhir
        print("\n--- Ringkasan ---")
        for t in ["raw_content", "labeled_content", "keyword_trend_history", "post_comment"]:
            count = conn.cursor().execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {count} rows")


if __name__ == "__main__":
    main()
