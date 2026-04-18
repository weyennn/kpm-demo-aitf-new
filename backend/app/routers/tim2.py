"""
Router Tim 2 — Narasi Isu (via Groq).
Prefix /mock/v1/tim2 untuk dev paralel sebelum API real Tim 2 siap.

Endpoint:
  GET  /mock/v1/tim2/models
  GET  /mock/v1/tim2/models/{model_id}
  POST /mock/v1/tim2/completions       ← pipeline utama RAG → Tim 2
  POST /mock/v1/tim2/chat/completions  ← mode chatbot agentic
"""

import re
import json
import uuid
import time
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core.settings import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL_TIM2
from app.mocks.mock_responses import mock_tim2_completions, mock_tim2_chat_completions, mock_models_tim2

router = APIRouter(prefix="/mock/v1/tim2", tags=["Tim 2 — Narasi Isu"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ContextItem(BaseModel):
    type: str = Field(..., description="'id' | 'url' | 'text'")
    value: str

class CompletionRequest(BaseModel):
    model: str = "indo-sft-v1"
    prompt: str
    context: list[ContextItem] = []
    max_tokens: int = 400
    temperature: float = 0.7
    stream: bool = False

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "indo-sft-v1"
    messages: list[Message]
    context: list[ContextItem] = []
    max_tokens: int = 400
    temperature: float = 0.6
    stream: bool = False


# ---------------------------------------------------------------------------
# Helper Groq
# ---------------------------------------------------------------------------

def _chat(messages: list[dict], max_tokens: int) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kpm.local",
        "X-Title": "KPM Tim 4 — Tim 2",
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json={"model": GROQ_MODEL_TIM2, "messages": messages, "max_tokens": max_tokens},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _parse_meta(raw: str) -> dict:
    try:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(m.group()) if m else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/models", summary="List model Tim 2")
def list_models():
    return mock_models_tim2()


@router.get("/models/{model_id}", summary="Detail model Tim 2")
def get_model(model_id: str):
    if model_id != "indo-sft-v1":
        raise HTTPException(status_code=404, detail={"error": {"message": f"Model '{model_id}' not found"}})
    return {"id": "indo-sft-v1", "object": "model", "created": 1709420000, "owned_by": "tim2-narasi"}


@router.post("/completions", summary="Analisis narasi isu (pipeline utama)")
def text_completions(req: CompletionRequest):
    ctx_list = [c.model_dump() for c in req.context]

    if not GROQ_API_KEY:
        return mock_tim2_completions(prompt=req.prompt, context=ctx_list, max_tokens=req.max_tokens)

    context_text = "\n\n".join(
        f"[Chunk {i+1}] {c['value']}" for i, c in enumerate(ctx_list[:5])
    ) if ctx_list else "Tidak ada konteks tambahan."

    messages = [
        {
            "role": "system",
            "content": (
                "Kamu adalah analis isu publik pemerintah Indonesia. "
                "Analisis narasi isu dari query dan konteks yang diberikan. "
                "Balas HANYA dalam format JSON:\n"
                '{"narasi":"...","issue_summary":"...","dominant_sentiment":"positif|negatif|campuran",'
                '"risk_level":"low|medium|high|critical","issue_category":"...",'
                '"sentiment_overview":{"positif":0,"negatif":0,"netral":0},'
                '"stakeholders":["..."],"trending_keywords":["..."]}'
            ),
        },
        {"role": "user", "content": f"[QUERY ISU]\n{req.prompt}\n\n[KONTEKS DATA]\n{context_text}"},
    ]

    try:
        raw  = _chat(messages, req.max_tokens)
        data = _parse_meta(raw)
        narasi_text = data.get("narasi", raw)
    except Exception:
        return mock_tim2_completions(prompt=req.prompt, context=ctx_list, max_tokens=req.max_tokens)

    return {
        "id"     : f"cmpl-{uuid.uuid4().hex[:8]}",
        "object" : "text_completion",
        "created": int(time.time()),
        "model"  : GROQ_MODEL_TIM2,
        "choices": [{"text": narasi_text, "index": 0, "finish_reason": "stop"}],
        "usage"  : {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "context_used": ctx_list[:3],
        "_mock_meta": {
            "issue_summary"     : data.get("issue_summary", ""),
            "dominant_sentiment": data.get("dominant_sentiment", ""),
            "risk_level"        : data.get("risk_level", ""),
            "issue_category"    : data.get("issue_category", ""),
            "sentiment_overview": data.get("sentiment_overview", {}),
            "stakeholders"      : data.get("stakeholders", []),
            "trending_keywords" : data.get("trending_keywords", []),
        },
    }


@router.post("/chat/completions", summary="Chatbot agentic multi-turn")
def chat_completions(req: ChatCompletionRequest):
    msgs = [m.model_dump() for m in req.messages]

    if not GROQ_API_KEY:
        return mock_tim2_chat_completions(messages=msgs, max_tokens=req.max_tokens)

    try:
        content = _chat(msgs, req.max_tokens)
    except Exception:
        return mock_tim2_chat_completions(messages=msgs, max_tokens=req.max_tokens)

    return {
        "id"     : f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object" : "chat.completion",
        "created": int(time.time()),
        "model"  : GROQ_MODEL_TIM2,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage"  : {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
