"""
Pipeline utama Tim 4 (RAG + OpenRouter):

  Step 1 — RETRIEVAL : Embed query → search Qdrant → ambil top-K chunks
  Step 2 — NARASI    : Kirim query + context ke Tim 2 / OpenRouter → narasi isu
  Step 3 — STRATKOM  : Kirim narasi ke Tim 3 / OpenRouter → strategi komunikasi
  Step 4 — RETURN    : Gabungkan hasil ke frontend

MODEL_MODE di settings:
  "openrouter" — pakai OpenRouter API (default)
  "custom"     — pakai API real Tim 2 & Tim 3
  "mock"       — pakai template hardcoded (fallback / offline)
"""

import re
import uuid
import json
import logging
import httpx
import os
from collections import OrderedDict

from app.services.qdrant_service import search_filtered
from app.core.settings import (
    MODEL_MODE,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL_TIM2,
    OPENROUTER_MODEL_TIM3,
    TIM2_BASE_URL,
    TIM2_API_KEY,
    TIM2_MODEL_ID,
    TIM3_BASE_URL,
    TIM3_API_KEY,
    TIM3_MODEL_ID,
)

logger = logging.getLogger(__name__)

_SESSION_CACHE: OrderedDict[str, dict] = OrderedDict()
_MAX_SESSIONS = 100


def _db_url() -> str:
    from app.core.settings import DATABASE_URL
    return DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")


def get_session(session_id: str) -> dict | None:
    try:
        import psycopg
        with psycopg.connect(_db_url()) as conn:
            row = conn.execute(
                "SELECT data FROM pipeline_sessions WHERE session_id = %s AND expires_at > NOW()",
                [session_id],
            ).fetchone()
            if row:
                return row[0]
    except Exception as e:
        logger.warning(f"DB get_session gagal, coba cache: {e}")
    return _SESSION_CACHE.get(session_id)


def _save_session(session_id: str, data: dict) -> None:
    url = _db_url()
    logger.warning(f"[session] save {session_id} ke DB (url prefix: {url[:30]}...)")
    try:
        import psycopg
        with psycopg.connect(url) as conn:
            conn.execute(
                """
                INSERT INTO pipeline_sessions (session_id, data, expires_at)
                VALUES (%s, %s, NOW() + INTERVAL '1 hour')
                ON CONFLICT (session_id) DO UPDATE
                SET data = EXCLUDED.data, expires_at = EXCLUDED.expires_at
                """,
                [session_id, json.dumps(data)],
            )
            conn.commit()
        logger.warning(f"[session] save {session_id} OK")
        return
    except Exception as e:
        logger.error(f"[session] DB save_session gagal: {e}")
    _SESSION_CACHE[session_id] = data
    if len(_SESSION_CACHE) > _MAX_SESSIONS:
        _SESSION_CACHE.popitem(last=False)


