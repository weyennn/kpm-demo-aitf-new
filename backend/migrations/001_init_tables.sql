-- Migration 001: Inisialisasi tabel Tim 1
-- Jalankan sekali di Railway PostgreSQL (Query tab)

-- ── keyword_corpus ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS keyword_corpus (
    keyword_id        SERIAL PRIMARY KEY,
    keyword_text      TEXT NOT NULL,
    taxonomy_category TEXT,
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── raw_content ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_content (
    content_id        SERIAL PRIMARY KEY,
    platform          TEXT,
    crawl_timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    keyword_refs      TEXT[] DEFAULT '{}',
    content           TEXT,
    source_url        TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── labeled_content ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS labeled_content (
    label_id          SERIAL PRIMARY KEY,
    source_id         INTEGER REFERENCES raw_content(content_id) ON DELETE CASCADE,
    sentiment         TEXT CHECK (sentiment IN ('positif', 'negatif', 'netral')),
    issue_category    TEXT,
    issue_summary     TEXT,
    labeled_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── batch_manifest ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS batch_manifest (
    batch_id          TEXT PRIMARY KEY,
    status            TEXT NOT NULL DEFAULT 'pending',
    start_time        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time          TIMESTAMPTZ,
    raw_data_count    INTEGER DEFAULT 0,
    records_error     INTEGER DEFAULT 0,
    success_rate_pct  NUMERIC(5, 2) DEFAULT 0
);

-- ── Index untuk performa query ────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_raw_content_platform        ON raw_content (platform);
CREATE INDEX IF NOT EXISTS idx_raw_content_crawl_timestamp ON raw_content (crawl_timestamp);
CREATE INDEX IF NOT EXISTS idx_labeled_content_sentiment   ON labeled_content (sentiment);
CREATE INDEX IF NOT EXISTS idx_keyword_corpus_is_active    ON keyword_corpus (is_active);
CREATE INDEX IF NOT EXISTS idx_batch_manifest_start_time   ON batch_manifest (start_time DESC);
