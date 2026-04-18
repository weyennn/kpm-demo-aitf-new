"""
Router Tim 3 — Strategi Komunikasi (via Groq).
Prefix /mock/v1/tim3 untuk dev paralel sebelum API real Tim 3 siap.

Endpoint:
  GET  /mock/v1/tim3/models
  POST /mock/v1/tim3/chat/completions   ← generate strategi komunikasi
  GET  /mock/v1/tim3/crawlers/status    ← status corpus regulasi
"""

import uuid
import time
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.settings import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL_TIM3
from app.mocks.mock_responses import mock_tim3_chat_completions, mock_models_tim3

router = APIRouter(prefix="/mock/v1/tim3", tags=["Tim 3 — Strategi Komunikasi"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "team3-comm-strategy-sft-v1"
    messages: list[Message]
    temperature: float = 0.3
    max_tokens: int = 1500
    stream: bool = False


# ---------------------------------------------------------------------------
# Helper Groq
# ---------------------------------------------------------------------------

def _chat(messages: list[dict], max_tokens: int) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kpm.local",
        "X-Title": "KPM Tim 4 — Tim 3",
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json={"model": GROQ_MODEL_TIM3, "messages": messages, "max_tokens": max_tokens},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/models", summary="List model Tim 3")
def list_models():
    return mock_models_tim3()


@router.get("/models/{model_id}", summary="Detail model Tim 3")
def get_model(model_id: str):
    if model_id != "team3-comm-strategy-sft-v1":
        raise HTTPException(status_code=404, detail={"error": {"message": f"Model '{model_id}' not found"}})
    return {"id": "team3-comm-strategy-sft-v1", "object": "model", "created": 1709425000, "owned_by": "tim3-stratkom"}


@router.post("/chat/completions", summary="Generate strategi komunikasi")
def chat_completions(req: ChatCompletionRequest):
    msgs = [m.model_dump() for m in req.messages]

    if not GROQ_API_KEY:
        return mock_tim3_chat_completions(messages=msgs, max_tokens=req.max_tokens)

    try:
        content = _chat(msgs, req.max_tokens)
    except Exception:
        return mock_tim3_chat_completions(messages=msgs, max_tokens=req.max_tokens)

    return {
        "id"     : f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object" : "chat.completion",
        "created": int(time.time()),
        "model"  : GROQ_MODEL_TIM3,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage"  : {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "citations": {"regulations": [], "press_statements": []},
    }


@router.get("/crawlers/status", summary="Status corpus regulasi Tim 3")
def crawlers_status():
    return {
        "status": "ok",
        "crawlers": [
            {"name": "regulasi-peraturan-pemerintah", "last_run": "2026-03-31T00:00:00Z", "documents_indexed": 1842, "status": "idle"},
            {"name": "regulasi-perpres",              "last_run": "2026-03-31T00:00:00Z", "documents_indexed": 654,  "status": "idle"},
            {"name": "siaran-pers-kominfo",            "last_run": "2026-04-01T06:00:00Z", "documents_indexed": 320,  "status": "idle"},
        ],
        "corpus_last_updated": "2026-04-01T06:00:00Z",
        "note": "Corpus regulasi real tersedia saat Tim 3 deploy.",
    }