def strip_markdown(text: str) -> str:
    text = re.sub(r'#{1,3}\s*', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()


def extract_key_points(stratkom: str) -> list[str]:
    SKIP_HEADINGS = [
        "strategi utama", "key messages", "talking points",
        "channel", "timeline", "dasar hukum",
    ]
    points = []
    for line in stratkom.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[0] not in "0123456789-•*":
            continue
        clean = re.sub(r'\*\*(.*?)\*\*', r'\1', stripped)
        clean = clean.lstrip("0123456789.-• ").strip()
        if any(h in clean.lower() for h in SKIP_HEADINGS):
            continue
        if clean:
            points.append(clean)
        if len(points) == 5:
            break
    return points


# ---------------------------------------------------------------------------
# Groq (OpenAI-compatible)
# ---------------------------------------------------------------------------

def _openrouter_chat(messages: list[dict], model: str, max_tokens: int = 1000) -> str:
    from app.core.settings import GROQ_API_KEY, GROQ_BASE_URL
    api_key  = GROQ_API_KEY or OPENROUTER_API_KEY
    base_url = GROQ_BASE_URL if GROQ_API_KEY else OPENROUTER_BASE_URL
    if not api_key:
        raise ValueError("GROQ_API_KEY belum diset")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model"     : model,
        "messages"  : messages,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        if not resp.is_success:
            logger.error(f"LLM API error {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _call_tim2_openrouter(prompt: str, chunks: list[dict], max_tokens: int = 800) -> dict:
    context_text = "\n\n".join(
        f"[Chunk {i+1}] {c['text']}" for i, c in enumerate(chunks[:5])
    ) if chunks else "Tidak ada konteks tambahan."

    messages = [
        {
            "role": "system",
            "content": (
                "Kamu adalah analis isu publik pemerintah Indonesia. "
                "Analisis narasi isu dari query dan konteks yang diberikan. "
                "Balas HANYA dalam format JSON berikut tanpa teks lain:\n"
                "{\n"
                '  "narasi": "teks narasi lengkap dalam Bahasa Indonesia",\n'
                '  "issue_summary": "ringkasan 1-2 kalimat",\n'
                '  "dominant_sentiment": "positif|negatif|campuran",\n'
                '  "risk_level": "low|medium|high|critical",\n'
                '  "issue_category": "kategori isu",\n'
                '  "sentiment_overview": {"positif": 0, "negatif": 0, "netral": 0},\n'
                '  "stakeholders": ["..."],\n'
                '  "trending_keywords": ["..."]\n'
                "}"
            ),
        },
        {
            "role": "user",
            "content": f"[QUERY ISU]\n{prompt}\n\n[KONTEKS DATA]\n{context_text}",
        },
    ]

    raw = _openrouter_chat(messages, OPENROUTER_MODEL_TIM2, max_tokens)

    try:
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(json_match.group()) if json_match else {}
    except Exception:
        data = {}

    return {
        "narasi_text": data.get("narasi", raw),
        "meta": {
            "issue_summary"     : data.get("issue_summary", ""),
            "dominant_sentiment": data.get("dominant_sentiment", ""),
            "risk_level"        : data.get("risk_level", ""),
            "issue_category"    : data.get("issue_category", ""),
            "sentiment_overview": data.get("sentiment_overview", {}),
            "stakeholders"      : data.get("stakeholders", []),
            "trending_keywords" : data.get("trending_keywords", []),
        },
    }


def _call_tim3_openrouter(narasi: str, meta: dict, channel: str = "press") -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "Kamu adalah asisten penyusun kebijakan pemerintah Indonesia. "
                "Buatlah Strategi Komunikasi yang mencakup: Strategi Utama, "
                "Key Messages, Talking Points, Channel, Timeline, dan Dasar Hukum."
            ),
        },
        {
            "role": "user",
            "content": (
                f"[NARASI ISU]     {meta.get('issue_summary', narasi[:300])}\n"
                f"[KATEGORI ISU]   {meta.get('issue_category', '-')}\n"
                f"[SENTIMEN]       {meta.get('dominant_sentiment', '-')}\n"
                f"[TINGKAT RISIKO] {meta.get('risk_level', '-')}\n"
                f"[TARGET AUDIENS] Masyarakat umum\n"
                f"[CHANNEL]        {channel}"
            ),
        },
    ]
    stratkom = _openrouter_chat(messages, OPENROUTER_MODEL_TIM3, max_tokens=1500)
    return {"stratkom": stratkom, "citations": {"regulations": [], "press_statements": []}}


# ---------------------------------------------------------------------------
# Custom (Tim 2 & Tim 3 real API)
# ---------------------------------------------------------------------------

def _call_tim2_custom(prompt: str, chunks: list[dict], max_tokens: int = 400) -> dict:
    context = [{"type": "text", "value": c["text"]} for c in chunks[:5]]
    payload = {
        "model"      : TIM2_MODEL_ID,
        "prompt"     : prompt,
        "context"    : context,
        "max_tokens" : max_tokens,
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{TIM2_BASE_URL}/completions",
            headers={"Authorization": f"Bearer {TIM2_API_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    narasi_text = data["choices"][0]["text"]
    meta_raw    = data.get("_mock_meta", {})
    return {
        "narasi_text": narasi_text,
        "meta": {
            "issue_summary"     : meta_raw.get("issue_summary", ""),
            "dominant_sentiment": meta_raw.get("dominant_sentiment", ""),
            "risk_level"        : meta_raw.get("risk_level", ""),
            "issue_category"    : meta_raw.get("issue_category", ""),
            "sentiment_overview": meta_raw.get("sentiment_overview", {}),
            "stakeholders"      : meta_raw.get("stakeholders", []),
            "trending_keywords" : meta_raw.get("trending_keywords", []),
        },
    }


def _call_tim3_custom(narasi: str, meta: dict, channel: str = "press") -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "Kamu adalah asisten penyusun kebijakan pemerintah Indonesia. "
                "Buatlah Strategi Komunikasi yang mencakup: Strategi Utama, "
                "Key Messages, Talking Points, Channel, Timeline, dan Dasar Hukum."
            ),
        },
        {
            "role": "user",
            "content": (
                f"[NARASI ISU]     {meta.get('issue_summary', '')}\n"
                f"[KATEGORI ISU]   {meta.get('issue_category', '-')}\n"
                f"[SENTIMEN]       {meta.get('dominant_sentiment', '-')}\n"
                f"[TINGKAT RISIKO] {meta.get('risk_level', '-')}\n"
                f"[TARGET AUDIENS] Masyarakat umum\n"
                f"[CHANNEL]        {channel}"
            ),
        },
    ]
    payload = {
        "model"      : TIM3_MODEL_ID,
        "messages"   : messages,
        "max_tokens" : 1500,
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{TIM3_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {TIM3_API_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    stratkom = data["choices"][0]["message"]["content"]
    citations = data.get("citations", {"regulations": [], "press_statements": []})
    return {"stratkom": stratkom, "citations": citations}


# ---------------------------------------------------------------------------
# Mock (fallback offline)
# ---------------------------------------------------------------------------

def _call_mock(prompt: str, chunks: list[dict], channel: str = "press") -> tuple[dict, dict]:
    from app.mocks.mock_responses import mock_tim2_completions, mock_tim3_chat_completions

    context   = [{"type": "text", "value": c["text"]} for c in chunks[:3]]
    tim2_res  = mock_tim2_completions(prompt=prompt, context=context, max_tokens=400)
    narasi_text = tim2_res["choices"][0]["text"]
    meta_raw    = tim2_res.get("_mock_meta", {})
    meta = {
        "issue_summary"     : meta_raw.get("issue_summary", ""),
        "dominant_sentiment": meta_raw.get("dominant_sentiment", ""),
        "risk_level"        : meta_raw.get("risk_level", ""),
        "issue_category"    : meta_raw.get("issue_category", ""),
        "sentiment_overview": meta_raw.get("sentiment_overview", {}),
        "stakeholders"      : meta_raw.get("stakeholders", []),
        "trending_keywords" : meta_raw.get("trending_keywords", []),
    }

    messages = [
        {"role": "system", "content": "Kamu adalah asisten penyusun kebijakan pemerintah Indonesia."},
        {
            "role": "user",
            "content": (
                f"[NARASI ISU]     {meta['issue_summary']}\n"
                f"[KATEGORI ISU]   {meta['issue_category']}\n"
                f"[SENTIMEN]       {meta['dominant_sentiment']}\n"
                f"[TINGKAT RISIKO] {meta['risk_level']}\n"
                f"[CHANNEL]        {channel}"
            ),
        },
    ]
    tim3_res  = mock_tim3_chat_completions(messages=messages, max_tokens=1500)
    stratkom  = tim3_res["choices"][0]["message"]["content"]
    citations = tim3_res.get("citations", {"regulations": [], "press_statements": []})

    return (
        {"narasi_text": narasi_text, "meta": meta},
        {"stratkom": stratkom, "citations": citations},
    )


# ---------------------------------------------------------------------------
# Pipeline utama
# ---------------------------------------------------------------------------

def run_pipeline(
    prompt: str,
    context: list,
    top_k: int          = 5,
    issue_category      = None,
    sentiment           = None,
    region              = None,
    session_id: str     = None,
    channel: str        = "press",
    tone: str           = "formal",
) -> dict:

    sid = session_id or f"s-{uuid.uuid4().hex[:8]}"

    # Step 1: Qdrant retrieval
    try:
        chunks = search_filtered(
            query=prompt,
            top_k=top_k,
            issue_category=issue_category,
            sentiment=sentiment,
            region=region,
        )
    except Exception as e:
        logger.warning(f"Qdrant search gagal: {e}")
        chunks = []

    # Step 2 & 3: Tim 2 + Tim 3
    tim2_status = "ok"
    tim3_status = "ok"

    mode = MODEL_MODE

    try:
        if mode == "openrouter":
            if not OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY belum diset")
            tim2 = _call_tim2_openrouter(prompt, chunks)
            tim3 = _call_tim3_openrouter(tim2["narasi_text"], tim2["meta"], channel)

        elif mode == "custom":
            tim2 = _call_tim2_custom(prompt, chunks)
            tim3 = _call_tim3_custom(tim2["narasi_text"], tim2["meta"], channel)

        else:
            tim2_data, tim3_data = _call_mock(prompt, chunks, channel)
            tim2 = tim2_data
            tim3 = tim3_data

        narasi_text = tim2["narasi_text"]
        meta        = tim2["meta"]
        stratkom    = tim3["stratkom"]
        citations   = tim3["citations"]

    except Exception as e:
        logger.error(f"Pipeline error (mode={mode}): {e} — fallback ke mock")
        tim2_data, tim3_data = _call_mock(prompt, chunks, channel)
        narasi_text = tim2_data["narasi_text"]
        meta        = tim2_data["meta"]
        stratkom    = tim3_data["stratkom"]
        citations   = tim3_data["citations"]
        tim2_status = "fallback"
        tim3_status = "fallback"

    regulasi = [
        {
            "nomor"  : r.get("title", ""),
            "judul"  : r.get("value", ""),
            "lembaga": "Pemerintah RI",
            "tahun"  : int(r["title"][-4:]) if r.get("title", "")[-4:].isdigit() else 0,
        }
        for r in citations.get("regulations", [])
    ]

    narasi_clean = strip_markdown(narasi_text)
    key_points   = extract_key_points(stratkom)

    result = {
        "status"    : "success",
        "session_id": sid,
        "narasi": {
            "isu"       : prompt,
            "narasi"    : narasi_clean,
            "key_points": key_points,
        },
        "stratkom": {
            "strategi"   : stratkom,
            "pesan_utama": meta.get("issue_summary", ""),
            "rekomendasi": key_points,
        },
        "retrieved_docs": chunks,
        "regulasi"      : regulasi,
        "export_url"    : None,
        "step_meta": {
            "tim2": {"status": tim2_status, "latency_ms": None, "fallback_used": tim2_status == "fallback"},
            "tim3": {"status": tim3_status, "latency_ms": None, "fallback_used": tim3_status == "fallback"},
        },
        "message": None,
    }
    _save_session(sid, result)
    return result
